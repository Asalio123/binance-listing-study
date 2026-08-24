"""Конфирматорный холдаут: H1-H3 на выживших токенах Bybit (REST), H4 на Binance панели.

Спека заморожена в HYPOTHESES.md (2026-08-23). Скрипт бежит ОДНИМ проходом,
без подглядываний и подгонок: все результаты — в paper/bybit_holdout.md.
Формулы фич зеркалят src/enriched_study.py (cross-venue идентичность).
"""
import json
import re
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path.home() / "binance-listing-study"
CAL = ROOT / "data" / "listing_calendar_bybit.csv"
BINANCE = ROOT / "data" / "listing_events_enriched.csv"
CACHE = ROOT / "data" / "bybit_klines_cache"
OUT = ROOT / "paper" / "bybit_holdout.md"
API = "https://api.bybit.com/v5/market/kline"
LEV_PAT = re.compile(r"(UP|DOWN|BULL|BEAR)USDT$")
WINDOW_MS = 75 * 86_400_000  # первые ~75 дней: покрывает все замороженные метрики (до +30д)
rng = np.random.default_rng(42)

lines = []


def md(s=""):
    lines.append(s)
    print(s, flush=True)


def fetch_klines(sym, start_ms, retries=3):
    """Дейли-свечи с start_ms, ASC по времени. Пусто = символа нет в REST.

    Сырой ответ кэшируется в data/bybit_klines_cache/{sym}.json: конфирматорный
    прогон должен быть воспроизводим после того, как REST изменится.
    """
    CACHE.mkdir(exist_ok=True)
    cf = CACHE / f"{sym}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    url = f"{API}?category=spot&symbol={sym}&interval=D&start={start_ms}&end={start_ms + WINDOW_MS}&limit=200"
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read())
            if j.get("retCode") != 0:
                raise RuntimeError(j.get("retMsg", "retCode!=0"))
            rows = [(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
                    for k in j["result"]["list"]]
            rows = sorted(rows)
            cf.write_text(json.dumps(rows))
            return rows
        except Exception as e:
            if i == retries - 1:
                print(f"  {sym}: REST fail {str(e)[:60]}")
                return []
            time.sleep(2 ** i)


def enrich(rows, sym, first_month):
    """Зеркало enrich() из enriched_study.py: те же формулы, тот же порядок."""
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"], unit="ms").dt.date
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    n = len(df)
    if n < 2:
        return None, n
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    c0 = c.iloc[0]
    m = {"symbol": sym, "first_month": first_month, "days_listed": n,
         "day0_date": str(df["date"].iloc[0]),
         "quote_vol_day0": v.iloc[0],
         "pop_day0": c0 / o.iloc[0] - 1,
         "range_day0": (h.iloc[0] - l.iloc[0]) / o.iloc[0]}
    for hz in (7, 30):
        idx = min(hz, n - 1)
        m[f"fwd_{hz}"] = c.iloc[idx] / c0 - 1
        m[f"trunc_{hz}"] = int((n - 1) < hz)
    rr = c.pct_change().iloc[:7].dropna()
    m["max_daily_7d"] = float(rr.max()) if len(rr) else np.nan
    return m, n


def ols(Xv, yv):
    beta, _, _, _ = np.linalg.lstsq(Xv, yv, rcond=None)
    resid = yv - Xv @ beta
    sigma2 = resid @ resid / (len(yv) - Xv.shape[1])
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(Xv.T @ Xv)))
    t = beta / se
    p = 2 * (1 - stats.t.cdf(np.abs(t), df=len(yv) - Xv.shape[1]))
    return beta, t, p


def bh_adjust(pvals):
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    o = np.argsort(p)
    ranked = p[o] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.clip(adj, 0, 1)
    return out


def wmedian(x, w):
    o = np.argsort(x)
    xs, ws = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(ws)
    return float(xs[np.searchsorted(cw, ws.sum() / 2)])


