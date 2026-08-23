# Methodology

## Data sources

| Source | What | Access |
|---|---|---|
| data.binance.vision (S3) | monthly 1d-kline archives per symbol, **including delisted pairs** | anonymous, free |
| api.binance.com `/api/v3/klines` | daily klines for surviving symbols (faster than archive) | public, no key |

## Building the point-in-time listing calendar

1. Walk the flat S3 index `data/spot/monthly/klines/` via symbol-folder pagination
   (`Delimiter='/'`, then per-symbol `1d/` prefix, threaded).
2. For each symbol: `first_month` = earliest archive month → **listing month**;
   `last_month` = latest month; if `last_month` < current-1 → flag `delisted=1`.
3. Keep only `*USDT` spot symbols; exclude leveraged-token families
   (`UP/DOWN/BULL/BEAR`) — they were mass-delisted in 2021 and are not equity-like events.

Result: 3683 symbols total; 472 USDT listings from 2021-01 onward form the event sample.

## Event study

For each event, the full daily OHLCV path is fetched from REST; if the symbol is
delisted (REST returns nothing), monthly archive zips are stitched instead
(timestamp unit switches ms→µs in 2025 — handled).

Entry reference = **close of day 0** (the first trading day). Forward returns are
measured to closes at +1/+3/+7/+14/+30 trading days.

### Survivorship & truncation handling

- Delisted coins contribute their real post-listing path from archive data.
- If the path ends before a horizon, the return is **marked to last available close**
  and flagged in `trunc_*`. Re-running with hard `-100%` on truncation makes every
  horizon worse — conclusions are conservative either way.
- Sanity anchor vs external data: CryptoRank's 559-listing Binance panel reports
  median ROI ≈ 0.12x; our median +7d of −11.5% is consistent with "most listings bleed".

## Known limitations

- No historical order-book depth exists publicly → open liquidity/slippage not modelled.
- Announcement timestamps are not reconstructed; this study covers the post-open window only.
- Quote-asset multiplicity: some assets appear under several quote pairs; each USDT
  pair counts once. Non-USDT pairs excluded.
- Multiple-testing: this repo reports pre-specified horizons only; any strategy derived
  from these stats needs out-of-sample confirmation.
