"""Микроструктура дня 0 из кэша минутных klines (data/intraday_day0_cache/).

Ничего не скачивает: только локальные zip (470 daily-файлов, имена
{SYM}_{YYYY-MM-DD}_daily.zip). ГРАБЛЯ open_time (13 цифр = мс, 16 = мкс с 2025)
решается копией parse_zip из fetch_intraday_day0.py.

Метрики на символ:
- opening print premium: ret_min1 / ret_open_h1 / ret_open_day
  (open первого бара -> close 1-й минуты / 1-го часа / дня);
- агрессия покупателей: tb_share_{5,15,60}m =
  sum(taker_buy_quote_volume) / sum(quote_volume) по окну;
- френтези: count_h1, cpm_h1, cpm_5, cpm_rest (бары с 6-й минуты до конца),
  frenzy_ratio = cpm_5 / cpm_rest;
- связь с фейдом: spearman с fwd_7 (полная выборка и без trunc_7==1),
  медианный fwd_7 по квартилям tb_share_60m (печать в stdout);
- кросс-чек ret_open_h1 / ret_open_day против data/intraday_day0.csv.

Выход: data/day0_microstructure.csv (symbol + метрики).
"""
import io
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path.home() / "binance-listing-study"
CACHE = ROOT / "data" / "intraday_day0_cache"
OUT = ROOT / "data" / "day0_microstructure.csv"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def parse_zip(path):
    """Локальный zip -> DataFrame баров дня 0, ts_ms нормализован по длине числа."""
    zf = zipfile.ZipFile(path)
    with zf.open(zf.namelist()[0]) as f:
        df = pd.read_csv(f, header=None, names=COLS,
                         dtype={c: "float64" for c in COLS[1:6]} | {"quote_volume": "float64"})
    df = df[pd.to_numeric(df["open_time"], errors="coerce").notna()]  # скип header-строк
    ts = df["open_time"].astype("int64")
    scale = {13: 1, 16: 10 ** 3, 19: 10 ** 6}[len(str(ts.iloc[0]))]
    df["ts_ms"] = ts // scale
    return df.sort_values("ts_ms").reset_index(drop=True)


def metrics(sym, df):
    """Метрики микроструктуры дня 0 по барам одного символа."""
    open0, n = df["open"].iloc[0], len(df)
    h1, w5, w15 = df.iloc[:60], df.iloc[:5], df.iloc[:15]

    def tb_share(w):
        q = w["quote_volume"].sum()
        return w["taker_buy_quote_volume"].sum() / q if q else np.nan

    count_h1 = h1["count"].sum()
    cpm_5 = w5["count"].sum() / 5
    cpm_rest = df["count"].iloc[5:].sum() / (n - 5)
    return {"symbol": sym,
            "ret_min1": df["close"].iloc[0] / open0 - 1,
            "ret_open_h1": h1["close"].iloc[-1] / open0 - 1,
            "ret_open_day": df["close"].iloc[-1] / open0 - 1,
            "tb_share_5m": tb_share(w5),
            "tb_share_15m": tb_share(w15),
            "tb_share_60m": tb_share(h1),
            "count_h1": count_h1,
            "cpm_h1": count_h1 / 60,
            "cpm_5": cpm_5,
            "cpm_rest": cpm_rest,
            "frenzy_ratio": cpm_5 / cpm_rest if cpm_rest else np.nan,
            "n_bars": n}


