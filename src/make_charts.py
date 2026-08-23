"""Генерирует графики для README репозитория binance-listing-study."""
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATA = Path.home() / "[private-repo]" / "data"
REPO = Path.home() / "binance-listing-study" / "charts"
REPO.mkdir(exist_ok=True)

plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117", "axes.edgecolor": "#30363d",
                     "axes.labelcolor": "#c9d1d9", "text.color": "#c9d1d9", "xtick.color": "#8b949e",
                     "ytick.color": "#8b949e", "font.size": 11, "grid.color": "#21262d"})

ev = pd.read_csv(DATA / "listing_event_returns.csv")
cal = pd.read_csv(Path.home() / "binance-listing-study" / "data" / "listing_calendar_binance.csv")

# 1. Медианная траектория после листинга
horizons = ["fwd_1", "fwd_3", "fwd_7", "fwd_14", "fwd_30"]
labels = ["+1д", "+3д", "+7д", "+14д", "+30д"]
med = ev[horizons].median() * 100
pos = (ev[horizons] > 0).mean() * 100
fig, ax = plt.subplots(figsize=(9, 5))
colors = ["#f85149" if v < 0 else "#3fb950" for v in med]
bars = ax.bar(labels, med, color=colors, alpha=0.85)
for b, p in zip(bars, pos):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{p:.0f}% в плюсе",
            ha="center", va="bottom" if b.get_height() >= 0 else "top", fontsize=10, color="#8b949e")
ax.axhline(0, color="#30363d")
ax.set_title(f"Что происходит после первого дня листинга Binance (n={len(ev)}, включая делистнутые)")
ax.set_ylabel("Медианная доходность от закрытия дня 0, %")
plt.tight_layout()
plt.savefig(REPO / "post_listing_drift.png", dpi=130)
plt.close()

# 2. Градиент: сила пампа -> глубина слива
ev["bucket"] = pd.qcut(ev.pop_day0, 4, labels=["слабый\nпамп", "средний", "сильный", "безумный"])
g = ev.groupby("bucket", observed=True).agg(pop=("pop_day0", "median"), fwd7=("fwd_7", "median")) * 100
fig, ax = plt.subplots(figsize=(9, 5))
x = range(len(g))
ax.bar([i - 0.2 for i in x], g["pop"], width=0.4, label="памп дня 0 (медиана)", color="#58a6ff", alpha=0.85)
ax.bar([i + 0.2 for i in x], g["fwd7"], width=0.4, label="+7 дней (медиана)", color="#f85149", alpha=0.85)
ax.set_xticks(list(x))
ax.set_xticklabels(g.index)
ax.axhline(0, color="#30363d")
ax.legend(frameon=False)
ax.set_title("Чем сильнее памп в день листинга — тем жёстче слив на неделе")
ax.set_ylabel("%")
plt.tight_layout()
plt.savefig(REPO / "pop_fade_gradient.png", dpi=130)
plt.close()

# 3. Листинги по годам + доля делистнутых
usdt = cal[cal.symbol.str.endswith("USDT") & (cal.first_month >= "2021-01")].copy()
usdt["year"] = usdt.first_month.str[:4]
yearly = usdt.groupby("year").agg(total=("symbol", "size"), dead=("delisted", "sum"))
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(yearly.index, yearly["total"], color="#238636", alpha=0.8, label="листингов USDT")
ax.bar(yearly.index, yearly["dead"], color="#f85149", alpha=0.8, label="из них уже делистнуто")
ax.set_title("Новые листинги Binance по годам и их смертность")
ax.legend(frameon=False)
ax.set_ylabel("штук")
plt.tight_layout()
plt.savefig(REPO / "listings_per_year.png", dpi=130)
plt.close()

print("OK:", list(p.name for p in REPO.glob('*.png')))
