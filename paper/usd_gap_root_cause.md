# Root causes of the USD-weighted vs equal-weighted gap (exploratory)

Question: why does the dollar-typical listing lose −28.7% in week 1 while the
token-typical loses only −11.45%? All numbers from data/day0_turnover.csv +
listing_events_enriched.csv (n=472, death-inclusive). Declared exploratory —
NOT part of the frozen H1-H4 verdicts.

## Finding 1 — the fade is monotone in day-0 turnover [DATA]

Turnover quintiles, median fwd_7 / fwd_30 (%), share of positive weeks:

| Quintile | n | fwd_7 | fwd_30 | %>0 | median day-0 range |
|---|---|---|---|---|---|
| Q1 lowest | 95 | **−0.34** | −0.25 | 44.2 | 10.8% |
| Q2 | 94 | −5.04 | −18.88 | 23.4 | 38.8% |
| Q3 | 94 | −14.50 | −31.62 | 29.8 | 83.1% |
| Q4 | 94 | −16.78 | −34.08 | 22.3 | 196.3% |
| Q5 highest | 95 | **−22.73** | −38.35 | 25.3 | 1800.0% |

Spearman(log turnover, fwd_7) = −0.285, p = 2.8e−10. The lowest-turnover
quintile shows NO post-listing fade at +7d; the entire fade phenomenon is
concentrated where money traded.

## Finding 2 — turnover is an attention meter [DATA]

Spearman correlations of log(turnover): range_day0 **+0.844**, pop_day0
+0.785, ann_vol_7d +0.473, max_daily_7d +0.246. High-turnover launches are
exactly the extreme first-day speculation events (Q5 median day-0 range:
1800%).

## Finding 3 — independent effect, but entangled with volatility [DATA]

OLS fwd_7 ~ const + log_pop + log_range + ann_vol + log_turnover:
log_turnover b = −2.32 pp (t = −2.53), incremental over controls; R² rises
only 0.340 → 0.349. With log_turnover in the model, log_range flips to
−5.71 (t = −3.19) — the two channels share variance (ρ = 0.84) and cannot be
cleanly separated at this sample size.

## Finding 4 — persistent across years, not a giant artifact [DATA]

EW−VW gap: full panel +17.27 pp; excluding top-5 weight events (TRUMP, SHIB,
ALICE, XPL, THE) still +10.17 pp; 2021–22 +18.58 vs 2023–26 +16.52. Present
in every calendar year (2021: EW −11.4 vs VW −33.2; … 2026: −0.3 vs −13.6).
Caveat: 2026 median day-0 turnover (0.4 M$) is anomalously low vs prior years
— verify before relying on that year's VW number.

Top turnover-decile composition: hype/narrative launches (TRUMP, SHIB, ALICE,
XPL, SAGA, BOME…); median fwd_7 of the decile −31.3%. Exceptions exist (ENA
+60%) — the effect is probabilistic, not deterministic.

## Interpretation (mechanism chain)

Miller (1977) divergence-of-opinion + short-sale constraints: prices are set
by the most optimistic participants; the more extreme the disagreement, the
higher the transient price and the deeper the reversion as disagreement and
attention decay. In IPO equity data, opening-day uncertainty/divergence
proxies predict long-run underperformance (Amihud 2006; Houge et al. 2001).
Day-0 USD turnover in crypto listings is precisely such a proxy — it measures
how much disagreement-and-attention money changed hands on day one.

Chain: attention → extreme day-0 ranges/pops + record turnover → price held
by optimists → attention decay → fade. Dollars systematically buy the top of
the attention cycle, hence −28.7% money-weighted vs −11.45% token-weighted.
Delisting is a separate, second-order channel (+0.95 pp wedge).

[EXPERT] This mechanism is the standard explanation for IPO underperformance;
applying it to exchange listings with turnover as the divergence proxy is, to
our knowledge, new. [SPECULATION] The residual unexplained part likely
includes launch-price mechanics (initial float, vesting schedules) that we
cannot observe publicly.

## What we did NOT find

- No public dataset of listing-day floating supply/market cap to test the
  float-turnover channel directly.
- Causality remains correlational: turnover may proxy unobserved quality or
  insider-schedule effects rather than cause the fade.
