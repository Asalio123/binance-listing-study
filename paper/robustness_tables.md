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
  BUT the negative sign means LONGS lose; monetizing requires shorting perps. Full-panel
  funding sweep (`data/funding_sweep.csv`, all 470 names; script `src/funding_sweep.py`):
  - A perp exists for 327/470 names (69.6%), but it is shortable from day 0
    (perp inception ≤ spot day 0) for only **80/470 = 17.0%** of the panel, and within
    week 1 for 210/470 = 44.7%. Availability, not funding, is the binding constraint.
  - Across the 209 names with week-1 funding history, the median week-1 funding sum for
    a short is **−0.36%** vs the −11.45% median drift — about 3% of the drift. A sustained
    break-even rate (< −0.5%/8h for the whole week) occurs in 1 of 209 names.
  - The tail is real: 17.7% of day-0 shorts (14/79 with week-1 history) lose more than
    half the drift to funding; the worst week-1 sum is −28.97% (NEWTUSDT).
  - Regime break: in 2021–2024 week-1 funding was roughly zero-to-positive for shorts
    (cohort medians +0.21/+0.22/+0.16%, except 2022 at −0.67%); since 2025 shorts pay
    (median −1.13% in 2025, −1.89% in 2026) — still ~10–17% of the drift, but no
    longer ~zero.
