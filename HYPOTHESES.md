# Preregistered hypotheses — frozen 2026-08-23

## Design

- **Discovery sample**: Binance USDT listings (n=472). Already explored during
  August 2026 sessions — all results here are EXPLORATORY.
- **Confirmatory holdout**: **Bybit USDT listings** (calendar frozen separately:
  n=829, incl. 410 delisted markers). Price-path OUTCOMES have NOT been computed
  as of freeze date. Tests below run on the Bybit cohort first, before any peeking.
- Known limitation declared upfront: Bybit public archive stores raw trades, so
  price paths for the holdout come from REST klines → **surviving tokens only**.
  Hypothesis H4 (survivorship decomposition) therefore runs on the Binance
  archive-based panel instead, where death-inclusive measurement is possible.

## Hypotheses (directional, pre-specified)

### H1 — Post-listing underperformance replicates cross-venue
Median forward return from day-0 close at +7 trading days is negative in the
Bybit surviving-token cohort.
Test: Wilcoxon signed-rank, two-sided, α=0.05. Prediction: median < −5%.

### H2 — Day-0 intraday volatility predicts the fade
In OLS of fwd_7 (%) on controls {log day-0 pop, log day-0 range, log day-0
volume, delisting flag}, the coefficient on log(range) is negative.
Test: t-stat < −2. Prediction: β ∈ [−15, −5] pp per log-unit (Binance estimate:
−8.21, t=−5.01).

### H3 — First-week extremes predict continuation, not reversal
Correlation between max single-day return of week 1 and fwd_30 is positive.
Test: Pearson r > 0 with p < 0.05; plus top-vs-bottom tercile median comparison.
Prediction: r ≈ +0.2…+0.4 (Binance: +0.32).

### H4 — Survivorship shifts medians upward (decomposition)
On the Binance death-inclusive panel: excluding delisted tokens raises the median
fwd_7 relative to the full sample. Additionally, equal-weight minus value-weight
(volume-weighted) spread is decomposed into a delisting-attributable component.
Test: sign check + bootstrap CI of shift; prediction: shift ≥ +1 pp, VW spread
smaller than EW spread.

## Multiple testing

Within each venue, family = {H1, H2, H3}: Benjamini-Hochberg at q=0.05.
Decision rule: a hypothesis "replicates" if BH-adjusted p < 0.05 AND direction
matches prediction.

## Exploratory additions (declared, not preregistered)

- Announcement-window analysis (requires announcement-date reconstruction;
  Common Crawl / Telegram routes).
- Intraday first-hour dynamics on Binance subsample (taker-buy pressure).
- Cross-sectional extension: MAX features (computed post-hoc on Binance,
  reported transparently as exploratory).
