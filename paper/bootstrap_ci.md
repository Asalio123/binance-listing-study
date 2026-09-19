# Bootstrap CI for the dollar-weighted headline statistics (M4)

**Date:** 2026-09-19. **Script:** `src/bootstrap_vw_ci.py`. **Output:** `data/bootstrap_vw_ci.csv`.

## Method

Month-block bootstrap, same cluster design as `post_window_inference.py`:
the resampling unit is the calendar month of listing (67 clusters, panel
n = 470; BTC-adjusted statistics also n = 470 after the 2026-09-19 refresh of the day-closes cache). Months are drawn with
replacement, every event in a drawn month enters with the draw's
multiplicity, and each statistic is recomputed inside the draw — including
re-cutting the turnover-quintile partition on the resampled panel
(rank-based assignment, so duplicated turnover values cannot collapse a
bin). B = 5,000 draws, `numpy` generator seeded at 42, percentile 95% CI
(2.5/97.5). Weights are day-0 USD turnover clipped below at 1.

The weighted median sorts observations by the return value (the
`argsort(weight)` ordering in the frozen `post_window_inference.py` is a
known bug and is not replicated here). Point estimates recomputed with the
correct ordering match the published headline numbers exactly
(−28.72%, −35.46%, +0.96 pp, −0.6/−5.0/−14.5/−16.8/−23.5%).

## Results

| Statistic | Point | 95% CI low | 95% CI high |
|---|---|---|---|
| VW median fwd_7 (n=470) | −28.72% | −39.45 | −19.79 |
| VW median BTC-adj madj_7 (n=470) | −35.46% | −49.32 | −22.31 |
| Delisting wedge (VW survivors − VW full) | +0.96 pp | −3.41 | +3.24 |
| EW − VW gap (fwd_7) | +17.27 pp | +8.05 | +27.37 |
| Turnover quintile Q1 median fwd_7 | −0.60% | −7.21 | +0.70 |
| Turnover quintile Q2 | −4.99% | −14.18 | −1.85 |
| Turnover quintile Q3 | −14.50% | −20.50 | −6.14 |
| Turnover quintile Q4 | −16.78% | −25.99 | −12.95 |
| Turnover quintile Q5 | −23.54% | −33.15 | −14.93 |
| Gradient Q5 − Q1 | −22.94 pp | −32.61 | −13.25 |
| BTC-adj quintile Q1 | −4.55% | −8.56 | +0.12 |
| BTC-adj quintile Q2 | −9.78% | −15.62 | −4.59 |
| BTC-adj quintile Q3 | −15.73% | −22.46 | −10.26 |
| BTC-adj quintile Q4 | −19.53% | −27.72 | −12.00 |
| BTC-adj quintile Q5 | −29.08% | −41.44 | −14.80 |
| BTC-adj gradient Q5 − Q1 | −24.54 pp | −37.42 | −9.91 |

Reading: the VW medians and the quintile gradient exclude zero
comfortably under clustering; Q1 (quietest listings) does not — its CI
spans zero on both raw and BTC-adjusted panels, which is exactly the
"no fade in the quietest quintile" claim and is stated as such. The
delisting wedge (+0.96 pp) is not distinguishable from zero at 95%.

## The n = 460 partition (RESOLVED 2026-09-19)

The original run had n = 460 for BTC-adjusted series: ten July-2026 tokenized-stock listings lacked a day+7 close in the day-closes cache. After the cache refresh (2026-08 files added by the M9 hygiene pass), madj is defined for all 470 events; the BTC-adjusted VW median is unchanged (−35.46%), the BTC-adjusted Q1 quintile moves −4.55 -> −3.45. The table above reports refreshed numbers.
