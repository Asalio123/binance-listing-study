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
- Сматчено анонсов: **97/99** (true delist 73, migration 24; TG-text fallback: 0) [DATA].
- Несматчено: 2 (NBTUSDT, BETHUSDT) [DATA].
- Медианный лаг анонс→конец торгов: 14 дн [DATA].

### True delistings — event study ±14д (n=73)
| Метрика | n | медиана, % | %>0 | Wilcoxon p |
|---|---|---|---|---|
| День 0 (close−1→close0) | 73 | -28.49 | 5 | 0.0000 |
| +1д от close−1 | 73 | -27.94 | 8 | 0.0000 |
| +3д от close−1 | 73 | -33.23 | 8 | 0.0000 |
| +7д от close−1 | 73 | -47.00 | 8 | 0.0000 |
| +14д от close−1 | 73 | -61.23 | 7 | 0.0000 |
| −14д→−1д (drift до анонса) | 73 | -7.48 | 30 | 0.0000 |
| close0 → last close (после анонса) | 73 | -51.48 | 16 | 0.0000 |
| close−1 → last close (полный эффект) | 73 | -61.23 | 7 | 0.0000 |
| B&H: close листинга д0 → last close | 73 | -98.25 | 1 | 0.0000 |

### Migrations/rebrands — контрастная группа (n=24)
| Метрика | n | медиана, % | %>0 | Wilcoxon p |
|---|---|---|---|---|
| День 0 (close−1→close0) | 23 | +7.88 | 78 | 0.0054 |
| +1д от close−1 | 23 | +6.58 | 78 | 0.0123 |
| +3д от close−1 | 23 | +2.01 | 70 | 0.0650 |
| +7д от close−1 | 23 | +3.47 | 57 | 0.1186 |
| +14д от close−1 | 23 | +10.65 | 65 | 0.0031 |
| −14д→−1д (drift до анонса) | 23 | -4.06 | 48 | 0.9406 |
| close0 → last close (после анонса) | 23 | +7.58 | 65 | 0.0327 |
| close−1 → last close (полный эффект) | 23 | +19.76 | 70 | 0.0017 |
| B&H: close листинга д0 → last close | 23 | -83.80 | 9 | 0.0000 |

## Выводы
- Памп-перед-смертью: день анонса медиана **-28.5%**, позитивных 5% (n=73) [DATA].
- Между анонсом и концом торгов (close0→last): медиана **-51.5%** (n=73) [DATA].
- Полный жизненный цикл B&H: медиана **-98.3%**, позитивных 1% (n=73) [DATA].
