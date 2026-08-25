# Statistical appendix (auto-generated)

## Table S1. Forward returns from day-0 close

| Horizon | N | Median % | Mean % | t-stat | p(mean≠0) | Wilcoxon p | %>0 |
|---|---|---|---|---|---|---|---|
| +1d | 470 | -4.45 | -1.35 | -1.22 | 2.22e-01 | 7.86e-13 | 32.6% |
| +3d | 470 | -8.87 | -3.44 | -2.21 | 2.74e-02 | 9.98e-16 | 27.4% |
| +7d | 470 | -11.45 | -6.65 | -3.72 | 2.20e-04 | 3.38e-17 | 28.9% |
| +14d | 470 | -14.51 | -9.68 | -4.77 | 2.41e-06 | 8.59e-19 | 28.9% |
| +30d | 470 | -21.53 | -7.29 | -1.71 | 8.82e-02 | 1.03e-18 | 29.1% |

## Table S2. Bootstrap 95% CI of median forward returns (10k resamples)

| Horizon | Median % | 2.5% | 97.5% | CI excludes 0 |
|---|---|---|---|---|
| +1d | -4.45 | -5.75 | -3.71 | yes |
| +3d | -8.87 | -10.22 | -6.79 | yes |
| +7d | -11.45 | -13.75 | -8.84 | yes |
| +14d | -14.51 | -17.67 | -10.59 | yes |
| +30d | -21.53 | -26.07 | -15.98 | yes |

## Table S3. Cross-sectional regression: fwd_7 ~ pop_day0 controls

| Term | Coef (pp) | t-stat | p-value |
|---|---|---|---|
| const | -33.94 | -4.57 | 6.22e-06 |
| log_pop | +9.40 | 3.44 | 0.000634 |
| log_range | -8.40 | -5.14 | 3.96e-07 |
| log_vol | -0.26 | -0.70 | 0.486 |
| ann_vol | +12.70 | 15.57 | 0 |
| delisted | +3.45 | 0.94 | 0.346 |

N=470, R²=0.3483

## Table S4. Split-half stability of median fwd returns (%)

| Horizon | 1st half median | 2nd half median |
|---|---|---|
| +7d | -10.80 | -12.47 | (Mann-Whitney p=0.330) |
| +30d | -22.10 | -20.51 | (Mann-Whitney p=0.405) |

## Table S5. Delisted vs surviving listings (median %)

| Horizon | Surviving | Delisted | Diff |
|---|---|---|---|
| +7d | -11.11 | -13.15 | +2.05 |
| +30d | -20.72 | -22.10 | +1.38 |

A survivor-only sample (excluding delisted) shifts the median fwd_7 by +0.35 pp (470 -> 371 events).
