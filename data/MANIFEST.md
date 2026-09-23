# Data manifest

Every committed artifact under `data/`, one row per file. Row counts exclude the
header. Cache directories are listed per directory with a filename template, not
per file (6,065 cache files total). Regeneration: run the source script from the
repo root (`python src/<script>.py`); scripts marked *(network)* hit public
endpoints (data.binance.vision, Binance REST/CMS, Bybit public archive,
web.archive.org, t.me), the rest are pure recompute over the caches.

## Calendars and panels

| File | Rows | Size | Contents | Source script |
|---|---|---|---|---|
| `listing_calendar_binance.csv` | 3,682 | 96K | Point-in-time calendar of every archived Binance symbol: first/last month with klines, delisted flag | `build_calendar.py` *(network)* |
| `listing_calendar_bybit.csv` | 1,032 | 28K | Bybit spot USDT listing calendar (holdout exchange) | `build_bybit_calendar.py` *(network)* |
| `listing_events_enriched.csv` | 470 | 156K | Analysis panel: one row per Binance USDT listing 2021-01+, 28 features (pop, range, fwd returns, truncation flags, volume decay, streaks) — delisted tokens included | `enriched_study.py` *(network)* |
| `panel_exclusions.csv` | 120 | 12K | C2 panel-hygiene exclusions: 59 misdated events (earlier non-USDT quote) + 61 special pairs (xStocks, stablecoin pairs), with per-symbol reason | derived for `paper/panel_robustness.md` (no script) |
| `coinbase_calendar.csv` | 603 | 32K | Death-inclusive Coinbase Exchange product calendar (incl. 180 delisted) | `build_coinbase_calendar.py` *(network)* |
| `coinbase_events.csv` | 566 | 80K | Coinbase replication panel (event-level returns) | `build_coinbase_calendar.py` *(network)* |
| `coinbase_overlap.csv` | 198 | 12K | Overlap between the Binance panel and Coinbase calendar by base asset | `build_coinbase_calendar.py` *(network)* |

## Event-study outputs

| File | Rows | Size | Contents | Source script |
|---|---|---|---|---|
| `day0_turnover.csv` | 472 | 20K | Day-0 quote-asset (USD) turnover per event (computed pre-exclusion of 2 leveraged tokens; merged downstream on symbol) | `binance_day0_turnover.py` *(network)* |
| `post_window_car.csv` | 470 | 72K | BTC-adjusted log CARs at +1/+3/+7d from day-0 close, merged with raw fwd returns | `post_window_inference.py` |
| `bootstrap_vw_ci.csv` | 16 | 4K | Month-block bootstrap CIs for the headline statistics (VW medians, gap, quintile gradient) | `bootstrap_vw_ci.py` |
| `survivorship_simulation.csv` | 56 | 8K | Point-in-time survivorship simulation: EW/VW median shift by month | `survivorship_simulation.py` |
| `funding_sweep.csv` | 470 | 52K | Perpetual-funding sweep: perp availability, spot→perp lag, week-1/month-1 funding sums per name | `funding_sweep.py` *(network)* |
| `short_pnl_check.csv` | 24 | 8K | Frozen-definition net short P&L check (top day-0 turnover names, funding netted) | `short_pnl_check.py` *(network)* |

## Announcements and intraday

| File | Rows | Size | Contents | Source script |
|---|---|---|---|---|
| `announcement_dates.csv` | 468 | 60K | Announcement timestamps for 468/470 events (Binance CMS + Telegram cross-validation), match pattern and confidence grade per event | `build_announcement_dates.py` |
| `announcement_lag_analysis.csv` | 470 | 64K | Announcement→trading lag per event with pre-announcement drift statistics | `announcement_lag.py` |
| `announcement_shock.csv` | 468 | 52K | Minute-level returns around the announcement timestamp | `announcement_shock.py` |
| `announcement_premium_coinbase.csv` | 79 | 8K | Returns around Binance announcement timestamps measured on Coinbase (79 cross-listed events) | generator: `src/build_announcement_premium.py` (offline, from announcement_dates.csv + listing_events_enriched.csv + coinbase_candles_cache/); one v1 cell corrected (POWRUSDT post7: gap-skipping positional index → calendar date; published medians invariant) |
| `intraday_day0.csv` | 470 | 56K | Minute-level day-0 anatomy: first-hour return, time-to-peak, volume share, listing open timestamp | `fetch_intraday_day0.py` *(network)* |
| `day0_microstructure.csv` | 470 | 88K | Day-0 microstructure aggregates from the minute cache | `day0_microstructure.py` |
| `delisting_events.csv` | 98 | 44K | Delisting event study: 98 located delisting announcements with post-announcement returns | `build_delisting_study.py` *(network)* |

