"""Строит календарь листингов Binance из архива data.binance.vision (включая делистнутые).

Логика: один проход по плоскому индексу monthly-klines -> для каждого символа
первый месяц с данными = месяц листинга, последний = месяц делистинга (если история оборвана).
"""
import re
from pathlib import Path

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "listing_calendar_binance.csv"
S3 = boto3.client("s3", region_name="ap-northeast-1", config=Config(signature_version=UNSIGNED, retries={"max_attempts": 5}))


def iter_keys():
    """Быстрый обход: список папок символов (delimiter=/), затем только их 1d-файлы (потоки)."""
    n = 0
    folders = []
    pag = S3.get_paginator("list_objects_v2")
    for page in pag.paginate(
        Bucket="data.binance.vision", Prefix="data/spot/monthly/klines/", Delimiter="/", MaxKeys=1000
    ):
        for p in page.get("CommonPrefixes", []):
            folders.append(p["Prefix"])
    print(f"Папок символов: {len(folders)}", flush=True)

    def sym_days(prefix):
        out = []
        for page in pag.paginate(Bucket="data.binance.vision", Prefix=prefix + "1d/", MaxKeys=1000):
            for obj in page.get("Contents", []):
                out.append(obj["Key"])
        return out

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=12) as pool:
        for keys in pool.map(sym_days, folders):
            yield from keys
            n += len(keys)
            if n % 20000 == 0:
                print(f"...{n} ключей 1d", flush=True)


def main():
    pat = re.compile(r"data/spot/monthly/klines/([^/]+)/1d/[^/]+?(\d{4})-(\d{2})\.zip$")
    first = {}
    last = {}
    for key in iter_keys():
        m = pat.match(key)
        if not m:
            continue
        sym, y, mo = m.groups()
        stamp = (int(y), int(mo))
        s = first.get(sym)
        if s is None or stamp < s:
            first[sym] = stamp
        l = last.get(sym)
        if l is None or stamp > l:
            last[sym] = stamp

    rows = []
    for sym, fm in first.items():
        lm = last.get(sym, fm)
        now = pd.Timestamp.utcnow().to_period("M")
        rows.append(
            dict(
                symbol=sym,
                first_month=f"{fm[0]}-{fm[1]:02d}",
                last_month=f"{lm[0]}-{lm[1]:02d}",
                delisted=int(pd.Period(f"{lm[0]}-{lm[1]:02d}") < now - 1),
            )
        )
    df = pd.DataFrame(rows).sort_values("first_month")
    df.to_csv(OUT, index=False)
    print(f"\nВсего символов с историей: {len(df)}")
    print(f"Из них делистнуто (история оборвана): {df.delisted.sum()}")
    df["y"] = df.first_month.str[:4]
    print("\nЛистингов по годам:")
    print(df.groupby("y").size())


if __name__ == "__main__":
    main()
