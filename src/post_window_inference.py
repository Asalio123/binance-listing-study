"""Пост-событийные CAR на death-inclusive панели Binance + инференс.

Окна (0 -> +k) от close дня 0, market-adjusted (вычет BTC-доходности).
Сравнение инференса: наивный t/Wilcoxon против month-block bootstrap
(кластеры = календарные месяцы дня листинга).
"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'data' / 'binance_day_closes'
_local = threading.local()


def s3():
    if not hasattr(_local, 'cli'):
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config
        _local.cli = boto3.client('s3', region_name='ap-northeast-1',
                                  config=Config(signature_version=UNSIGNED))
    return _local.cli


def next_ym(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f'{y + 1}-01' if m == 12 else f'{y}-{m + 1:02d}'


def month_close_map(sym, ym):
    """{ts_нано: close} месячного файла с дисковым кэшем."""
    cf = CACHE / f'{sym}-{ym}.json'
    if cf.exists():
        return {int(k): v for k, v in json.loads(cf.read_text()).items()}
    try:
        import csv
        import io
        import zipfile
        obj = s3().get_object(Bucket='data.binance.vision',
                              Key=f'data/spot/monthly/klines/{sym}/1d/{sym}-1d-{ym}.zip')
        zf = zipfile.ZipFile(io.BytesIO(obj['Body'].read()))
        out = {}
        with zf.open(zf.namelist()[0]) as f:
            for line in csv.reader(io.TextIOWrapper(f, encoding='utf-8')):
                if len(line) < 5:
                    continue
                ts = int(line[0])
                if ts > 10 ** 14:
                    ts //= 1000
                out[pd.Timestamp(ts, unit='ms').normalize().value] = float(line[4])
        CACHE.mkdir(exist_ok=True)
        cf.write_text(json.dumps(out))
        return out
    except Exception:
        return {}


def main():
    df = pd.read_csv(ROOT / 'data' / 'listing_events_enriched.csv')
    btc = {}
    lock = threading.Lock()
    months = sorted({m for m in df.first_month} | {next_ym(m) for m in df.first_month})
    t0 = time.time()

    def grab_btc(ym):
        part = month_close_map('BTCUSDT', ym)
        if part:
            with lock:
                btc.update(part)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(grab_btc, months))
    print(f'BTC месяцев: {len(months)}, дней: {len(btc)} ({time.time() - t0:.0f}с)', flush=True)

    rows, fails = [], []
    for i, row in enumerate(df.itertuples(index=False), 1):
        cm = {}
        for mm in [row.first_month, next_ym(row.first_month)]:
            cm.update(month_close_map(row.symbol, mm) or {})
        dates = sorted(cm)
        if not dates:
            fails.append((row.symbol, 'no data'))
            continue
        d0ts = dates[0]
        d0 = pd.Timestamp(d0ts)
        b0 = btc.get(d0ts)
        rec = {'symbol': row.symbol, 'month': row.first_month}
        any_ok = False
        for k in (1, 3, 7):
            kk = d0 + pd.Timedelta(days=k)
            c0, ck = cm.get(d0ts), cm.get(kk.value)
            bk = btc.get(kk.value)
            if c0 is None or ck is None or b0 is None or bk is None:
                rec[f'madj_{k}'] = np.nan
                continue
            rec[f'madj_{k}'] = float(np.log(ck / c0) - np.log(bk / b0))
            any_ok = True
        if any_ok:
            rows.append(rec)
        else:
            fails.append((row.symbol, 'windows missing'))
        if i % 100 == 0:
            print(f'...{i}/{len(df)} ({time.time() - t0:.0f}с)', flush=True)

    out = pd.DataFrame(rows).merge(
        df[['symbol', 'fwd_7', 'fwd_30', 'delisted', 'pop_day0', 'range_day0']],
        on='symbol', how='left')
    out.to_csv(ROOT / 'data' / 'post_window_car.csv', index=False)
    print(f'\nуспешно: {len(out)} | фейлов: {len(fails)} {fails[:5]}')

    c = out['madj_7'].dropna().values * 100
    t, p = stats.ttest_1samp(c, 0)
    w = stats.wilcoxon(c)
    print(f'\nmadj (0->7д): n={len(c)} mean={c.mean():+.2f}% median={np.median(c):+.2f}% '
          f't={t:+.2f} p={p:.2e} wilcoxon p={w.pvalue:.2e}')

    rng = np.random.default_rng(42)
    by_m = {m: g['madj_7'].dropna().values * 100 for m, g in out.groupby('month')}
    clusters = sorted(by_m)
    boots = []
    for _ in range(5000):
        pick = rng.choice(clusters, size=len(clusters), replace=True)
        boots.append(np.concatenate([by_m[m] for m in pick]).mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p_boot = 2 * min((np.array(boots) <= 0).mean(), (np.array(boots) >= 0).mean())
    naive_se = c.std(ddof=1) / np.sqrt(len(c))
    cl_se = float(np.std(boots, ddof=1))
    print(f'month-block bootstrap: CI [{lo:+.2f}, {hi:+.2f}], p~{p_boot:.3g}')
    print(f'SE naive {naive_se:.3f} vs month-cluster {cl_se:.3f} -> инфляция x{naive_se / cl_se:.2f}')

    # USD-взвешенная версия
    to = pd.read_csv(ROOT / 'data' / 'day0_turnover.csv')
    dd = out.merge(to, on='symbol').dropna(subset=['madj_7'])
    wv = dd.usd_turnover.clip(lower=1).values
    o = np.argsort(dd.madj_7.values)  # взвешенная медиана: порядок по ЗНАЧЕНИЮ, не по весу
    vw = float(dd.madj_7.values[o][np.searchsorted(np.cumsum(wv[o]), wv[o].sum() / 2)]) * 100
    print(f'USD-VW madj (0->7д): {vw:+.2f}% (EW mean {c.mean():+.2f}%)')


if __name__ == '__main__':
    main()
