# Statistical appendix (auto-generated)

## Table S1. Forward returns from day-0 close

| Horizon | N | Median % | Mean % | t-stat | p(mean≠0) | Wilcoxon p | %>0 |
|---|---|---|---|---|---|---|---|
| +1d | 472 | -4.45 | -1.34 | -1.22 | 2.22e-01 | 9.64e-13 | 32.6% |
| +3d | 472 | -8.87 | -3.50 | -2.26 | 2.41e-02 | 5.77e-16 | 27.3% |
| +7d | 472 | -11.45 | -6.73 | -3.78 | 1.77e-04 | 2.50e-17 | 29.0% |
| +14d | 472 | -14.63 | -9.84 | -4.86 | 1.57e-06 | 4.10e-19 | 28.8% |
| +30d | 472 | -21.62 | -7.53 | -1.77 | 7.70e-02 | 4.78e-19 | 29.0% |

## Table S2. Bootstrap 95% CI of median forward returns (10k resamples)

| Horizon | Median % | 2.5% | 97.5% | CI excludes 0 |
|---|---|---|---|---|
| +1d | -4.45 | -5.75 | -3.71 | yes |
| +3d | -8.87 | -10.22 | -6.90 | yes |
| +7d | -11.45 | -13.73 | -8.84 | yes |
| +14d | -14.63 | -17.89 | -10.67 | yes |
| +30d | -21.62 | -26.65 | -16.59 | yes |

## Table S3. Cross-sectional regression: fwd_7 ~ pop_day0 controls

| Term | Coef (pp) | t-stat | p-value |
|---|---|---|---|
| const | -33.91 | -4.54 | 7.01e-06 |
| log_pop | +9.19 | 3.35 | 0.000883 |
| log_range | -8.21 | -5.01 | 7.77e-07 |
| log_vol | -0.24 | -0.64 | 0.526 |
| ann_vol | +12.57 | 15.36 | 0 |
| delisted | +2.44 | 0.67 | 0.503 |

N=472, R²=0.3410

## Table S4. Split-half stability of median fwd returns (%)

| Horizon | 1st half median | 2nd half median |
|---|---|---|
| +7d | -11.39 | -11.67 | (Mann-Whitney p=0.646) |
| +30d | -23.92 | -19.30 | (Mann-Whitney p=0.895) |

## Table S5. Delisted vs surviving listings (median %)

| Horizon | Surviving | Delisted | Diff |
|---|---|---|---|
| +7d | -11.11 | -13.15 | +2.05 |
| +30d | -20.72 | -22.81 | +2.09 |

A survivor-only sample (excluding delisted) shifts the median fwd_7 by +0.35 pp (472 -> 371 events).
