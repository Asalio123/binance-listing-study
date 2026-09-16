# Зеркальное event study: анонсы делистингов Binance
Собрано: 2026-09-16 [DATA]. Скрипт: `src/build_delisting_study.py`; данные: `data/delisting_events.csv`.
## Метод
- Вселенная: 99 делистнутых USDT-символов панели 470 (`listing_events_enriched.csv`, delisted=1) [DATA].
- Анонсы делистингов: Binance CMS (`cms_details_cache` + догрузка тел по кодам из TG-дампа @binance_announcements через публичный bapi article endpoint в `delisting_cms_cache/`); спот-only (margin/futures/grid/loan исключены по заголовку) [DATA].
- Rebrand/swap/migration/merge → `event_type=migration`, в headline не входят (контрастная группа) [DATA].
- Матчинг: base-тикер в статье (тайтл-список, «Name (TICKER)», пары XYZ/USDT в теле, data.pairs), publishDate в [last_date−150д, last_date+5д], берётся ближайший анонс перед last_date [DATA].
- Klines: monthly zip data.binance.vision за [анонс−35д, анонс+35д], кэш `delisting_klines_cache/` [DATA].
- День 0 = UTC-дата анонса. Доходности от close дня −1 (fwd_h, день 0 = ret_day0) и от close дня 0 (post_death_from_0 = до последнего close перед концом торгов). trunc: смерть раньше горизонта → mark-to-last [DATA].
## Покрытие
- Сматчено анонсов: **40/99** (true delist 40, migration 0; TG-text fallback: 14) [DATA].
- Несматчено: 59 (FIROUSDT, TRUUSDT, LITUSDT, PERPUSDT, RAMPUSDT, DEGOUSDT, OMUSDT, BADGERUSDT, LINAUSDT, FISUSDT, BURGERUSDT, BAKEUSDT, EPSUSDT, FORTHUSDT, ERNUSDT, NUUSDT, KLAYUSDT, ATAUSDT, KEEPUSDT, CLVUSDT, MLNUSDT, TVKUSDT, GHSTUSDT, ALPACAUSDT, MBOXUSDT, FARMUSDT, VIDTUSDT, POLYUSDT, SYSUSDT, IDEXUSDT, DFUSDT, ELFUSDT, BETAUSDT, CHESSUSDT, FRONTUSDT, RNDRUSDT, RGTUSDT, PLAUSDT, BNXUSDT, DARUSDT, VOXELUSDT, HIGHUSDT, MCUSDT, ANYUSDT, FXSUSDT, ACAUSDT, LOKAUSDT, BSWUSDT, KDAUSDT, NBTUSDT, BIFIUSDT, REIUSDT, GALUSDT, PHBUSDT, HOOKUSDT, AGIXUSDT, BETHUSDT, OMNIUSDT, TONUSDT) [DATA].
- Медианный лаг анонс→конец торгов: 7 дн [DATA].

### True delistings — event study ±14д (n=40)
| Метрика | n | медиана, % | %>0 | Wilcoxon p |
|---|---|---|---|---|
| День 0 (close−1→close0) | 40 | -31.18 | 0 | 0.0000 |
| +1д от close−1 | 33 | -32.39 | 6 | 0.0000 |
| +3д от close−1 | 33 | -33.20 | 6 | 0.0000 |
| +7д от close−1 | 33 | -41.19 | 9 | 0.0000 |
| +14д от close−1 | 33 | -49.88 | 12 | 0.0000 |
| −14д→−1д (drift до анонса) | 40 | -9.60 | 28 | 0.0001 |
| close0 → last close (после анонса) | 33 | -26.89 | 24 | 0.0071 |
| close−1 → last close (полный эффект) | 33 | -49.88 | 12 | 0.0000 |
| B&H: close листинга д0 → last close | 33 | -95.44 | 3 | 0.0000 |

### Migrations/rebrands — контрастная группа (n=0)
| Метрика | n | медиана, % | %>0 | Wilcoxon p |
|---|---|---|---|---|
| День 0 (close−1→close0) | 0 | +nan | nan | — |
| +1д от close−1 | 0 | +nan | nan | — |
| +3д от close−1 | 0 | +nan | nan | — |
| +7д от close−1 | 0 | +nan | nan | — |
| +14д от close−1 | 0 | +nan | nan | — |
| −14д→−1д (drift до анонса) | 0 | +nan | nan | — |
| close0 → last close (после анонса) | 0 | +nan | nan | — |
| close−1 → last close (полный эффект) | 0 | +nan | nan | — |
| B&H: close листинга д0 → last close | 0 | +nan | nan | — |

## Выводы
- Памп-перед-смертью: день анонса медиана **-31.2%**, позитивных 0% (n=40) [DATA].
- Между анонсом и концом торгов (close0→last): медиана **-26.9%** (n=33) [DATA].
- Полный жизненный цикл B&H: медиана **-95.4%**, позитивных 3% (n=33) [DATA].
