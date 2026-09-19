"""Month-block bootstrap CI для заголовочных USD-взвешенных статистик (M4 аудита).

Кластер = календарный месяц листинга (колонка `month` в post_window_car.csv),
resample месяцев с возвращением, 5000 дравов, percentile 95% CI, rng(42).

Взвешенная медиана считается argsort по ЗНАЧЕНИЮ доходности (исправление
argsort(wv)-бага post_window_inference.py: там сортировка шла по весу).

Статистики:
  vw_median_fwd7          USD-VW медиана fwd_7, полная панель n=470
  vw_median_madj7_btcadj  USD-VW медиана BTC-adjusted madj_7, n=460
  wedge_delisting_vw      VW медиана survivors-only минус VW медиана полной панели
  ew_minus_vw             разрыв EW медиана fwd_7 минус VW медиана fwd_7
  quintile_q1..q5         медиана fwd_7 в квинтилях оборота (партиция n=470,
                          перерезается внутри каждого драва)
  q5_minus_q1             градиент Q5 - Q1 (fwd_7)
  quintile_btcadj_q1..q5  то же на madj_7 (партиция n=460)
  q5_minus_q1_btcadj      градиент Q5 - Q1 (madj_7)

Входы только читаются. Выход: data/bootstrap_vw_ci.csv (statistic, point, lo, hi).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DRAWS = 5000
SEED = 42


def wmedian(x, w):
    """Взвешенная медиана: сортировка по значению, не по весу."""
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    o = np.argsort(x)
    xs, ws = x[o], w[o]
    return float(xs[np.searchsorted(np.cumsum(ws), ws.sum() / 2)])


def quintile_labels(w):
    """Метки 0..4 по рангу веса; rank(method='first') гарантирует 5 бинов
    даже при дублирующихся оборотах внутри бутстрэп-драва."""
    r = pd.Series(w).rank(method='first').values
    return np.minimum((r - 1) * 5 // len(r), 4).astype(int)


def panel_stats(fwd7, madj7, madj_ok, w, delisted):
    """Все статистики для одной панели (реальной или бутстрэпной).
    fwd7, madj7 — в процентах; madj_ok — булева маска не-NaN madj_7."""
    out = {}
    vw_full = wmedian(fwd7, w)
    out['vw_median_fwd7'] = vw_full
    out['vw_median_madj7_btcadj'] = wmedian(madj7[madj_ok], w[madj_ok])
    surv = delisted == 0
    out['wedge_delisting_vw'] = wmedian(fwd7[surv], w[surv]) - vw_full
    out['ew_minus_vw'] = float(np.median(fwd7)) - vw_full

    q = quintile_labels(w)
    meds = [float(np.median(fwd7[q == i])) for i in range(5)]
    for i, m in enumerate(meds, 1):
        out[f'quintile_q{i}'] = m
    out['q5_minus_q1'] = meds[4] - meds[0]

    wb, mb = w[madj_ok], madj7[madj_ok]
    qb = quintile_labels(wb)
    meds_b = [float(np.median(mb[qb == i])) for i in range(5)]
    for i, m in enumerate(meds_b, 1):
        out[f'quintile_btcadj_q{i}'] = m
    out['q5_minus_q1_btcadj'] = meds_b[4] - meds_b[0]
    return out


def main():
    car = pd.read_csv(ROOT / 'data' / 'post_window_car.csv')
    to = pd.read_csv(ROOT / 'data' / 'day0_turnover.csv')
    df = car.merge(to, on='symbol', how='inner').dropna(subset=['fwd_7', 'usd_turnover'])
    n_full = len(df)
    n_btc = int(df.madj_7.notna().sum())
    print(f'панель: n={n_full} (BTC-adj n={n_btc}), месяцев: {df.month.nunique()}')

    fwd7 = df.fwd_7.values * 100
    madj7 = df.madj_7.values * 100
    madj_ok = df.madj_7.notna().values
    w = df.usd_turnover.clip(lower=1).values
    delisted = df.delisted.values.astype(int)

    point = panel_stats(fwd7, madj7, madj_ok, w, delisted)

    # Индексы событий по месяцам — атом resample'а.
    by_month = {m: g.index.values for m, g in df.groupby('month')}
    clusters = sorted(by_month)
    rng = np.random.default_rng(SEED)
    boots = {k: np.empty(DRAWS) for k in point}
    for b in range(DRAWS):
        pick = rng.choice(clusters, size=len(clusters), replace=True)
        idx = np.concatenate([by_month[m] for m in pick])
        s = panel_stats(fwd7[idx], madj7[idx], madj_ok[idx], w[idx], delisted[idx])
        for k, v in s.items():
            boots[k][b] = v
        if (b + 1) % 1000 == 0:
            print(f'...{b + 1}/{DRAWS}', flush=True)

    rows = []
    for k, p in point.items():
        lo, hi = np.percentile(boots[k], [2.5, 97.5])
        rows.append({'statistic': k, 'point': round(p, 2),
                     'lo': round(lo, 2), 'hi': round(hi, 2)})
    out = pd.DataFrame(rows)
    out_path = ROOT / 'data' / 'bootstrap_vw_ci.csv'
    out.to_csv(out_path, index=False)
    print(out.to_string(index=False))
    print(f'OK -> {out_path}')


if __name__ == '__main__':
    main()
