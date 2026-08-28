"""Кросс-биржевой анализ: каскад листингов Bybit->Binance и MAX-эффект."""
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats

D = Path.home() / "binance-listing-study" / "data"
L = []


def md(s=""):
    L.append(s)


binance = pd.read_csv(D / "listing_events_enriched.csv")
bybit = pd.read_csv(D / "listing_calendar_bybit.csv")
ann = pd.read_csv(D / "binance_announcements.csv") if (D / "binance_announcements.csv").exists() else None

b = binance.copy()
b["base"] = b.symbol.str.replace("USDT", "", regex=False)
bb = bybit.copy()
bb["base"] = bb.symbol.str.replace("USDT", "", regex=False)

merged = b.merge(bb[["base", "first_month", "delisted"]].rename(
    columns={"first_month": "bybit_first", "delisted": "bybit_dead"}), on="base", how="left")
merged["on_bybit"] = merged.bybit_first.notna()
md("# Cross-exchange cascades and lottery features\n")

md(f"## C1. Overlap: {int(merged.on_bybit.sum())}/{len(merged)} Binance listings "
   f"({merged.on_bybit.mean()*100:.0f}%) were also listed on Bybit\n")

both = merged.dropna(subset=["bybit_first"]).copy()
both["gap_months"] = [(pd.Period(bf, freq="M") - pd.Period(fm, freq="M")).n
                      for bf, fm in zip(both.bybit_first, both.first_month)]
n_binance_first = int((both.gap_months < 0).sum())
n_bybit_first = int((both.gap_months > 0).sum())
n_same = int((both.gap_months == 0).sum())
md(f"| Порядок | N | Медианный fwd_7 % |\n|---|---|---|")
for name, sub in [("Bybit first", both[both.gap_months < 0]),
                  ("same month", both[both.gap_months == 0]),
                  ("Binance first", both[both.gap_months > 0])]:
    md(f"| {name} | {len(sub)} | {sub.fwd_7.median()*100:+.1f} |")
mw = stats.mannwhitneyu(
    both[both.gap_months <= 0].fwd_7.dropna(),
    both[both.gap_months > 0].fwd_7.dropna()).pvalue if n_bybit_first > 10 else np.nan
md(f"\nMann-Whitney p (Bybit-first vs Binance-first-or-same-month): {mw:.3f}\n")

# MAX-эффект на Binance выборке
md("## C2. Lottery/MAX features (first week daily extremes)\n")
m7 = binance[["max_daily_7d", "min_daily_7d", "fwd_30"]].dropna()
q = pd.qcut(m7.max_daily_7d, 3, labels=["низкий MAX", "средний", "высокий MAX"])
tab = m7.groupby(q, observed=True).agg(max_d=("max_daily_7d", "median"), fwd30=("fwd_30", "median")) * 100
md("| MAX-квартиль первой недели | медиана max дневной % | медиана fwd_30 % |")
md("|---|---|---|")
for i, r in tab.iterrows():
    md(f"| {i} | {r.max_d:+.1f} | {r.fwd30:+.1f} |")
corr = m7.max_daily_7d.corr(m7.fwd_30)
md(f"\nКорреляция max_daily_7d -> fwd_30: {corr:+.3f}\n")

out_md = "\n".join(L)
(Path.home() / "binance-listing-study" / "paper" / "cross_exchange.md").write_text(out_md)
print(out_md)
