# Confirmatory holdout: Bybit surviving tokens (H1-H3) + Binance decomposition (H4)

Preregistered spec: HYPOTHESES.md, frozen 2026-08-23. Single-pass run, no peeking.

## Cohort

- Calendar USDT non-leveraged survivors (delisted=0): **419** of 1032 listings.
- REST-available with >=2 daily bars: **415** (empty/unavailable: 4; dropped n<2: 0).
- Day-0 later than calendar month+45d (suspicious, kept): 1.
- Truncated windows: fwd_7 truncated 0, fwd_30 truncated 2 (carried-last-close convention, mirroring the Binance panel).
- Note: `quote_vol_day0` is the kline **base-asset** volume on both venues (field 5 in both APIs — cross-venue consistent; label inherited from the Binance pipeline).

## H1 — Post-listing underperformance replicates cross-venue

N=415 | median fwd_7 = **-10.34%** | Wilcoxon two-sided p = 5.390e-14
(prediction: median < −5%; share positive: 27.5%)

## H2 — Day-0 intraday volatility predicts the fade

Controls: log_pop, log_range, log_vol (delisting flag dropped: identically 0 in survivor-only cohort — declared deviation from frozen control set).

| Term | Coef (pp) | t-stat | p |
|---|---|---|---|
| const | +5.44 | 0.54 | 0.591 |
| log_pop | -8.08 | -1.97 | 0.0496 |
| log_range | +4.65 | 2.69 | 0.00745 |
| log_vol | -0.06 | -0.10 | 0.918 |

N=415 | log_range coef = **+4.65 pp**, t = **2.69** (criterion t < −2; prediction band [−15, −5]; Binance was −8.21, t=−5.01)

## H3 — First-week extremes predict continuation

N=415 | Pearson r(max_daily_7d, fwd_30) = **+0.373** (one-sided p = 1.86e-15)
Terciles: top MAX median fwd_30 = **-6.74%** vs bottom = **-17.81%** (MW p = 0.00235; prediction r ≈ +0.2…+0.4; Binance was +0.32)

## Multiple testing (Benjamini-Hochberg q=0.05, family {H1,H2,H3})

- H1 (Wilcoxon): raw p listed above -> BH-adjusted **8.08e-14**
- H2 (OLS log_range): raw p listed above -> BH-adjusted **0.00745**
- H3 (Pearson, one-sided per spec): raw p listed above -> BH-adjusted **5.57e-15**

## Verdicts

- **H1: REPLICATES** (median -10.34%)
- **H2: does NOT replicate** (beta +4.65, t 2.69)
- **H3: REPLICATES** (r +0.373)

## H4 — Survivorship decomposition (Binance death-inclusive panel)

- Survivor-only median fwd_7 shift: **+0.35 pp**, bootstrap 95% CI [-1.32, +2.16] on 10000 draws (prediction >= +1 pp)
- EW median fwd_7 = -11.45% vs volume-weighted median full = -52.37% (EW-VW spread +40.91 pp)
- Weighted median survivors-only = -52.37% -> delisting-attributable VW component +0.00 pp

**VW sub-test caveat:** the archived weight column is *base-asset* day-0 volume (non-comparable across tokens): top-5 symbols hold **98%** of total weight, so the weighted median is pinned by a handful of mega-supply tokens and the preregistered "VW spread < EW spread" comparison is **NOT EVALUABLE** from archived features (USD turnover was never stored; refetching it via REST would survivorship-contaminate the weights).

**H4 verdict:** survivorship shift does NOT match prediction (+0.35 pp, CI includes 0 and < +1 pp); VW spread sub-prediction NOT EVALUABLE (degenerate weights, see caveat above).