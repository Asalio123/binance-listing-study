"""Генератор charts/announcement_premium.png из data/announcement_premium_coinbase.csv.

Читает CSV напрямую (медианы и %positive считаются из данных, не зашиты).
Стиль: как src/make_charts.py (DejaVu Serif, светлая тема, BLUE/RED).

История: фигура волны 1 несла аннотации %positive, никогда не совпадавшие с CSV
(53/65/63/20 вместо вычисляемых 77.8/87.9/80.6/21.8); аудит 2026-09-23 (V5)
поймал расхождение, генератора в репо не было — этот скрипт закрывает оба.

Запуск: python3 src/make_announcement_premium_chart.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
CHARTS = REPO / "charts"

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
    "axes.grid": False,
})
RED, BLUE = "#c0392b", "#2471a3"

df = pd.read_csv(DATA / "announcement_premium_coinbase.csv")
windows = [
    ("pre7", "7 days before"),
    ("pre3", "3 days before"),
    ("pre1", "day before"),
    ("post7", "7 days after"),
]
meds, poss, ns = [], [], []
for col, _ in windows:
    s = df[col].dropna()
    meds.append(s.median() * 100)
    poss.append(100 * (s > 0).mean())
    ns.append(len(s))

fig, ax = plt.subplots(figsize=(8, 5))
colors = [BLUE if m >= 0 else RED for m in meds]
bars = ax.bar(range(4), meds, color=colors, width=0.62, zorder=3)
ax.axhline(0, color="#444444", lw=1)

for i, (m, p, n) in enumerate(zip(meds, poss, ns)):
    # медиана над/под баром жирным
    off = 1.5 if m >= 0 else -1.5
    va = "bottom" if m >= 0 else "top"
    ax.text(i, m + off, f"{m:+.1f}%", ha="center", va=va,
            fontsize=12, fontweight="bold")
    # %positive и n у нижнего края, в две строки, без налезания
    ax.text(i, -44.5, f"{p:.1f}% positive", ha="center", va="top",
            fontsize=10, color="#555555")
    ax.text(i, -50.5, f"n={n}", ha="center", va="top",
            fontsize=10, color="#555555")

ax.set_xticks(range(4))
ax.set_xticklabels([lab for _, lab in windows], fontsize=11)
ax.set_ylim(-55, 47)
ax.set_ylabel("Median return on Coinbase, %")
ax.set_title("Returns around Binance announcement timestamps, 79 cross-listed events\n"
             "(prices on Coinbase, where the token already traded)", fontsize=12)
ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
fig.savefig(CHARTS / "announcement_premium.png", dpi=300)
plt.close(fig)
print("saved announcement_premium.png; annotations:",
      [f"{p:.1f}% pos (n={n})" for p, n in zip(poss, ns)],
      "; medians:", [f"{m:+.1f}%" for m in meds])
