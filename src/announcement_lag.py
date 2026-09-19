"""Лаг анонс->листинг как treatment: отличается ли фейд по группам лага.

Входы:
  data/announcement_dates.csv      (symbol, announce_ts_utc — точность до минуты)
  data/listing_events_enriched.csv (symbol, fwd_7, fwd_30, pop_day0, trunc_*)
  data/day0_turnover.csv           (symbol, day0_date)
Лаг = day0_date - announce_date в календарных днях (первичная мера: время
листинга внутри дня нам неизвестно, календарный день робастен). Дополнительно
считаем часы от анонса до 00:00 UTC дня day0 — это НИЖНЯЯ оценка истинного
лага в часах (листинг внутри дня, обычно позже полуночи).
Группы: same-day (0 дн) / 1 день / 2-7 дней / >7 дней.
Отрицательные лаги (анонс позже даты day0 — артефакты rebrand/шума) -
флагируются и исключаются из групповых тестов.
Тест: Mann-Whitney same-day vs lag>=1d (двусторонний), вторично same-day vs >7d.
Выход: data/announcement_lag_analysis.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "announcement_lag_analysis.csv"


def lag_group(d):
    if d == 0:
        return "same-day"
    if d == 1:
        return "1d"
    if d <= 7:
        return "2-7d"
    return ">7d"


def mw(a, b):
    a, b = a.dropna(), b.dropna()
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan
    r = stats.mannwhitneyu(a, b)
    return r.statistic, r.pvalue


def main():
    enr = pd.read_csv(ROOT / "data" / "listing_events_enriched.csv")
    ann = pd.read_csv(ROOT / "data" / "announcement_dates.csv")
    turn = pd.read_csv(ROOT / "data" / "day0_turnover.csv")
    turn = turn[turn.symbol.isin(enr.symbol)]  # 1INCHUP/DOWN вне панели

    df = enr.merge(ann[["symbol", "announce_ts_utc", "confidence"]], on="symbol", how="left")
    df = df.merge(turn[["symbol", "day0_date"]], on="symbol", how="left")
    print(f"Панель: {len(df)}, с анонсом: {df.announce_ts_utc.notna().sum()}", flush=True)

    df["announce_ts"] = pd.to_datetime(df.announce_ts_utc, utc=True)
    df["day0_ts"] = pd.to_datetime(df.day0_date, utc=True)
    df["lag_days"] = (df.day0_ts.dt.normalize() - df.announce_ts.dt.normalize()).dt.days
    df["lag_hours_to_midnight"] = (df.day0_ts - df.announce_ts).dt.total_seconds() / 3600

    neg = df[df.lag_days < 0]
    print(f"Отрицательный лаг (исключены из тестов): {len(neg)}", flush=True)
    for _, r in neg.iterrows():
        print(f"  NEG {r.symbol} ann={r.announce_ts_utc} day0={r.day0_date} conf={r.confidence}", flush=True)

    df["lag_group"] = df.lag_days.map(lambda d: lag_group(d) if pd.notna(d) and d >= 0 else np.nan)
    noann = df[df.announce_ts_utc.isna()].symbol.tolist()
    print(f"Без даты анонса: {noann}", flush=True)

    cols = ["symbol", "announce_ts_utc", "confidence", "day0_date", "lag_days",
            "lag_hours_to_midnight", "lag_group", "pop_day0", "fwd_7", "fwd_30",
            "trunc_7", "trunc_30"]
    df[cols].to_csv(OUT, index=False)
    print(f"Записано {OUT}", flush=True)

    g = df.dropna(subset=["lag_group"])
    print(f"\nВ групповых тестах: {len(g)}", flush=True)
    order = ["same-day", "1d", "2-7d", ">7d"]
    print("\n=== Медианы по группам лага ===", flush=True)
    rows = []
    for grp in order:
        s = g[g.lag_group == grp]
        rows.append({
            "group": grp, "n": len(s),
            "med_fwd_7": s.fwd_7.median() * 100,
            "med_fwd_30": s.fwd_30.median() * 100,
            "med_pop_day0": s.pop_day0.median() * 100,
            "share_trunc_7": s.trunc_7.mean(),
            "share_trunc_30": s.trunc_30.mean(),
        })
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False, float_format="%.2f"), flush=True)

    sd = g[g.lag_group == "same-day"]
    rest = g[g.lag_days >= 1]
    late = g[g.lag_group == ">7d"]
    print("\n=== Mann-Whitney (two-sided) ===", flush=True)
    for metric in ["fwd_7", "fwd_30", "pop_day0"]:
        u1, p1 = mw(sd[metric], rest[metric])
        u2, p2 = mw(sd[metric], late[metric])
        print(f"{metric}: same-day(n={sd[metric].notna().sum()}) vs >=1d(n={rest[metric].notna().sum()}): "
              f"U={u1:.0f}, p={p1:.4f} | same-day vs >7d(n={late[metric].notna().sum()}): "
              f"U={u2:.0f}, p={p2:.4f}", flush=True)

    # медианы плеч для интерпретации направления
    print("\nМедианы плеч MW:", flush=True)
    for metric in ["fwd_7", "fwd_30", "pop_day0"]:
        print(f"  {metric}: same-day={sd[metric].median()*100:.2f}%  >=1d={rest[metric].median()*100:.2f}%  "
              f">7d={late[metric].median()*100:.2f}%", flush=True)


if __name__ == "__main__":
    main()
