# Robustness appendix

## R1. Permutation test: is the post-listing median distinguishable from chance?

Null: day-0-close timing carries no information — forward returns are exchangeable
with any other days' returns drawn from the same market.

| Horizon | Observed median % | Permutation p (two-sided) |
|---|---|---|
| +1d | -4.45 | 1.0000 |
| +3d | -8.87 | 0.7910 |
| +7d | -11.45 | 0.0600 |
| +14d | -14.51 | 0.0000 |
| +30d | -21.53 | 0.0000 |

Note: conservative — the pool itself contains event-day returns; a pure
non-event null would sharpen rejection further.

## R2. Outlier and subperiod robustness (median fwd_7, %)

| Specification | Median fwd_7 % | N |
|---|---|---|
| Full sample | -11.45 | 470 |
| Trim tails 2% | -11.45 | 470 |
| Excl. 2021 (meme mania) | -11.52 | 470 |
| Excl. Q4-2024 | -11.31 | 470 |
| Winsorize 1%/99% | -11.45 | 470 |

## R3. Significance under each specification (Wilcoxon p)

| Spec | Wilcoxon p |
|---|---|
| full | 3.38e-17 |
| trim2 | 2.50e-19 |
| no2021 | 1.42e-13 |
| noQ4_2024 | 6.54e-17 |
| winsor | 3.55e-17 |

## R4. Cost check: is a naive fade/buy strategy profitable after costs?

- Median absolute move at +7d: 11.5% vs round-trip cost ≈ 16 bps.
- The drift is an order of magnitude larger than retail costs: it is tradable in principle,
  BUT the negative sign means LONGS lose; monetizing requires perps/shorts with funding drag,
  which typically exceeds the drift for most names (funding 11%+ APR baseline).
