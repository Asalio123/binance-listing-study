"""Календарь листингов Bybit spot из публичного архива (point-in-time, с делистнутыми).

Структура: https://public.bybit.com/spot/{SYM}/{SYM}-{YYYY-MM}.csv.gz (сырые сделки).
Первый месяц в индексе папки = месяц листинга; последний = делистинг.
"""
import re
import time as time_mod
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

OUT = Path.home() / "binance-listing-study" / "data" / "listing_calendar_bybit.csv"
BASE = "https://public.bybit.com/spot/"
MON = re.compile(r"-(\d{4}-\d{2})\.csv\.gz$")


def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=30).read().decode()
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def main():
    html = get(BASE)
    symbols = sorted(set(re.findall(r'<a href="([^"]+)">', html)))
    print(f"Символов на Bybit spot: {len(symbols)}", flush=True)

    def months(sym):
        try:
            files = re.findall(r'<a href="([^"]+)"', get(BASE + sym + "/"))
            ms = []
            for f in files:
                m = MON.search(f)
                if m:
                    ms.append(m.group(1))
            return sym, sorted(set(ms))
        except Exception:
            return sym, []

    rows = []
    done = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        for sym, ms in pool.map(months, symbols):
            done += 1
            time_mod.sleep(0.05)
            if done % 200 == 0:
                print(f"...{done}", flush=True)
            if not ms:
                continue
            now_pm = pd.Period(pd.Timestamp.now("UTC"), "M")
            last_pm = pd.Period(ms[-1])
            rows.append(dict(symbol=sym, first_month=ms[0], last_month=ms[-1],
                             delisted=int(last_pm < now_pm - 1)))

    df = pd.DataFrame(rows).sort_values("first_month")
    df.to_csv(OUT, index=False)
    usdt = df[df.symbol.str.endswith("USDT")]
    print(f"\nВсего: {len(df)} | USDT: {len(usdt)} | делистнуто USDT: {int(usdt.delisted.sum())}")
    print(usdt.assign(y=usdt.first_month.str[:4]).groupby("y").size())


if __name__ == "__main__":
    main()