def main():
    t = pd.read_csv(ROOT / "data" / "day0_turnover.csv")
    e = pd.read_csv(ROOT / "data" / "listing_events_enriched.csv",
                    usecols=["symbol", "fwd_7", "trunc_7"])
    jobs = list(t.merge(e[["symbol"]], on="symbol")[["symbol", "day0_date"]].itertuples(index=False))
    print(f"Событий: {len(jobs)}", flush=True)
    out, fail = [], []
    t0 = time.time()
    for i, job in enumerate(jobs, 1):
        p = CACHE / f"{job.symbol}_{job.day0_date}_daily.zip"
        if not p.exists():
            fail.append(job.symbol)
            continue
        out.append(metrics(job.symbol, parse_zip(p)))
        if i % 50 == 0:
            print(f"...{i}/{len(jobs)} ({time.time() - t0:.0f}с)", flush=True)
    df = pd.DataFrame(out)
    df.to_csv(OUT, index=False)
    print(f"\nOK: {len(df)}/{len(jobs)} | нет кэша: {len(fail)}", flush=True)
    if fail:
        print("дыры:", fail, flush=True)
    print(f"-> {OUT}", flush=True)

    # --- сводка для отчёта ---
    def med(s):
        return f"{s.median():+.4f}"

    print("\n== Opening print premium (медианы) ==", flush=True)
    for c in ["ret_min1", "ret_open_h1", "ret_open_day"]:
        print(f"{c}: {med(df[c])}  (p25={df[c].quantile(.25):+.4f}, p75={df[c].quantile(.75):+.4f})", flush=True)

    print("\n== Агрессия покупателей (taker buy share) ==", flush=True)
    for c in ["tb_share_5m", "tb_share_15m", "tb_share_60m"]:
        s = df[c]
        print(f"{c}: медиана={s.median():.4f}, p25={s.quantile(.25):.4f}, p75={s.quantile(.75):.4f}, "
              f"min={s.min():.4f}, max={s.max():.4f}, доля>0.5={100 * (s > .5).mean():.1f}%", flush=True)

    print("\n== Френтези в сделках ==", flush=True)
    for c in ["count_h1", "cpm_h1", "cpm_5", "cpm_rest", "frenzy_ratio"]:
        s = df[c]
        print(f"{c}: медиана={s.median():.2f}, p25={s.quantile(.25):.2f}, p75={s.quantile(.75):.2f}", flush=True)

    print("\n== Связь с фейдом (fwd_7) ==", flush=True)
    m = df.merge(e, on="symbol")
    for c in ["tb_share_5m", "tb_share_15m", "tb_share_60m", "cpm_h1"]:
        sp = stats.spearmanr(m[c], m.fwd_7)
        print(f"spearman({c}, fwd_7): rho={sp.statistic:+.4f}, p={sp.pvalue:.4g}, n={len(m)}", flush=True)
    m0 = m[m.trunc_7 == 0]
    for c in ["tb_share_60m", "cpm_h1"]:
        sp = stats.spearmanr(m0[c], m0.fwd_7)
        print(f"  [без trunc_7] spearman({c}, fwd_7): rho={sp.statistic:+.4f}, p={sp.pvalue:.4g}, n={len(m0)}", flush=True)

    m["q"] = pd.qcut(m.tb_share_60m, 4, labels=["Q1", "Q2", "Q3", "Q4"])
    g = m.groupby("q", observed=True).agg(n=("symbol", "count"),
                                          x_med=("tb_share_60m", "median"),
                                          fwd7_med=("fwd_7", "median"))
    print("\nКвартили tb_share_60m -> медианный fwd_7:", flush=True)
    print(g.to_string(float_format=lambda x: f"{x:.4f}"), flush=True)
    m["qc"] = pd.qcut(m.cpm_h1, 4, labels=["Q1", "Q2", "Q3", "Q4"])
    gc = m.groupby("qc", observed=True).agg(n=("symbol", "count"),
                                            x_med=("cpm_h1", "median"),
                                            fwd7_med=("fwd_7", "median"))
    print("\nКвартили cpm_h1 -> медианный fwd_7:", flush=True)
    print(gc.to_string(float_format=lambda x: f"{x:.4f}"), flush=True)

    # --- кросс-чек против intraday_day0.csv ---
    ref = pd.read_csv(ROOT / "data" / "intraday_day0.csv")
    chk = df.merge(ref, on="symbol")
    d1 = (chk.ret_open_h1 - chk.ret_first_hour).abs().max()
    d2 = (chk.ret_open_day - chk.ret_day0_full).abs().max()
    print(f"\n== Кросс-чек (n={len(chk)}): max|d ret_open_h1 vs ret_first_hour|={d1:.3e}, "
          f"max|d ret_open_day vs ret_day0_full|={d2:.3e}", flush=True)
    smp = chk.sample(10, random_state=42)[["symbol", "ret_open_h1", "ret_first_hour",
                                           "ret_open_day", "ret_day0_full"]]
    print(smp.to_string(index=False, float_format=lambda x: f"{x:.6f}"), flush=True)


if __name__ == "__main__":
    main()
