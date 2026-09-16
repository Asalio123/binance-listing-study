"""Survivorship simulation: how a live-API snapshot distorts the listing panel.

For a monthly grid of dates T (2022-01 -> 2026-08) rebuild the panel as a
live-API user would have seen it at T: events with day0 < T, minus all events
whose history ended before T (last_date < T, i.e. already delisted/silent).
Compare against the death-inclusive panel of the same events and measure the
bias in median fwd_7 / fwd_30 and the USD-weighted median fwd_7.

Weighted median sorts by VALUE (not by weight) and takes the smallest value
where cumulative weight >= 50% -- same pattern as wmedian in bybit_holdout.py.
"""
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path.home() / "binance-listing-study"
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

RED, BLUE, GRAY = "#c0392b", "#2471a3", "#7f8c8d"


def wmedian(x, w):
    o = np.argsort(x)
    xs, ws = np.asarray(x, dtype=float)[o], np.asarray(w, dtype=float)[o]
    cw = np.cumsum(ws)
    return float(xs[np.searchsorted(cw, ws.sum() / 2)])


ev = pd.read_csv(DATA / "listing_events_enriched.csv")
to = pd.read_csv(DATA / "day0_turnover.csv")
df = ev.merge(to, on="symbol", how="inner").copy()
df["day0_date"] = pd.to_datetime(df["day0_date"])
df["last_date"] = pd.to_datetime(df["last_date"])
df["w"] = df["usd_turnover"].clip(lower=1)
print(f"panel: {len(df)} events, day0 {df.day0_date.min().date()} -> "
      f"{df.day0_date.max().date()}, delisted={int(df.delisted.sum())}", flush=True)

grid = pd.date_range("2022-01-01", "2026-08-01", freq="MS")
rows = []
for T in grid:
    full = df[df.day0_date < T]
    live = full[full.last_date >= T]

    def stats(p):
        f7 = p.fwd_7.dropna()
        f30 = p.fwd_30.dropna()
        if len(f7) == 0:
            return dict(n=0, med_f7=np.nan, med_f30=np.nan, pct_pos7=np.nan, vw_f7=np.nan)
        p7 = p.loc[f7.index]
        return dict(
            n=len(p),
            med_f7=float(f7.median()) * 100,
            med_f30=float(f30.median()) * 100 if len(f30) else np.nan,
            pct_pos7=float((f7 > 0).mean()) * 100,
            vw_f7=wmedian(f7.values * 100, p7["w"].values),
        )

    s_full, s_live = stats(full), stats(live)
    rows.append({
        "T": T.date().isoformat(),
        "n_full": s_full["n"], "n_live": s_live["n"],
        "med_f7_full": s_full["med_f7"], "med_f7_live": s_live["med_f7"],
        "bias_pp": s_live["med_f7"] - s_full["med_f7"],
        "med_f30_full": s_full["med_f30"], "med_f30_live": s_live["med_f30"],
        "bias30_pp": s_live["med_f30"] - s_full["med_f30"],
        "vw_f7_full": s_full["vw_f7"], "vw_f7_live": s_live["vw_f7"],
        "vw_bias_pp": s_live["vw_f7"] - s_full["vw_f7"],
        "pct_pos7_full": s_full["pct_pos7"], "pct_pos7_live": s_live["pct_pos7"],
        "share_dropped": 1 - s_live["n"] / s_full["n"] if s_full["n"] else np.nan,
    })

res = pd.DataFrame(rows)
res.to_csv(DATA / "survivorship_simulation.csv", index=False, float_format="%.4f")
print(f"saved data/survivorship_simulation.csv ({len(res)} rows)", flush=True)

# --- verification against the headline number ------------------------------
tail = res.iloc[-1]
raw_med = float(df.fwd_7.median()) * 100
print(f"verify T={tail['T']}: n_full={int(tail.n_full)} (expect 470), "
      f"med_f7_full={tail.med_f7_full:.2f}% vs raw panel median={raw_med:.2f}%",
      flush=True)
assert int(tail.n_full) == 470, "n_full at T=2026-08 != 470"
assert abs(tail.med_f7_full - raw_med) < 1e-6, "full-panel median mismatch"

# --- chart ------------------------------------------------------------------
x = pd.to_datetime(res["T"])
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(x, res["bias_pp"], color=RED, linewidth=1.6, marker="o", markersize=2.5,
        label="EW median fwd_7 bias (pp)")
ax.plot(x, res["vw_bias_pp"], color=BLUE, linewidth=1.6, linestyle="--",
        label="USD-weighted median fwd_7 bias (pp)")
ax.axhline(0, color="#444444", linewidth=0.8)
ax.set_ylabel("Live-API median minus full-panel median (pp)")
ax2 = ax.twinx()
ax2.fill_between(x, res["share_dropped"] * 100, color=GRAY, alpha=0.25)
ax2.set_ylabel("Share of events dropped (%)", color="#555555")
ax2.tick_params(axis="y", colors="#555555")
ax2.grid(False)
h1, l1 = ax.get_legend_handles_labels()
from matplotlib.patches import Patch
h1.append(Patch(facecolor=GRAY, alpha=0.25))
l1.append("Share dropped (right axis)")
ax.legend(h1, l1, frameon=False, loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(CHARTS / "survivorship_bias_curve.png", dpi=300)
plt.close(fig)
print("saved charts/survivorship_bias_curve.png", flush=True)

# --- anchor points for the report -------------------------------------------
for t in ["2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01", "2026-08-01"]:
    r = res[res["T"] == t].iloc[0]
    print(f"T={t}: n {int(r.n_live)}/{int(r.n_full)} "
          f"(dropped {r.share_dropped*100:.1f}%), "
          f"med_f7 {r.med_f7_live:+.2f}% vs {r.med_f7_full:+.2f}% -> bias {r.bias_pp:+.2f} pp, "
          f"vw bias {r.vw_bias_pp:+.2f} pp, bias30 {r.bias30_pp:+.2f} pp", flush=True)

first_sign = res[res.bias_pp > 0.5]["T"].min()
print(f"first T with bias > +0.5 pp: {first_sign}", flush=True)
print(f"bias range: {res.bias_pp.min():+.2f} .. {res.bias_pp.max():+.2f} pp; "
      f"vw bias range: {res.vw_bias_pp.min():+.2f} .. {res.vw_bias_pp.max():+.2f} pp",
      flush=True)
