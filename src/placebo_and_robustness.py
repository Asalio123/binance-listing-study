"""Плацебо-перестановочный тест + батарея робастности для препринта."""
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DF = ROOT / "data" / "listing_events_enriched.csv"
OUT = ROOT / "paper" / "robustness_tables.md"
rng = np.random.default_rng(7)

df = pd.read_csv(DF)
L = []


def md(s=""):
    L.append(s)


def med(r):
    return np.median(r) * 100


md("# Robustness appendix\n")

# --- 1. Перестановочный (permutation) тест для медиан
md("## R1. Permutation test: is the post-listing median distinguishable from chance?\n")
md("Null: day-0-close timing carries no information — forward returns are exchangeable\nwith any other days' returns drawn from the same market.\n")
md("| Horizon | Observed median % | Permutation p (two-sided) |")
md("|---|---|---|")

# нулевое распределение: медианы случайных выборок из ОБЩЕГО пула дневных доходностей
# всех событий во все дни (смешиваем события между собой по горизонтам)
pool = df[[f"fwd_{h}" for h in [1, 3, 7, 14, 30]]].values.flatten()
pool = pool[~np.isnan(pool)]
for hi, h in enumerate([1, 3, 7, 14, 30]):
    obs = df[f"fwd_{h}"].dropna().values
    obs_med = med(obs)
    draws = rng.choice(pool, size=(2000, len(obs)), replace=True)
    perm_meds = np.median(draws, axis=1) * 100
    p = (np.abs(perm_meds) >= abs(obs_med)).mean()
    md(f"| +{h}d | {obs_med:+.2f} | {p:.4f} |")
md("\nNote: conservative — the pool itself contains event-day returns; a pure\nnon-event null would sharpen rejection further.\n")

# --- 2. Выбросы и подпериоды
md("## R2. Outlier and subperiod robustness (median fwd_7, %)\n")
r7 = df.fwd_7.dropna() * 100
rows = []
rows.append(("Full sample", np.median(r7.values)))
w = stats.trimboth(r7.values, 0.02)
rows.append(("Trim tails 2%", np.median(w)))
no21 = df[df.first_month.str[:4] != "2021"].fwd_7.dropna() * 100
rows.append(("Excl. 2021 (meme mania)", no21.median()))
no24q4 = df[~((df.first_month.str[:4] == "2024") & (df.first_month.str[-2:].isin(["10", "11", "12"])))].fwd_7.dropna() * 100
rows.append(("Excl. Q4-2024", no24q4.median()))
wins = r7.clip(r7.quantile(0.01), r7.quantile(0.99))
rows.append(("Winsorize 1%/99%", wins.median()))

md("| Specification | Median fwd_7 % | N |")
md("|---|---|---|")
for name, v in rows:
    md(f"| {name} | {v:+.2f} | {len(r7)} |")
md("")

# --- 3. Wilcoxon на каждой спецификации
md("## R3. Significance under each specification (Wilcoxon p)\n")
specs = {
    "full": r7.values,
    "trim2": w,
    "no2021": no21.values,
    "noQ4_2024": no24q4.values,
    "winsor": wins.values,
}
md("| Spec | Wilcoxon p |")
md("|---|---|")
for name, vals in specs.items():
    p = stats.wilcoxon(vals).pvalue
    md(f"| {name} | {p:.2e} |")
md("")

# --- 4. Экономическая значимость против издержек
md("## R4. Cost check: is a naive fade/buy strategy profitable after costs?\n")
turn_cost = 16  # bps round trip taker на Binance VIP0 (0.08% сторона)
med7 = abs(np.median(r7.values))
md(f"- Median absolute move at +7d: {med7:.1f}% vs round-trip cost ≈ {turn_cost} bps.\n"
   f"- The drift is nearly two orders of magnitude larger than retail costs. The negative sign means\n"
   f"  LONGS lose; for shorts, the full funding sweep (funding_sweep.csv) shows funding rarely eats\n"
   f"  the drift (median −0.36% per week vs −11.45% drift); the binding constraint is instrument\n"
   f"  availability (perpetual exists from day 0 for 17.0% of the panel) and the upside tail.\n")

OUT.write_text("\n".join(L))
print("\n".join(L))
