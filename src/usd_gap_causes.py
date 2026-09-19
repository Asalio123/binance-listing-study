from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent

df = pd.read_csv(ROOT / 'data' / 'listing_events_enriched.csv')
to = pd.read_csv(ROOT / 'data' / 'day0_turnover.csv')
d = df.merge(to, on='symbol', how='inner').dropna(subset=['fwd_7', 'usd_turnover', 'pop_day0', 'range_day0']).copy()
d['log_to'] = np.log(d['usd_turnover'].clip(lower=1))
d['lm'] = pd.to_datetime(d.first_month + '-01')
d['year'] = d.lm.dt.year

print('=== M0: базовые квинтили оборота ===')
d['q'] = pd.qcut(d.usd_turnover, 5, labels=['Q1 низкий', 'Q2', 'Q3', 'Q4', 'Q5 высокий'])
g = d.groupby('q', observed=True).agg(
    n=('fwd_7', 'size'),
    med_f7=('fwd_7', lambda x: x.median() * 100),
    med_f30=('fwd_30', lambda x: x.median() * 100),
    med_pop=('pop_day0', lambda x: x.median() * 100),
    med_range=('range_day0', lambda x: x.median() * 100),
    med_annvol=('ann_vol_7d', lambda x: x.median() * 100),
    share_pos=('fwd_7', lambda x: (x > 0).mean() * 100),
)
print(g.round(2).to_string())
sp = stats.spearmanr(d.log_to, d.fwd_7)
print(f'\nSpearman(log turnover, fwd_7): rho={sp.statistic:+.3f}, p={sp.pvalue:.2e}')

print('\n=== M1: turnover <-> pop/range/max ===')
for col, lab in [('pop_day0', 'pop'), ('range_day0', 'range'), ('max_daily_7d', 'max_daily'), ('ann_vol_7d', 'ann_vol')]:
    s = stats.spearmanr(d.log_to, d[col], nan_policy='omit')
    print(f'Spearman(log_to, {lab}): rho={s.statistic:+.3f}, p={s.pvalue:.1e}')

def ols(Xv, yv):
    beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
    resid = yv - Xv @ beta
    s2 = resid @ resid / (len(yv) - Xv.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(Xv.T @ Xv)))
    return beta, beta / se

print('\n=== M1/M3: OLS fwd_7 ~ controls + log_turnover ===')
sub = d.dropna(subset=['ann_vol_7d']).copy()
X = np.column_stack([
    np.ones(len(sub)),
    np.log1p(sub.pop_day0.clip(lower=-0.99)),
    np.log(sub.range_day0.clip(lower=1e-6)),
    sub.ann_vol_7d.fillna(sub.ann_vol_7d.median()),
])
y = sub.fwd_7.values * 100
b0, t0 = ols(X, y)
X2 = np.column_stack([X, sub.log_to.values])
b1, t1 = ols(X2, y)
print(f'без turnover:      R^2={1 - ((y - X@b0)**2).sum()/((y-y.mean())**2).sum():.4f}')
print(f'с log_turnover:    b_logTO={b1[4]:+.2f} pp, t={t1[4]:+.2f} '
      f'(log_range b={b1[2]:+.2f} t={t1[2]:+.2f}; log_pop b={b1[1]:+.2f} t={t1[1]:+.2f})')
print(f'R^2 с turnover:    {1 - ((y - X2@b1)**2).sum()/((y-y.mean())**2).sum():.4f}')

print('\n=== M2: профиль по годам ===')

def ew_vw(dd):
    x = dd.fwd_7.values * 100
    w = dd.usd_turnover.clip(lower=1).values
    o = np.argsort(x)
    cw = np.cumsum(w[o])
    vw = float(x[o][np.searchsorted(cw, w.sum() / 2)])
    return float(np.median(x)) - vw

for y_, row in d.groupby('year').agg(n=('fwd_7', 'size'),
                                     med_f7=('fwd_7', lambda x: x.median() * 100),
                                     med_to=('usd_turnover', lambda x: x.median() / 1e6)).iterrows():
    dd = d[d.year == y_]
    vw_med = None
    x = dd.fwd_7.values * 100
    w = dd.usd_turnover.clip(lower=1).values
    o = np.argsort(x)
    vw_med = float(x[o][np.searchsorted(np.cumsum(w[o]), w.sum() / 2)])
    print(f'{y_}: n={row.n:3.0f} | медиана fwd_7 {row.med_f7:+7.2f}% | USD-VW {vw_med:+7.2f}% | медианный оборот {row.med_to:6.1f} млн$')

print('\n=== M4: разрыв без топ-5 весов и по подпериодам ===')
print(f'полная панель:            EW-VW = {ew_vw(d):+.2f} pp')
top5 = d.nlargest(5, 'usd_turnover').symbol.tolist()
d_no5 = d[~d.symbol.isin(top5)]
print(f'без топ-5 весов ({",".join(top5)}): EW-VW = {ew_vw(d_no5):+.2f} pp')
for lo, hi in [('2021', '2022'), ('2023', '2026')]:
    seg = d[(d.year >= int(lo)) & (d.year <= int(hi))]
    print(f'{lo}-{hi} (n={len(seg)}):          EW-VW = {ew_vw(seg):+.2f} pp')

print('\n=== состав топ-дециля оборота ===')
top = d.nlargest(47, 'usd_turnover')
print('медиана fwd_7 топ-дециля:', round(top.fwd_7.median() * 100, 2), '%')
print(top.nlargest(12, 'usd_turnover')[['symbol', 'first_month', 'usd_turnover', 'fwd_7']].assign(
    usd_mln=lambda x: (x.usd_turnover / 1e6).round(0), f7=lambda x: (x.fwd_7 * 100).round(1)
)[['symbol', 'first_month', 'usd_mln', 'f7']].to_string(index=False))