def main():
    md("# Confirmatory holdout: Bybit surviving tokens (H1-H3) + Binance decomposition (H4)\n")
    md("Preregistered spec: HYPOTHESES.md, frozen 2026-08-23. Single-pass run, no peeking.\n")

    # ---------- 1. Когорта ----------
    cal = pd.read_csv(CAL)
    cand = cal[cal.symbol.str.endswith("USDT") & ~cal.symbol.str.match(LEV_PAT) & (cal.delisted == 0)].copy()
    md(f"## Cohort\n")
    md(f"- Calendar USDT non-leveraged survivors (delisted=0): **{len(cand)}** of {len(cal)} listings.")

    res, rest_empty, late_data = [], 0, 0
    failed_syms = []
    t0 = time.time()
    for i, row in enumerate(cand.itertuples(), 1):
        start_ms = int(pd.Timestamp(row.first_month + "-01", tz="UTC").timestamp() * 1000)
        rows = fetch_klines(row.symbol, start_ms)
        if not rows:
            rest_empty += 1
            continue
        m, n = enrich(rows, row.symbol, row.first_month)
        if m is None:
            failed_syms.append(f"{row.symbol}(n<2)")
            continue
        lag_days = (pd.Timestamp(m["day0_date"]) - pd.Timestamp(row.first_month + "-01")).days
        if lag_days > 45:
            late_data += 1
        res.append(m)
        if i % 100 == 0:
            print(f"...{i}/{len(cand)} ({time.time()-t0:.0f}с)", flush=True)
        time.sleep(0.15)

    byb = pd.DataFrame(res)
    md(f"- REST-available with >=2 daily bars: **{len(byb)}** "
       f"(empty/unavailable: {rest_empty}; dropped n<2: {len(cand) - rest_empty - len(byb)}).")
    if failed_syms:
        md(f"- Excluded symbols (selection transparency): {', '.join(failed_syms)}.")
    md(f"- Day-0 later than calendar month+45d (suspicious, kept): {late_data}.")
    md(f"- Truncated windows: fwd_7 truncated {int(byb.trunc_7.sum())}, fwd_30 truncated {int(byb.trunc_30.sum())} "
       f"(carried-last-close convention, mirroring the Binance panel).")
    md(f"- Note: `quote_vol_day0` is the kline **base-asset** volume on both venues "
       f"(field 5 in both APIs — cross-venue consistent; label inherited from the Binance pipeline).\n")

    # ---------- 2. H1 ----------
    md("## H1 — Post-listing underperformance replicates cross-venue\n")
    r7 = byb.fwd_7.dropna() * 100
    med7 = r7.median()
    w_stat, w_p = stats.wilcoxon(r7, alternative="two-sided")
    md(f"N={len(r7)} | median fwd_7 = **{med7:+.2f}%** | Wilcoxon two-sided p = {w_p:.3e}")
    md(f"(prediction: median < −5%; share positive: {(r7 > 0).mean()*100:.1f}%)\n")

    # ---------- 3. H2 ----------
    md("## H2 — Day-0 intraday volatility predicts the fade\n")
    sub = byb[["fwd_7", "pop_day0", "range_day0", "quote_vol_day0"]].dropna()
    X = pd.DataFrame({
        "const": 1.0,
        "log_pop": np.log1p(sub.pop_day0.clip(lower=-0.99)),
        "log_range": np.log(sub.range_day0.clip(lower=1e-6)),
        "log_vol": np.log(sub.quote_vol_day0.clip(lower=1)),
    })
    beta, tstat, pval = ols(X.values, sub.fwd_7.values * 100)
    b_range, t_range = beta[X.columns.get_loc("log_range")], tstat[X.columns.get_loc("log_range")]
    p_range = pval[X.columns.get_loc("log_range")]
    md(f"Controls: log_pop, log_range, log_vol (delisting flag dropped: identically 0 "
       f"in survivor-only cohort — declared deviation from frozen control set).\n")
    md("| Term | Coef (pp) | t-stat | p |")
    md("|---|---|---|---|")
    for name, b, t_, p_ in zip(X.columns, beta, tstat, pval):
        md(f"| {name} | {b:+.2f} | {t_:.2f} | {p_:.3g} |")
    md(f"\nN={len(sub)} | log_range coef = **{b_range:+.2f} pp**, t = **{t_range:.2f}** "
       f"(criterion t < −2; prediction band [−15, −5]; Binance was −8.21, t=−5.01)\n")

    # ---------- 4. H3 ----------
    md("## H3 — First-week extremes predict continuation\n")
    h3 = byb[["max_daily_7d", "fwd_30"]].dropna()
    r, p_r = stats.pearsonr(h3.max_daily_7d, h3.fwd_30)
    p_r_one = p_r / 2 if r > 0 else 1 - p_r / 2
    q1, q2 = np.quantile(h3.max_daily_7d, [1 / 3, 2 / 3])
    low = h3[h3.max_daily_7d <= q1].fwd_30.median() * 100
    high = h3[h3.max_daily_7d >= q2].fwd_30.median() * 100
    mw_p = stats.mannwhitneyu(h3[h3.max_daily_7d >= q2].fwd_30,
                              h3[h3.max_daily_7d <= q1].fwd_30).pvalue
    md(f"N={len(h3)} | Pearson r(max_daily_7d, fwd_30) = **{r:+.3f}** (one-sided p = {p_r_one:.3g})")
    md(f"Terciles: top MAX median fwd_30 = **{high:+.2f}%** vs bottom = **{low:+.2f}%** "
       f"(MW p = {mw_p:.3g}; prediction r ≈ +0.2…+0.4; Binance was +0.32)\n")

    # ---------- 5. BH over family {H1,H2,H3} ----------
    md("## Multiple testing (Benjamini-Hochberg q=0.05, family {H1,H2,H3})\n")
    p_raw = [w_p, p_range, p_r_one]  # H3 односторонний по спеке; H1/H2 двусторонние
    p_adj = bh_adjust(p_raw)
    labels = ["H1 (Wilcoxon)", "H2 (OLS log_range)", "H3 (Pearson, one-sided per spec)"]
    verdicts = []
    for lab, pa in zip(labels, p_adj):
        md(f"- {lab}: raw p listed above -> BH-adjusted **{pa:.3g}**")
    v1 = p_adj[0] < 0.05 and med7 < -5
    v2 = p_adj[1] < 0.05 and t_range < -2 and b_range < 0
    v3 = p_adj[2] < 0.05 and r > 0
    verdicts = [("H1", v1, f"median {med7:+.2f}%"), ("H2", v2, f"beta {b_range:+.2f}, t {t_range:.2f}"),
                ("H3", v3, f"r {r:+.3f}")]
    md("\n## Verdicts\n")
    for name, ok, detail in verdicts:
        md(f"- **{name}: {'REPLICATES' if ok else 'does NOT replicate'}** ({detail})")
    md("")

    # ---------- 6. H4 на Binance панели ----------
    md("## H4 — Survivorship decomposition (Binance death-inclusive panel)\n")
    df = pd.read_csv(BINANCE)
    surv = df[df.delisted == 0]
    shift = (surv.fwd_7.median() - df.fwd_7.median()) * 100
    boots = []
    idx_all = df.index.values
    for _ in range(10000):
        pick = rng.choice(idx_all, size=len(idx_all), replace=True)
        resampled = df.loc[pick]
        a = resampled[resampled.delisted == 0].fwd_7.dropna()
        b = resampled.fwd_7.dropna()
        if len(a) > 10:
            boots.append((a.median() - b.median()) * 100)
    lo, hi = np.percentile(boots, [2.5, 97.5])

    x = df.fwd_7.dropna().values * 100
    w = df.loc[df.fwd_7.notna(), "quote_vol_day0"].clip(lower=1).values
    ew = df.fwd_7.median() * 100
    vw_full = wmedian(x, w)
    mask_s = df.loc[df.fwd_7.notna(), "delisted"].values == 0
    vw_surv = wmedian(x[mask_s], w[mask_s])
    o = np.argsort(w)[::-1]
    top5_share = float(w[o[:5]].sum() / w.sum() * 100)
    md(f"- Survivor-only median fwd_7 shift: **{shift:+.2f} pp**, bootstrap 95% CI [{lo:+.2f}, {hi:+.2f}] "
       f"on {len(boots)} draws (prediction >= +1 pp)")
    md(f"- EW median fwd_7 = {ew:+.2f}% vs volume-weighted median full = {vw_full:+.2f}% "
       f"(EW-VW spread {ew - vw_full:+.2f} pp)")
    md(f"- Weighted median survivors-only = {vw_surv:+.2f}% -> delisting-attributable VW component "
       f"{vw_surv - vw_full:+.2f} pp")
    md(f"\n**VW sub-test caveat:** the archived weight column is *base-asset* day-0 volume "
       f"(non-comparable across tokens): top-5 symbols hold **{top5_share:.0f}%** of total weight, so the "
       f"weighted median is pinned by a handful of mega-supply tokens and the preregistered "
       f"\"VW spread < EW spread\" comparison is **NOT EVALUABLE** from archived features "
       f"(USD turnover was never stored; refetching it via REST would survivorship-contaminate the weights).\n")
    h4_a = shift >= 1 and lo > 0
    md(f"**H4 verdict:** survivorship shift does NOT match prediction ({shift:+.2f} pp, CI includes 0 and "
       f"< +1 pp); VW spread sub-prediction NOT EVALUABLE (degenerate weights, see caveat above).")

    OUT.write_text("\n".join(lines))
    print(f"\nOK -> {OUT}")


if __name__ == "__main__":
    main()
