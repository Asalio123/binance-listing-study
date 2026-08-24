"""День-0 USD turnover для всех событий панели из архива data.binance.vision.

Архив death-inclusive (хранит делистнутые символы), в отличие от REST.
Источник поля: klines monthly zip, колонка 7 = quoteAssetVolume (USD).
Выход: data/day0_turnover.csv (symbol, day0_date, usd_turnover).
"""
import csv
import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

ROOT = Path.home() / "binance-listing-study"
OUT = ROOT / "data" / "day0_turnover.csv"
S3 = boto3.client("s3", region_name="ap-northeast-1", config=Config(signature_version=UNSIGNED))


def grab(sym, ym):
    key = f"data/spot/monthly/klines/{sym}/1d/{sym}-1d-{ym}.zip"
    for attempt in range(3):
        try:
            obj = S3.get_object(Bucket="data.binance.vision", Key=key)
            zf = zipfile.ZipFile(io.BytesIO(obj["Body"].read()))
            with zf.open(zf.namelist()[0]) as f:
                for line in csv.reader(io.TextIOWrapper(f, encoding="utf-8")):
                    if len(line) < 8:
                        continue
                    ts = int(line[0])
                    if ts > 10 ** 14:
                        ts //= 1000
                    return {"symbol": sym,
                            "day0_date": str(pd.Timestamp(ts, unit="ms").date()),
                            "usd_turnover": float(line[7])}
            return None
        except S3.exceptions.NoSuchKey:
            return None
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def main():
    df = pd.read_csv(ROOT / "data" / "listing_events_enriched.csv")
    jobs = list(df[["symbol", "first_month"]].itertuples(index=False))
    print(f"Событий: {len(jobs)}", flush=True)
    out, fail = [], []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, res in enumerate(pool.map(lambda j: grab(*j), jobs), 1):
            (out if res else fail).append(res) if res else fail.append((jobs[i - 1].symbol, jobs[i - 1].first_month))
            if i % 100 == 0:
                print(f"...{i}/{len(jobs)} ({time.time()-t0:.0f}с)", flush=True)
    ok = pd.DataFrame(out)
    ok.to_csv(OUT, index=False)
    print(f"\nOK: {len(ok)} | нет в архиве/ошибка: {len(fail)}")
    if fail[:10]:
        print("примеры фейлов:", fail[:10])
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
