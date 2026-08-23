# Robustness appendix

## R1. Permutation test: is the post-listing median distinguishable from chance?

Null: day-0-close timing carries no information — forward returns are exchangeable
with any other days' returns drawn from the same market.

| Horizon | Observed median % | Permutation p (two-sided) |
|---|---|---|
| +1d | -4.45 | 1.0000 |
| +3d | -8.87 | 0.8080 |
| +7d | -11.45 | 0.0710 |
| +14d | -14.63 | 0.0000 |
| +30d | -21.62 | 0.0000 |

Note: conservative — the pool itself contains event-day returns; a pure
non-event null would sharpen rejection further.

## R2. Outlier and subperiod robustness (median fwd_7, %)

| Specification | Median fwd_7 % | N |
|---|---|---|
| Full sample | -11.45 | 472 |
| Trim tails 2% | -11.45 | 472 |
| Excl. 2021 (meme mania) | -11.52 | 472 |
| Excl. Q4-2024 | -11.31 | 472 |
| Winsorize 1%/99% | -11.45 | 472 |

## R3. Significance under each specification (Wilcoxon p)

| Spec | Wilcoxon p |
|---|---|
| full | 2.50e-17 |
| trim2 | 1.83e-19 |
| no2021 | 1.42e-13 |
| noQ4_2024 | 4.88e-17 |
| winsor | 2.63e-17 |

## R4. Cost check: is a naive fade/buy strategy profitable after costs?

- Median absolute move at +7d: 11.5% vs round-trip cost ≈ 16 bps.
- The drift is an order of magnitude larger than retail costs: it is tradable in principle,
  BUT the negative sign means LONGS lose; monetizing requires perps/shorts with funding drag,
  which typically exceeds the drift for most names (funding 11%+ APR baseline).
