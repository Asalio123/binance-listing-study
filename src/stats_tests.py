"""Статистические тесты для препринта: t-тесты, bootstrap CI, Wilcoxon, регрессия, подпериоды."""
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DF = ROOT / "data" / "listing_events_enriched.csv"
OUT = ROOT / "paper" / "stats_tables.md"
rng = np.random.default_rng(42)

df = pd.read_csv(DF)
HORIZONS = [1, 3, 7, 14, 30]
lines = []


def md(s=""):
    lines.append(s)


md("# Statistical appendix (auto-generated)\n")

# --- 1. Mean t-tests + Wilcoxon per horizon
md("## Table S1. Forward returns from day-0 close\n")
md("| Horizon | N | Median % | Mean % | t-stat | p(mean≠0) | Wilcoxon p | %>0 |")
md("|---|---|---|---|---|---|---|---|")
for h in HORIZONS:
    r = df[f"fwd_{h}"].dropna() * 100
    t, p = stats.ttest_1samp(r, 0)
    w = stats.wilcoxon(r, alternative="two-sided").pvalue if len(r) > 20 else np.nan
    md(f"| +{h}d | {len(r)} | {r.median():+.2f} | {r.mean():+.2f} | {t:.2f} | {p:.2e} | {w:.2e} | {(r>0).mean()*100:.1f}% |")
md("")

# --- 2. Bootstrap CI for medians
md("## Table S2. Bootstrap 95% CI of median forward returns (10k resamples)\n")
md("| Horizon | Median % | 2.5% | 97.5% | CI excludes 0 |")
md("|---|---|---|---|---|")
for h in HORIZONS:
    r = df[f"fwd_{h}"].dropna().values * 100
    boots = np.median(rng.choice(r, size=(10000, len(r))), axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    excl = "yes" if (lo > 0 or hi < 0) else "no"
    md(f"| +{h}d | {np.median(r):+.2f} | {lo:+.2f} | {hi:+.2f} | {excl} |")
md("")

# --- 3. Pop-fade gradient: quartile test + OLS
md("## Table S3. Cross-sectional regression: fwd_7 ~ pop_day0 controls\n")
sub = df[["fwd_7", "pop_day0", "range_day0", "quote_vol_day0", "delisted", "ann_vol_7d"]].dropna()
X = pd.DataFrame({
    "const": 1.0,
    "log_pop": np.log1p(sub.pop_day0.clip(lower=-0.99)),
    "log_range": np.log(sub.range_day0.clip(lower=1e-6)),
    "log_vol": np.log(sub.quote_vol_day0.clip(lower=1)),
    "ann_vol": sub.ann_vol_7d.fillna(sub.ann_vol_7d.median()),
    "delisted": sub.delisted,
})
y = sub.fwd_7 * 100
Xv, yv = X.values, y.values
beta, res_, rank, _ = np.linalg.lstsq(Xv, yv, rcond=None)
resid = yv - Xv @ beta
sigma2 = resid @ resid / (len(yv) - Xv.shape[1])
se = np.sqrt(np.diag(sigma2 * np.linalg.inv(Xv.T @ Xv)))
tstats = beta / se
pv = 2 * (1 - stats.t.cdf(np.abs(tstats), df=len(yv) - Xv.shape[1]))
md("| Term | Coef (pp) | t-stat | p-value |")
md("|---|---|---|---|")
for name, b, t_, p_ in zip(X.columns, beta, tstats, pv):
    md(f"| {name} | {b*1:+.2f} | {t_:.2f} | {p_:.3g} |")
md(f"\nN={len(yv)}, R²={1 - resid@resid/((yv-yv.mean())@(yv-yv.mean())):.4f}\n")

# --- 4. Subperiod halves for key horizons
md("## Table S4. Split-half stability of median fwd returns (%)\n")
mid_date = df.first_month.sort_values().iloc[len(df) // 2]
first_half = df[df.first_month < mid_date]
second_half = df[df.first_month >= mid_date]
md("| Horizon | 1st half median | 2nd half median |")
md("|---|---|---|")
for h in [7, 30]:
    a = first_half[f"fwd_{h}"].dropna() * 100
    b = second_half[f"fwd_{h}"].dropna() * 100
    mw = stats.mannwhitneyu(a, b).pvalue
    md(f"| +{h}d | {a.median():+.2f} | {b.median():+.2f} | (Mann-Whitney p={mw:.3f}) |")
md("")

# --- 5. Survivorship quantification
md("## Table S5. Delisted vs surviving listings (median %)\n")
md("| Horizon | Surviving | Delisted | Diff |")
md("|---|---|---|---|")
for h in [7, 30]:
    a = df[df.delisted == 0][f"fwd_{h}"].dropna() * 100
    b = df[df.delisted == 1][f"fwd_{h}"].dropna() * 100
    md(f"| +{h}d | {a.median():+.2f} | {b.median():+.2f} | {a.median()-b.median():+.2f} |")
md("\nA survivor-only sample (excluding delisted) shifts the median fwd_7 by "
   f"{df[df.delisted==0].fwd_7.median()*100 - df.fwd_7.median()*100:+.2f} pp "
   f"({len(df)} -> {int((df.delisted==0).sum())} events).\n")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text("\n".join(lines))
print("\n".join(lines))
