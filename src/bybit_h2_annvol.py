"""Exploratory robustness (declared): H2 на Bybit с ann_vol контролом.

Прогнозная полоса [−15, −5] в спеке была взята из банальной регрессии,
включавшей ann_vol_7d, тогда как замороженный контроль-сет его не содержит.
Здесь добавляем ann_vol (пересчитан из кэша свечей) ОБА спека — прозрачно.
Вердикт замороженной спеки не меняется (см. paper/bybit_holdout.md).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "bybit_klines_cache"


def ols(Xv, yv):
    beta, _, _, _ = np.linalg.lstsq(Xv, yv, rcond=None)
    resid = yv - Xv @ beta
    s2 = resid @ resid / (len(yv) - Xv.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(Xv.T @ Xv)))
    t = beta / se
    p = 2 * (1 - stats_t_cdf(abs(t), len(yv) - Xv.shape[1]))
    return beta, t, p


def stats_t_cdf(x, dfree):
    from scipy import stats as st
    return st.t.cdf(x, df=dfree)


rows = []
for cf in sorted(CACHE.glob("*.json")):
    rows_raw = json.loads(cf.read_text())
    if len(rows_raw) < 9:
        continue
    c = pd.Series([r[4] for r in rows_raw], dtype=float)
    rr = c.pct_change().iloc[:8].dropna()
    if len(rr) < 3:
        continue
    o = float(rows_raw[0][1]); h0 = float(rows_raw[0][2]); l0 = float(rows_raw[0][3])
    c0 = float(rows_raw[0][4]); v0 = float(rows_raw[0][5])
    idx7 = min(7, len(c) - 1)
    rows.append({
        "symbol": cf.stem,
        "fwd_7": c.iloc[idx7] / c0 - 1,
        "pop_day0": c0 / o - 1,
        "range_day0": (h0 - l0) / o,
        "quote_vol_day0": v0,
        "ann_vol_7d": float(rr.std() * np.sqrt(365)),
    })

df = pd.DataFrame(rows).dropna()
ann_med = float(df["ann_vol_7d"].median())

specs = {
    "frozen controls (const, log_pop, log_range, log_vol)": ["log_pop", "log_range", "log_vol"],
    "+ ann_vol (benchmark spec of the -8.21 estimate)": ["log_pop", "log_range", "log_vol", "ann_vol"],
}

print(f"N={len(df)}\n")
for label, ctrl in specs.items():
    cols = {"const": np.ones(len(df)),
            "log_pop": np.log1p(df["pop_day0"].clip(lower=-0.99)),
            "log_range": np.log(df["range_day0"].clip(lower=1e-6)),
            "log_vol": np.log(df["quote_vol_day0"].clip(lower=1))}
    if "ann_vol" in ctrl:
        cols["ann_vol"] = df["ann_vol_7d"].fillna(ann_med)
    X = np.column_stack([cols[c] for c in ["const"] + ctrl])
    y = df["fwd_7"].values * 100
    beta, t, p = ols(X, y)
    names = ["const"] + ctrl
    ir = names.index("log_range")
    print(f"{label}")
    print(f"  N={len(y)} | log_range b={beta[ir]:+.2f} pp, t={t[ir]:+.2f}, p={p[ir]:.3g}")
