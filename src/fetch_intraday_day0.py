"""Минутная анатомия дня 0 для всех событий панели из архива data.binance.vision.

Источник: daily 1m klines zip (28-64 КБ); при 404 — fallback на monthly zip
с фильтрацией строк дня 0. Архив death-inclusive, 404 = осмысленный пропуск.
ГРАБЛЯ: open_time с 2025 в микросекундах (16 цифр), раньше — миллисекунды (13);
нормализация по длине числа.

Кэш сырых zip в data/intraday_day0_cache/ (возобновляемость).
Выход: data/intraday_day0.csv (symbol + метрики первого часа/дня).
"""
import io
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path.home() / "binance-listing-study"
OUT = ROOT / "data" / "intraday_day0.csv"
CACHE = ROOT / "data" / "intraday_day0_cache"
BASE = "https://data.binance.vision/data/spot"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def fetch_url(url):
    """GET с ретраями; 404 -> None (архивная дыра, не ошибка)."""
    url = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=-._~%")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def parse_zip(body, day0=None):
    """zip -> DataFrame баров; если day0 задан, фильтрует только этот UTC-день."""
    zf = zipfile.ZipFile(io.BytesIO(body))
    with zf.open(zf.namelist()[0]) as f:
        df = pd.read_csv(f, header=None, names=COLS,
                         dtype={c: "float64" for c in COLS[1:6]} | {"quote_volume": "float64"})
    df = df[pd.to_numeric(df["open_time"], errors="coerce").notna()]  # скип header-строк
    ts = df["open_time"].astype("int64")
    # нормализация единиц по длине числа: 13=мс, 16=мкс, 19=нс
    scale = {13: 1, 16: 10 ** 3, 19: 10 ** 6}[len(str(ts.iloc[0]))]
    df["ts_ms"] = ts // scale
    if day0 is not None:
        df = df[df["ts_ms"] // 86_400_000 == day0]
    return df.sort_values("ts_ms").reset_index(drop=True)


def grab(sym, day0_date):
    """Кэш -> daily zip -> monthly fallback. Возвращает DataFrame баров дня 0 или None."""
    CACHE.mkdir(exist_ok=True)
    day0 = int(pd.Timestamp(day0_date).value // 10 ** 6) // 86_400_000  # unix-day
    daily_cp = CACHE / f"{sym}_{day0_date}_daily.zip"
    if daily_cp.exists():
        return parse_zip(daily_cp.read_bytes())
    time.sleep(random.uniform(0.3, 0.5))
    y, m, _ = day0_date.split("-")
    body = fetch_url(f"{BASE}/daily/klines/{sym}/1m/{sym}-1m-{day0_date}.zip")
    if body is not None:
        daily_cp.write_bytes(body)
        return parse_zip(body)
    monthly_cp = CACHE / f"{sym}_{y}-{m}_monthly.zip"
    if monthly_cp.exists():
        df = parse_zip(monthly_cp.read_bytes(), day0)
        return df if len(df) else None
    time.sleep(random.uniform(0.3, 0.5))
    body = fetch_url(f"{BASE}/monthly/klines/{sym}/1m/{sym}-1m-{y}-{m}.zip")
    if body is None:
        return None
    monthly_cp.write_bytes(body)
    df = parse_zip(body, day0)
    return df if len(df) else None


def metrics(sym, df):
    open0, n = df["open"].iloc[0], len(df)
    h1 = df.iloc[:60]
    first_ts = int(df["ts_ms"].iloc[0])
    peak_ts = int(df.loc[df["high"].idxmax(), "ts_ms"])
    qv_day = df["quote_volume"].sum()
    return {"symbol": sym,
            "listing_open_ts_utc": pd.Timestamp(first_ts, unit="ms").isoformat(),
            "listing_hour_utc": first_ts // 3_600_000 % 24,
            "ret_first_hour": h1["close"].iloc[-1] / open0 - 1,
            "ret_after_first_hour": df["close"].iloc[-1] / h1["close"].iloc[-1] - 1,
            "ret_day0_full": df["close"].iloc[-1] / open0 - 1,
            "time_to_peak_min": (peak_ts - first_ts) / 60_000,
            "hour1_volume_share": h1["quote_volume"].sum() / qv_day if qv_day else float("nan"),
            "n_bars": n}


def main():
    t = pd.read_csv(ROOT / "data" / "day0_turnover.csv")
    e = pd.read_csv(ROOT / "data" / "listing_events_enriched.csv", usecols=["symbol"])
    jobs = list(t.merge(e, on="symbol")[["symbol", "day0_date"]].itertuples(index=False))
    print(f"Событий: {len(jobs)}", flush=True)
    out, fail = [], []
    t0 = time.time()

    def work(job):
        df = grab(job.symbol, job.day0_date)
        return metrics(job.symbol, df) if df is not None and len(df) else None

    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, res in enumerate(pool.map(work, jobs), 1):
            (out if res is not None else fail).append(res if res is not None else jobs[i - 1].symbol)
            if i % 50 == 0:
                print(f"...{i}/{len(jobs)} ({time.time() - t0:.0f}с)", flush=True)
    ok = pd.DataFrame(out)
    ok.to_csv(OUT, index=False)
    print(f"\nOK: {len(ok)}/{len(jobs)} | дыры архива: {len(fail)}", flush=True)
    if fail:
        print("дыры:", fail, flush=True)
    print(f"-> {OUT}", flush=True)


if __name__ == "__main__":
    main()
