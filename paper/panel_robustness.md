# Panel robustness: re-pairing events, tokenized stocks, stablecoin pairs (2026-09-19)

Addresses committee audit 2026-09-19, item C2. Panel is NOT re-dated; this is
an exclusion-based robustness row plus disclosure, per the audit decision.
Inputs read-only: `data/listing_calendar_binance.csv`,
`data/listing_events_enriched.csv`, `data/day0_turnover.csv`.
Output: `data/panel_exclusions.csv` (120 rows).

## 1. Exclusion sets

### 1a. Misdated events (n = 59)
A panel event (BASE/USDT first month M) is flagged if the Binance calendar
contains the same base asset quoted against a different currency from the core
set {BUSD, USDC, FDUSD, TUSD, BTC, ETH, BNB} with an earlier first month.
Exact base+quote string matching (no prefix heuristics) to avoid collisions
of the "ARBUSD = ARB+USD vs AR+BUSD" type.

Verification against the audit:
- 59/470 = 12.6% — matches audit (59).
- Channel: 45 via fiat/stable quotes, 14 via BTC/ETH/BNB only — matches audit
  (45/14).
- 41 events have the true debut before 2021-01 (violates the panel's own
  inclusion rule) — matches audit (41).
- Median gap between the true and panel first month: 25.0 months
  (audit reports 24.9; the 0.1 difference is a month-counting rounding
  convention, not a data discrepancy).
- Spot checks reproduce the audit: SNTUSDT dated 2023-05 with SNTETH debut
  2017-07; SKYUSDT dated 2025-09 with SKYBTC debut 2018-05 (88 months).

### 1b. xStocks (n = 56)
All 56 events with first month 2026-06/2026-07 whose base ticker ends in "B"
(SPCXBUSDT ... HOODBUSDT). These are tokenized equities, not tokens. The
remaining three debuts of the same wave (REUSDT, GRAMUSDT, AEROUSDT) are real
crypto tokens (multi-quote listing waves on the calendar) and stay in.
Verification against the audit:
- n = 56 — matches.
- Median day-0 pop: 0.00 — matches audit ("pop медиана 0.00").
- Median fwd_30: +1.28% (all 56; +0.09% on the 46 with a full 30-day window).
  The audit printed +0.42%; I could not reproduce that exact figure (it is the
  27th order statistic of the sorted values), but all variants agree on the
  substance: flat around zero versus -27.4% for the rest.
- Rest of panel (470 - 56 - 5 stables): median fwd_30 = -27.38% — matches the
  audit's -27.3%.

### 1c. Stablecoin-quoted pairs (n = 5)
USDPUSDT (2021-09), FDUSDUSDT (2023-07), XUSDUSDT (2025-03), USD1USDT
(2025-05), BFUSDUSDT (2025-08). These are fiat-proxy crosses, not token
listings.

No overlap between the three sets; total exclusions 59 + 56 + 5 = 120;
clean panel n = 350. Direction of the contamination is against the fade
(xStocks pop 0.00, fwd_30 ~0; misdated events are seasoned assets with muted
day-0 reactions: full-panel pop median 0.28 vs 0.54 on the clean panel), so
removal strengthens the headline numbers — the bias was conservative.

## 2. Table II on the clean panel (n = 350) vs full panel (n = 470)

Forward returns from the day-0 close; Wilcoxon signed-rank p; %>0 = share of
positive returns. Same conventions as `paper/stats_tables.md` (truncated
windows included, as in Table S1).

| Horizon | Full median % | Full Wilcoxon p | Full %>0 | Clean median % | Clean Wilcoxon p | Clean %>0 |
|---|---|---|---|---|---|---|
| +1d  | -4.45  | 7.86e-13 | 32.6 | -6.51  | 1.02e-12 | 28.9 |
| +3d  | -8.87  | 9.98e-16 | 27.4 | -11.17 | 2.45e-14 | 24.9 |
| +7d  | -11.45 | 3.38e-17 | 28.9 | -14.32 | 8.68e-15 | 26.6 |
| +14d | -14.51 | 8.59e-19 | 28.9 | -20.57 | 9.60e-16 | 27.4 |
| +30d | -21.53 | 1.03e-18 | 29.1 | -30.99 | 2.30e-14 | 27.1 |

Turnover-weighted median fwd_7 (nearest-rank weighted median, weights =
`day0_turnover.csv:usd_turnover`, sorted by value — the published, correct
algorithm; reproduces -28.72% on the full panel):

| Panel | n | USD-weighted median fwd_7 |
|---|---|---|
| Full  | 470 | -28.72% |
| Clean | 350 | -28.89% |

Means for context: mean fwd_7 full -6.65% vs clean -7.81%; mean fwd_30
full -7.29% vs clean -7.36%.

## 3. Interpretation

- The fade is stronger, not weaker, on the clean panel: week-one median
  -14.32% vs -11.45%; month-one median -30.99% vs -21.53%. Every Wilcoxon p
  stays <= 2.5e-14.
- The dollar-weighted week-one median is essentially unchanged (-28.89% vs
  -28.72%): the excluded events carry little day-0 turnover weight relative
  to the headline listings.
- Conclusion for the manuscript: headline numbers are conservative; report the
  robustness row and disclose the panel composition. Full re-dating by
  first-any-quote remains the owner's deferred decision (changes every number
  in the paper; not done here).
