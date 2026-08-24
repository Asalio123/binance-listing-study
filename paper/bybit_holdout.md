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

### H2 robustness (declared exploratory, not part of frozen verdict)

The [−15, −5] band was imported from a Binance regression that *included* an annualized-volatility control absent from the frozen set — and on Binance that estimate is itself specification-fragile: without the ann_vol control the full-panel coefficient is only −3.19 pp (t = −1.65). Both venues, both specs:

| Sample | w/o ann_vol | w/ ann_vol |
|---|---|---|
| Binance full (n=472) | −3.19 (t=−1.65) | −8.21 (t=−5.01) |
| Binance survivors (n=371) | −4.52 (t=−2.02) | — |
| Bybit survivors (n=415) | +4.65 (t=+2.69) | +1.43 (t=+0.90) |

Reading: the range→fade gradient is specification-fragile on BOTH venues — on Binance it is significant only with the ann_vol control, on Bybit only without it. The preregistered claim 'day-0 volatility predicts the fade' does not survive as a stable cross-venue law.

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

N=472 events with archived day-0 USD turnover (death-inclusive source: data.binance.vision monthly klines, quoteAssetVolume field).

- Survivor-only median fwd_7 shift: **+0.35 pp**, bootstrap 95% CI [-1.32, +2.16] on 10000 draws (frozen prediction >= +1 pp)
- EW median fwd_7 = -11.45% vs USD-weighted median full = -28.72% (EW - VW = +17.27 pp)
- USD-weighted median survivors-only = **-27.77%** -> delisting-attributable VW component = **+0.96 pp**
- USD-weight concentration top-5: 20% (healthy; base-unit weights were degenerate — SHIB alone held 56% — hence the dedicated turnover refetch)

**H4 verdict:** the frozen median-shift prediction is NOT supported (+0.35 pp, CI includes 0). However, in USD space survivorship is first-order: dollar-weighted outcomes sit at -28.7% for the full panel versus -27.8% among survivors — a +1 pp delisting-attributable wedge, opposite in direction to the naive frozen guess and an order of magnitude larger. Death concentrates where money turned over; medians hide it, dollars expose it.