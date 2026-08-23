"""Обогащённый event-study: расширенные фичи по каждому листингу Binance.

На выходе: listing_events_enriched.csv — одна строка на листинг, ~25 колонок.
"""
import csv
import io
import json
import re
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
import numpy as np
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

DATA = Path.home() / "[private-repo]" / "data"
OUT_HOME = DATA / "listing_events_enriched.csv"
OUT_REPO = Path.home() / "binance-listing-study" / "data" / "listing_events_enriched.csv"

S3 = boto3.client("s3", region_name="ap-northeast-1", config=Config(signature_version=UNSIGNED))
API = "https://api.binance.com/api/v3/klines"
LEV_PAT = re.compile(r"(UP|DOWN|BULL|BEAR)USDT$")
HORIZONS = [1, 3, 7, 14, 30]


def rest_klines(sym, start_ms):
    url = f"{API}?symbol={sym}&interval=1d&startTime={start_ms}&limit=1000"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception:
        return []


def archive_daily(sym, ym_from, ym_to):
    rows = []
    cur, end = pd.Period(ym_from, "M"), pd.Period(ym_to, "M")
    jobs = []
    while cur <= end and len(jobs) < 40:
        jobs.append((f"data/spot/monthly/klines/{sym}/1d/{sym}-1d-{cur}.zip"))
        cur += 1

    def grab(key):
        try:
            obj = S3.get_object(Bucket="data.binance.vision", Key=key)
            zf = zipfile.ZipFile(io.BytesIO(obj["Body"].read()))
            out = []
            with zf.open(zf.namelist()[0]) as f:
                for line in csv.reader(io.TextIOWrapper(f, encoding="utf-8")):
                    if len(line) < 6:
                        continue
                    ts = int(line[0])
                    if ts > 10 ** 14:
                        ts //= 1000
                    d = pd.Timestamp(ts, unit="ms").date()
                    out.append((d, float(line[1]), float(line[2]), float(line[3]), float(line[4]), float(line[5])))
            return out
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=8) as pool:
        for res in pool.map(grab, jobs):
            rows.extend(res)
    return sorted(rows, key=lambda x: x[0])


def collect(sym, first_month, last_month):
    start_ms = int(pd.Timestamp(first_month + "-01").timestamp() * 1000)
    raw = rest_klines(sym, start_ms)
    if raw:
        rows = [(pd.Timestamp(k[0], unit="ms").date(), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in raw]
    else:
        rows = archive_daily(sym, first_month, last_month)
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"]).drop_duplicates("date").sort_values("date").set_index("date")
    return df


def enrich(df, sym, row):
    n = len(df)
    if n < 2:
        return None
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    c0 = c.iloc[0]
    m = {"symbol": sym, "first_month": row.first_month, "delisted": int(row.delisted),
         "days_listed": n, "quote_vol_day0": v.iloc[0]}

    m["pop_day0"] = c0 / o.iloc[0] - 1
    m["range_day0"] = (h.iloc[0] - l.iloc[0]) / o.iloc[0]

    for hz in HORIZONS:
        idx = min(hz, n - 1)
        m[f"fwd_{hz}"] = c.iloc[idx] / c0 - 1
        m[f"trunc_{hz}"] = int((n - 1) < hz)

    win30 = df.iloc[: min(30, n)]
    peak_idx = int(win30["close"].idxmax() != win30.index[0]) and list(win30["close"]).index(win30["close"].max())
    m["peak30"] = win30["close"].max() / c0 - 1
    m["trough30"] = win30["close"].min() / c0 - 1
    m["time_to_peak_d"] = peak_idx
    w7 = df.iloc[:7]
    m["vol_usd_7d_avg"] = float(w7["volume"].mean())
    m["vol_decay_7d"] = float(w7["volume"][1:].mean() / max(v.iloc[0], 1)) if n > 2 else np.nan
    rr = c.pct_change().iloc[:8].dropna()
    m["ann_vol_7d"] = float(rr.std() * np.sqrt(365)) if len(rr) > 2 else np.nan
    w30c = c.iloc[: min(30, n)]
    m["up_days_share_30"] = float((w30c.pct_change().dropna() > 0).mean()) if len(w30c) > 2 else np.nan
    m["last_date"] = str(df.index[-1])
    return m


def main():
    cal = pd.read_csv(DATA / "listing_events.csv")
    cal = cal[cal.symbol.str.endswith("USDT") & ~cal.symbol.str.match(LEV_PAT) & (cal.first_month >= "2021-01")]
    print(f"Событий: {len(cal)}", flush=True)
    res = []
    t0 = time.time()
    for i, row in enumerate(cal.itertuples(), 1):
        df = collect(row.symbol, row.first_month, row.last_month)
        if df is None:
            continue
        m = enrich(df, row.symbol, row)
        if m:
            res.append(m)
        if i % 50 == 0:
            print(f"[{i}/{len(cal)}] {time.time()-t0:.0f}с", flush=True)
    out = pd.DataFrame(res)
    out.to_csv(OUT_HOME, index=False)
    out.to_csv(OUT_REPO, index=False)
    cols = ["pop_day0", "range_day0", "fwd_7", "fwd_30", "peak30", "trough30", "up_days_share_30"]
    print("\nМедианы ключевых фичей (%):")
    print((out[cols].median() * 100).round(2).to_string())
    print(f"\nOK -> {OUT_REPO}")


if __name__ == "__main__":
    main()
