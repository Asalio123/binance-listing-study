# Release v1.1.0 — готовый текст для GitHub release (→ Zenodo DOI)

Создать релиз: GitHub repo → Releases → Draft a new release → tag `v1.1.0` →
вставить текст ниже → Publish. После линковки репо с Zenodo депозит создастся
автоматически из `.zenodo.json`.

---

Second public release of the companion repository for the preprint
**"Post-Listing Underperformance in Cryptocurrency Markets: Evidence from Every
Binance USDT Listing, 2021–2026"** (Said Bakhtiev, 2026).

## What is new in v1.1.0 (wave 2)

- `data/delisting_events.csv` — 98-event delisting study (73 true delistings,
  25 migrations/swaps), with CMS and kline caches
- `data/funding_sweep.csv` — full-panel perpetual funding sweep (470 names):
  perp availability, spot→perp lag, week-1/month-1 funding sums
- `data/short_pnl_check.csv` — frozen-definition net short-P&L check
- `data/announcement_shock.csv` + `data/announce_shock_cache/` — minute-level
  returns around announcement timestamps
- `data/bootstrap_vw_ci.csv` — month-block bootstrap CIs for the dollar-weighted
  headline statistics
- `data/panel_exclusions.csv` — panel-hygiene exclusion list (misdated and
  special-purpose pairs) used by the robustness appendix
- Repo hygiene: all `src/*.py` use repo-local paths (fresh-clone runnable),
  the VW-median print bug in `post_window_inference.py` is fixed and reproduces
  the published −35.46%, `data/MANIFEST.md` documents every artifact, and
  `./build_cjsj.sh` verifies the headline numbers from the CSVs offline.

## Wave 1 (v1.0.0) contents

**Data**
- `data/listing_calendar_binance.csv` — point-in-time calendar of 3,682 archived
  Binance symbols (first/last month, delisting flag), rebuilt from the raw
  data.binance.vision archive
- `data/listing_calendar_bybit.csv` — 829 Bybit spot USDT listings
- `data/listing_events_enriched.csv` — the analysis panel: 470 events × 28
  features (delisted tokens included)
- `data/day0_turnover.csv` — day-0 quote-asset (USD) turnover for all 470 events
- `data/post_window_car.csv` — event-study outputs
- `data/announcement_dates.csv` — announcement timestamps for 468 of 470 events
  (Binance public content API + Telegram cross-validation), with match patterns
  and confidence grades
- `data/coinbase_calendar.csv`, `coinbase_events.csv`, `coinbase_overlap.csv` —
  death-inclusive Coinbase Exchange calendar (603 products, 180 delisted) and
  the 566-event replication panel
- `data/intraday_day0.csv` — minute-level day-0 anatomy for all 470 events
  (first-hour return, time-to-peak, volume share, listing open timestamp)
- `data/announcement_premium_coinbase.csv` — returns around Binance announcement
  timestamps measured on Coinbase (79 cross-listed events)
- `data/binance_day_closes/`, `data/bybit_klines_cache/`,
  `data/coinbase_candles_cache/`, `data/intraday_day0_cache/`,
  `data/cms_details_cache/`, `data/tg_announcements_scrape.json` — raw caches
  for exact replication

**Code** (`src/`) — calendar builders (Binance + Bybit + Coinbase), event-study
engine, statistics, pre-specified Bybit holdout, announcement-date
reconstruction (CMS + Telegram), intraday day-0 fetcher, chart generation.

**Paper** (`paper/`) — preprint PDF and sources, the claim-by-claim
falsification matrix for the prior listing literature (`FALSIFICATION.md`),
and statistical appendices.

## Headline numbers (n = 470, death-inclusive)

- Median fwd returns from day-0 close: −4.45% (+1d), −11.45% (+7d), −21.53% (+30d)
- Dollar-weighted week-one median: −28.72% raw, −35.46% BTC-adjusted
- Delisting explains +0.96 pp of the token-vs-dollar gap; survivorship shift
  on medians +0.35 pp (n.s.)
- Preregistered Bybit holdout (415 survivors): fade replicates (−10.34%,
  BH p = 8×10⁻¹⁴); H2 volatility gradient does not replicate (sign flip)

## Citing

See `CITATION.cff`. DOI of this dataset (Zenodo) and of the preprint (SSRN)
will be added to this section and the README after deposit.

## License

MIT.
