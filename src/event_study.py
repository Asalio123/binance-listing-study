"""Event-study листинговой стратегии Binance spot 2021-2026.

Вопросы:
  - Что происходит с ценой ПОСЛЕ открытия торгов (день 0 = первый день листинга)?
  - pop_day0: движение от первого принта до закрытия дня 0.
  - fwd_1/3/7/14/30: доходность от закрытия дня 0 вперёд на N торговых дней.
Survivorship: делистнутые монеты берём из архива data.binance.vision;
если история оборвалась раньше горизонта - фиксируем mark-to-last и флаг trunc.
"""
import csv
import io
import re
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

DATA = Path.home() / "[private-repo]" / "data"
CAL = DATA / "listing_events.csv"
OUT = DATA / "listing_event_returns.csv"

S3 = boto3.client("s3", region_name="ap-northeast-1", config=Config(signature_version=UNSIGNED))
HORIZONS = [1, 3, 7, 14, 30]
LEV_PAT = re.compile(r"(UP|DOWN|BULL|BEAR)USDT$")

API = "https://api.binance.com/api/v3/klines"


def rest_klines(sym, start_ms):
    url = f"{API}?symbol={sym}&interval=1d&startTime={start_ms}&limit=1000"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json_loads(r.read())
    except Exception:
        return []


def json_loads(b):
    import json

    return json.loads(b)


def archive_daily(sym, ym_from, ym_to):
    """Дневные свечи из архивных zip'ов [ym_from..ym_to]. Возврат: list[(date, open, close)]."""
    rows = []
    cur = pd.Period(ym_from, "M")
    end = pd.Period(ym_to, "M")
    jobs = []
    while cur <= end and len(jobs) < 40:  # предохранитель: не более 40 месяцев на символ
        key = f"data/spot/monthly/klines/{sym}/1d/{cur}-1d.zip" if False else f"data/spot/monthly/klines/{sym}/1d/{sym}-1d-{cur}.zip"
        jobs.append((key, str(cur)))
        cur += 1
    def grab(job):
        key, period = job
        try:
            obj = S3.get_object(Bucket="data.binance.vision", Key=key)
            zf = zipfile.ZipFile(io.BytesIO(obj["Body"].read()))
            name = zf.namelist()[0]
            out = []
            with zf.open(name) as f:
                text = io.TextIOWrapper(f, encoding="utf-8")
                for line in csv.reader(text):
                    if len(line) < 5:
                        continue
                    ts = int(line[0])
                    if ts > 10 ** 14:  # микросекунды с 2025
                        ts //= 1000
                    d = pd.Timestamp(ts, unit="ms").date()
                    out.append((d, float(line[1]), float(line[4])))
            return out
        except Exception:
            return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for res in pool.map(grab, jobs):
            rows.extend(res)
    rows.sort(key=lambda x: x[0])
    return rows


def collect(sym, first_month, last_month):
    start_ms = int(pd.Timestamp(first_month + "-01").timestamp() * 1000)
    raw = rest_klines(sym, start_ms)
    src = "rest"
    if not raw:
        raw_rows = archive_daily(sym, first_month, last_month)
        src = "archive"
    else:
        raw_rows = [
            (
                pd.Timestamp(k[0], unit="ms").date(),
                float(k[1]),
                float(k[4]),
            )
            for k in raw
        ]
    if not raw_rows:
        return None
    df = pd.DataFrame(raw_rows, columns=["date", "open", "close"]).drop_duplicates("date").sort_values("date").set_index("date")
    return df, src


def metrics(df):
    c, o = df["close"], df["open"]
    n = len(c)
    if n < 2:
        return None
    day0_close = c.iloc[0]
    out = {"pop_day0": c.iloc[0] / o.iloc[0] - 1}
    last_date = df.index[-1]
    for h in HORIZONS:
        idx = min(h, n - 1)
        ret = c.iloc[idx] / day0_close - 1
        trunc = (n - 1) < h
        if trunc:
            out[f"fwd_{h}"] = ret  # mark-to-last
        else:
            out[f"fwd_{h}"] = ret
        out[f"trunc_{h}"] = int(trunc)
    out["days_listed"] = n
    out["last_date"] = str(last_date)
    return out


def main():
    cal = pd.read_csv(CAL)
    cal = cal[
        cal.symbol.str.endswith("USDT")
        & ~cal.symbol.str.match(LEV_PAT)
        & (cal.first_month >= "2021-01")
    ]
    # убираем дубли номинала типа 1000SATS vs SATS - оставляем как есть, помечаем
    print(f"Событий к обработке: {len(cal)}", flush=True)

    results = []
    t0 = time.time()
    for i, row in enumerate(cal.itertuples(), 1):
        got = collect(row.symbol, row.first_month, row.last_month)
        if got is None:
            continue
        df, src = got
        m = metrics(df)
        if m is None:
            continue
        m.update(symbol=row.symbol, first_month=row.first_month, delisted=int(row.delisted), source=src)
        results.append(m)
        if i % 25 == 0:
            el = time.time() - t0
            print(f"[{i}/{len(cal)}] {el:.0f}с", flush=True)

    res = pd.DataFrame(results)
    res.to_csv(OUT, index=False)
    print(f"\nГотово: {len(res)} событий -> {OUT}")

    print("\n=== ПОЛНАЯ ВЫБОРКА (все события) ===")
    cols = ["pop_day0"] + [f"fwd_{h}" for h in HORIZONS]
    med = res[cols].median() * 100
    mean = res[cols].mean() * 100
    pos = (res[cols] > 0).mean() * 100
    summ = pd.DataFrame({"median%": med, "mean%": mean, "%positive": pos})
    print(summ.round(1).to_string())

    print("\n=== По годам листинга (медиана fwd_7, %) ===")
    res["year"] = res.first_month.str[:4]
    print(res.groupby("year")[["pop_day0", "fwd_7", "fwd_30"]].median().mul(100).round(1).to_string())

    print("\n=== Делистнутые vs живые (медиана, %) ===")
    print(res.groupby("delisted")[cols].median().mul(100).round(1).to_string())


if __name__ == "__main__":
    main()