## Cross-exchange and raw scrapes

| File | Rows | Size | Contents | Source script |
|---|---|---|---|---|
| `cc_dates.csv` | 49 | 4K | CryptoCompare listing-event dates (external calendar cross-check) | `cc_announcements.py` *(network)* |
| `cc_coverage.csv` | 38 | 4K | CryptoCompare coverage audit vs the panel (first seen date, lag, credibility flag) | derived during `paper/verification_2026-08-28.md` (no script) |
| `cc_raw.jsonl` | — | 12K | Raw CryptoCompare API responses | `cc_announcements.py` *(network)* |
| `cc_state.json` | — | 4K | Pagination state for the CryptoCompare fetcher | `cc_announcements.py` *(network)* |
| `binance_announcements.csv` | 0 | 4K | Wayback-machine announcement scrape (superseded by the CMS/TG pipeline; kept for provenance) | `scrape_announcements.py` *(network)* |
| `wayback_cdx_raw.txt` | — | 0B | Raw Wayback CDX index dump (empty upstream response, kept for provenance) | `scrape_announcements.py` *(network)* |
| `cms_catalog48_titles_scout.json` | — | 248K | Binance CMS catalog scout dump (article titles) | `fetch_announcements_cms.py` *(network)* |
| `cms_will_list_matches_scout.json` | — | 56K | CMS "will list" title matches from the scout pass | `fetch_announcements_cms.py` *(network)* |
| `tg_announcements_scrape.json` | — | 3.3M | Telegram @binance_announcements scrape used to cross-validate CMS timestamps | `fetch_announcements_tg.py` *(network)* |

## Cache directories (not listed file-by-file)

| Directory | Files | Size | Template | Written by |
|---|---|---|---|---|
| `binance_day_closes/` | 1,012 | 4.0M | `<SYMBOL>-<YYYY-MM>.json` — daily closes per symbol-month | `post_window_inference.py` |
| `announce_shock_cache/` | 187 | 2.0M | `<SYMBOL>_bybit_<UTCts>.json` — Bybit minute klines around Binance announcements | `announcement_shock.py` *(network)* |
| `bybit_klines_cache/` | 419 | 2.5M | `<SYMBOL>.json` — Bybit daily klines per holdout symbol | `bybit_holdout.py`, `bybit_h2_annvol.py` *(network)* |
| `cms_details_cache/` | 2,261 | 95M | `<md5>.json` — Binance CMS article detail responses | `fetch_announcements_cms.py`, `build_announcement_dates.py`, `fetch_notice_articles.py`, `build_delisting_study.py` *(network)* |
| `coinbase_candles_cache/` | 603 | 34M | `<BASE>-USD.json` — Coinbase daily candles per product | `build_coinbase_calendar.py` *(network)* |
| `delisting_cms_cache/` | 319 | 13M | `<md5>.json` — CMS detail responses for delisting notices | `build_delisting_study.py` *(network)* |
| `delisting_klines_cache/` | 312 | 1.2M | `<SYMBOL>-<YYYY-MM>.json` — daily klines around delisting events | `build_delisting_study.py` *(network)* |
| `funding_cache/` | 470 | 6.2M | `<SYMBOL>.json` — Binance USD-M funding-rate history per symbol | `funding_sweep.py` *(network)* |
| `intraday_day0_cache/` | 470 | 15M | `<SYMBOL>_<YYYY-MM-DD>_daily.zip` — raw day-0 minute klines | `fetch_intraday_day0.py`, `day0_microstructure.py` *(network)* |
| `short_pnl_cache/` | 12 | 48K | `<SYMBOL>.json` — perp prices + funding for the frozen short-P&L check | `short_pnl_check.py` *(network)* |
