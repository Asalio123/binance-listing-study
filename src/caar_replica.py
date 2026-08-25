"""Реплика оценщика Ante/Ante-Meyer на death-inclusive панели Binance.

Для каждого из 472 событий строим дневные закрытия из архива
data.binance.vision (месячные файлы, death-inclusive), оцениваем market model
против BTC на окне (-30,-10), считаем CAR(-3,+3). Затем сравниваем инференс:
наивный кросс-секционный t/Wilcoxon (как в работах Ante) против
month-block bootstrap (кластеризация по календарному месяцу события).
Плюс USD-turnover взвешивание.
"""
import csv
import io
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import boto3
from botocore import UNSIGNED
from botocore.config import Config

ROOT = Path.home() / 'binance-listing-study'
OUT = ROOT / 'data' / 'caar_panel.csv'
S3 = boto3.client('s3', region_name='ap-northeast-1', config=Config(signature_version=UNSIGNED))
_local = threading.local()


def s3():
    if not hasattr(_local, 'cli'):
        _local.cli = boto3.client('s3', region_name='ap-northeast-1',
                                  config=Config(signature_version=UNSIGNED))
    return _local.cli


def month_zip(sym, ym):
    """{date: close} из месячного файла; None если нет."""
    key = f"data/spot/monthly/klines/{sym}/1d/{sym}-1d-{ym}.zip"
    try:
        obj = s3().get_object(Bucket='data.binance.vision', Key=key)
        zf = zipfile.ZipFile(io.BytesIO(obj['Body'].read()))
        out = {}
        with zf.open(zf.namelist()[0]) as f:
            for line in csv.reader(io.TextIOWrapper(f, encoding='utf-8')):
                if len(line) < 5:
                    continue
                ts = int(line[0])
                if ts > 10 ** 14:
                    ts //= 1000
                out[pd.Timestamp(ts, unit='ms').normalize()] = float(line[4])
        return out
    except Exception:
        return None


def prev_ym(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f'{y - 1}-12' if m == 1 else f'{y}-{m - 1:02d}'


def next_ym(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f'{y + 1}-01' if m == 12 else f'{y}-{m + 1:02d}'


def event_car(sym, first_month, btc_cache):
    """CAR(-3,+3) в market-adjusted спецификации (beta=1, вычет BTC).

    Отклонение от оригинала: у Ante оценка беты по (-30,-10) на CMC-ценах
    токена ДО листинга (токен уже торговался на других биржах). На архиве
    Binance до-листинговой истории нет, поэтому beta=1; это консервативнее
    и задекларировано в аудите.
    """
    closes = {}
    for ym in {first_month, next_ym(first_month)}:
        part = month_zip(sym, ym)
        if part:
            closes.update(part)
    if len(closes) < 9:
        return None
    dates = sorted(closes)
    d0 = dates[0]
    pos = {dd: i for i, dd in enumerate(dates)}

    ars, raws = [], []
    for off in range(-3, 4):
        dd = d0 + pd.Timedelta(days=off)
        pd_prev = d0 + pd.Timedelta(days=off - 1)
        if dd not in pos or pd_prev not in pos:
            return None
        i = pos[dd]
        ip = pos[pd_prev]
        pb, cb = btc_cache.get(pd_prev), btc_cache.get(dd)
        if pb is None or cb is None:
            return None
        ri = np.log(closes[dd] / closes[pd_prev])
        rbi = np.log(cb / pb)
        ars.append(ri - rbi)
        raws.append(ri)
    return {'symbol': sym, 'car': float(np.sum(ars)), 'car_raw': float(np.sum(raws)),
            'ar': [float(a) for a in ars], 'day0': str(d0.date()), 'year': d0.year}


def main():
    df = pd.read_csv(ROOT / 'data' / 'listing_events_enriched.csv')
    jobs = list(df[['symbol', 'first_month']].itertuples(index=False))

    btc_months = sorted({next_ym(m) for _, m in jobs} | {m for _, m in jobs})
    print(f'BTC месячных файлов: {len(btc_months)}')
    btc = {}

    def grab_btc(ym):
        part = month_zip('BTCUSDT', ym)
        if part:
            with lock:
                btc.update(part)

    lock = threading.Lock()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(grab_btc, btc_months))
    print(f'BTC загружен ({time.time()-t0:.0f}с)', flush=True)

    res, fails = [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, r in enumerate(pool.map(lambda j: event_car(*j, btc), jobs), 1):
            if r:
                res.append(r)
            else:
                fails += 1
            if i % 100 == 0:
                print(f'...{i}/{len(jobs)}', flush=True)

    car = pd.DataFrame(res)
    car.to_csv(OUT, index=False)
    print(f'\nуспешно: {len(car)} | пропущено: {fails}')
    c = car.car.values * 100
    t, tp = stats.ttest_1samp(c, 0)
    w = stats.wilcoxon(c)
    print(f'CAR(-3,+3) naive: mean={c.mean():+.2f}% t={t:+.2f} (p={tp:.2e}) | wilcoxon p={w.pvalue:.2e}')

    # month-block bootstrap
    car['month'] = pd.to_datetime(car.day0).dt.to_period('M').astype(str)
    clusters = car.month.unique()
    rng = np.random.default_rng(42)
    boots = []
    arr = car.car.values * 100
    by_m = {m: g.car.values * 100 for m, g in car.groupby('month')}
    for _ in range(5000):
        pick = rng.choice(clusters, size=len(clusters), replace=True)
        pooled = np.concatenate([by_m[m] for m in pick])
        boots.append(pooled.mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p_boot = 2 * min((np.array(boots) <= 0).mean(), (np.array(boots) >= 0).mean())
    naive_se = c.std(ddof=1) / np.sqrt(len(c))
    boot_se = float(np.std(boots, ddof=1))
    print(f'month-block bootstrap: mean={np.mean(boots):+.2f}%, CI [{lo:+.2f}, {hi:+.2f}], p~{p_boot:.3g}')
    print(f'SE naive {naive_se:.2f} vs cluster {boot_se:.2f} -> инфляция t x{naive_se/boot_se:.2f}')

    # USD-weighted CAAR
    to = pd.read_csv(ROOT / 'data' / 'day0_turnover.csv')
    d = car.merge(to, on='symbol')
    w = d.usd_turnover.clip(lower=1).values
    o = np.argsort(w)
    vw = float((d.car.values * 100)[o][np.searchsorted(np.cumsum(w[o]), w[o].sum() / 2)])
    print(f'USD-VW CAAR: {vw:+.2f}% (vs EW {c.mean():+.2f}%)')


if __name__ == '__main__':
    main()
