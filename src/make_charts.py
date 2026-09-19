"""Publication figures for the binance-listing-study preprint (English, light theme)."""
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
CHARTS = REPO / "charts"
CHARTS.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#111111",
    "text.color": "#111111",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "font.size": 11,
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
})

RED, BLUE, GREEN, GRAY = "#c0392b", "#2471a3", "#1e8449", "#7f8c8d"

ev = pd.read_csv(DATA / "listing_events_enriched.csv")
to = pd.read_csv(DATA / "day0_turnover.csv")
pw = pd.read_csv(DATA / "post_window_car.csv")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(CHARTS / name, dpi=300)
    plt.close(fig)
    print("saved", name)


# --- Fig 1: listings per year + mortality -----------------------------------
usdt = ev.copy()
usdt["year"] = usdt.first_month.str[:4]
yearly = usdt.groupby("year").agg(total=("symbol", "size"), dead=("delisted", "sum"))
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.bar(yearly.index, yearly["total"], color=BLUE, alpha=0.85, label="USDT listings")
ax.bar(yearly.index, yearly["dead"], color=RED, alpha=0.85, label="already delisted")
ax.set_ylabel("Number of listings")
ax.legend(frameon=False)
save(fig, "listings_per_year.png")

# --- Fig 2: post-listing drift -----------------------------------------------
horizons = ["fwd_1", "fwd_3", "fwd_7", "fwd_14", "fwd_30"]
labels = ["+1d", "+3d", "+7d", "+14d", "+30d"]
med = ev[horizons].median() * 100
pos = (ev[horizons] > 0).mean() * 100
fig, ax = plt.subplots(figsize=(8, 4.2))
bars = ax.bar(labels, med, color=[RED if v < 0 else GREEN for v in med], alpha=0.85, width=0.62)
for b, p, m in zip(bars, pos, med):
    ax.text(b.get_x() + b.get_width() / 2, m, f"{p:.0f}% positive",
            ha="center", va="bottom" if m >= 0 else "top", fontsize=10, color="#555555")
ax.axhline(0, color="#444444", linewidth=0.8)
ax.set_ylabel("Median return from day-0 close (%)")
ax.set_ylim(min(med) * 1.25, 4)
save(fig, "post_listing_drift.png")

# --- Fig 3: pop vs fade gradient ---------------------------------------------
ev["bucket"] = pd.qcut(ev.pop_day0, 4,
                       labels=["weakest\npop", "Q2", "Q3", "strongest\npop"])
g = ev.groupby("bucket", observed=True).agg(pop=("pop_day0", "median"),
                                            fwd7=("fwd_7", "median")) * 100
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(g))
ax.bar(x - 0.2, g["pop"], width=0.4, label="Day-0 pop (median)", color=BLUE, alpha=0.85)
ax.bar(x + 0.2, g["fwd7"], width=0.4, label="+7 days (median)", color=RED, alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(g.index)
ax.axhline(0, color="#444444", linewidth=0.8)
ax.legend(frameon=False)
ax.set_ylabel("%")
save(fig, "pop_fade_gradient.png")

# --- Fig 4: token-typical vs dollar-typical week one -------------------------
d = pw.merge(to, on="symbol").dropna(subset=["madj_7"]).copy()


def vw_median(x, w):
    o = np.argsort(x)
    xs, ws = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(ws)
    return float(xs[np.searchsorted(cw, ws.sum() / 2)])


ew_m = float(d.madj_7.median()) * 100
vw_m = vw_median(d.madj_7.values * 100, d.usd_turnover.clip(lower=1).values)
raw_ew = float(ev.fwd_7.median()) * 100
raw_vw = None
dv = ev.merge(to, on="symbol").dropna(subset=["fwd_7"])
raw_vw = vw_median(dv.fwd_7.values * 100, dv.usd_turnover.clip(lower=1).values)

fig, ax = plt.subplots(figsize=(8, 4.2))
cats = ["Token-counted\n(equal weight)", "Dollar-weighted\n(day-0 turnover)"]
raw_vals = [raw_ew, raw_vw]
adj_vals = [ew_m, vw_m]
x = np.arange(2)
ax.bar(x - 0.2, raw_vals, width=0.38, label="Raw returns", color=BLUE, alpha=0.85)
ax.bar(x + 0.2, adj_vals, width=0.38, label="BTC-adjusted", color=RED, alpha=0.85)
for xi, v in zip(x - 0.2, raw_vals):
    ax.text(xi, v - 1.5, f"{v:+.1f}%", ha="center", va="top", fontsize=11, fontweight="bold")
for xi, v in zip(x + 0.2, adj_vals):
    ax.text(xi, v - 1.5, f"{v:+.1f}%", ha="center", va="top", fontsize=11, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(cats)
ax.axhline(0, color="#444444", linewidth=0.8)
ax.legend(frameon=False)
ax.set_ylabel("Median week-one return (%)")
ax.set_ylim(min(raw_vals + adj_vals) * 1.18, 2)
save(fig, "dollar_vs_token.png")

# --- Fig 5: fade monotone in day-0 turnover ----------------------------------
d["q"] = pd.qcut(d.usd_turnover, 5,
                 labels=["Q1\nlowest", "Q2", "Q3", "Q4", "Q5\nhighest"])
q = d.groupby("q", observed=True).agg(madj=("madj_7", lambda x: x.median() * 100),
                                      n=("madj_7", "size"))
fig, ax = plt.subplots(figsize=(8, 4.2))
bars = ax.bar(q.index.astype(str), q["madj"], color=RED, alpha=0.85, width=0.6)
for b, v in zip(bars, q["madj"]):
    ax.text(b.get_x() + b.get_width() / 2, v - 1.2, f"{v:+.1f}%",
            ha="center", va="top", fontsize=11, fontweight="bold")
ax.axhline(0, color="#444444", linewidth=0.8)
ax.set_ylabel("Median BTC-adjusted return,\nfirst week (%)")
ax.set_xlabel("Day-0 USD turnover quintile")
ax.set_ylim(q["madj"].min() * 1.22, 3)
save(fig, "turnover_quintiles.png")

print("OK:", sorted(p.name for p in CHARTS.glob("*.png")))
