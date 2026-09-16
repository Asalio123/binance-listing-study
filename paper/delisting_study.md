# Зеркальное event study: анонсы делистингов Binance
Собрано: 2026-09-16 [DATA]. Скрипт: `src/build_delisting_study.py`; данные: `data/delisting_events.csv`.
## Метод
- Вселенная: 99 делистнутых USDT-символов панели 470 (`listing_events_enriched.csv`, delisted=1) [DATA].
- ГРАБЛЯ: `panel.last_date` у 52/99 усечён 1000-дневным лимитом исходного event study (`days_listed==1000`) — это не дата смерти. Истинный месяц смерти — `listing_calendar_binance.csv:last_month`, точный день = последний дневной kline в архиве [DATA].
- Анонсы: Binance CMS (`cms_details_cache` + догрузка тел по кодам из TG-дампа @binance_announcements через публичный bapi article endpoint в `delisting_cms_cache/`, ~330 кодов); спот-only (margin/futures/grid/loan/completion-нотификации исключены по заголовку) [DATA].
- Rebrand/swap/migration/merge (заголовок «Will Support the ... Token Swap/Rebranding ...») → `event_type=migration`, контрастная группа, в headline-статистику делистингов не входит [DATA].
- Матчинг: base-тикер в статье (тайтл-список «Will Delist A, B, C», «Name (TICKER)», пары XYZ/USDT в теле, data.pairs); окно = месяц смерти −180д .. +5д; берётся ПОСЛЕДНИЙ анонс перед смертью (для vote-to-delist это статья с результатами голосования = момент, когда смерть становится достоверной) [DATA].
- Klines: monthly zip data.binance.vision за [анонс−35д, анонс+35д], кэш `delisting_klines_cache/`; единицы open_time нормализованы по длине (мс/мкс/нс) [DATA].
- День 0 = UTC-дата анонса. fwd_h — от close дня −1; ret_day0 = close0/close−1; post_death = до последнего close; смерть раньше горизонта → mark-to-last с флагом trunc. Спотчек цен против свежей выгрузки архива: совпадение до 4 знаков (ALPACA 2025-04, FIRO 2025-04) [DATA].
## Покрытие
- Сматчено анонсов: **98/99** (true delist 73, migration 25; TG-text fallback: 0) [DATA].
- Несматчено: 1 (NBTUSDT: тихое снятие без анонса — проверены TG-дамп 2017-2026, весь каталог Delisting (433 статьи, id 82912..284618), тела notice Feb-Mar 2023) [DATA].
- Медианный лаг анонс→конец торгов: 14 дн (min 0 — UST, halt в день краха 2022-05-13; max 41 — BETH, конверсионный notice) [DATA].
- trunc_14 (смерть раньше 14-го дня) у delist: 51% [DATA].

### Механизмы смерти (по заголовкам сматченных статей)
| event_type | механизм | n |
|---|---|---|
| delist | notice-of-removal | 6 |
| delist | vote-to-delist | 9 |
| delist | will-delist batch | 58 |
| migration | migration/swap | 24 |
| migration | other | 1 |

### True delistings — event study ±14д (n=73)
| Метрика | n | медиана, % | %>0 | Wilcoxon p |
|---|---|---|---|---|
| День 0 (close−1→close0) | 73 | -28.49 | 5 | <0.0001 |
| +1д от close−1 | 73 | -27.94 | 8 | <0.0001 |
| +3д от close−1 | 73 | -33.23 | 8 | <0.0001 |
| +7д от close−1 | 73 | -47.00 | 8 | <0.0001 |
| +14д от close−1 | 73 | -61.23 | 7 | <0.0001 |
| −14д→−1д (drift до анонса) | 73 | -7.48 | 30 | <0.0001 |
| close0 → last close (после анонса) | 73 | -51.48 | 16 | <0.0001 |
| close−1 → last close (полный эффект) | 73 | -61.23 | 7 | <0.0001 |
| B&H: close листинга д0 → last close | 73 | -98.25 | 1 | <0.0001 |

### Migrations/rebrands — контрастная группа (n=25)
| Метрика | n | медиана, % | %>0 | Wilcoxon p |
|---|---|---|---|---|
| День 0 (close−1→close0) | 25 | +7.88 | 76 | 0.0038 |
| +1д от close−1 | 25 | +6.58 | 76 | 0.0096 |
| +3д от close−1 | 25 | +2.01 | 68 | 0.0516 |
| +7д от close−1 | 25 | +3.47 | 56 | 0.0851 |
| +14д от close−1 | 25 | +10.65 | 64 | 0.0023 |
| −14д→−1д (drift до анонса) | 25 | -5.67 | 44 | 0.8949 |
| close0 → last close (после анонса) | 25 | +7.58 | 64 | 0.0275 |
| close−1 → last close (полный эффект) | 25 | +19.76 | 68 | 0.0015 |
| B&H: close листинга д0 → last close | 25 | -83.80 | 12 | <0.0001 |

### Экстремумы дня 0 (true delistings)
Худшие: CREAMUSDT -61%; PROSUSDT -61%; BETAUSDT -58% [DATA].
Лучшие (dead-cat squeezes): ALPACAUSDT +47%; BSWUSDT +30%; VOXELUSDT +16% [DATA].

## Выводы
- Пампа-перед-смертью НЕТ: день анонса медиана **-28.5%**, позитивных 5% (n=73); дрейф за 14 дней до анонса -7.5% — рынок не выкупает смерть заранее, удар концентрирован в день анонса [DATA].
- Между анонсом и концом торгов (close0→last, медианный лаг 14 дн): медиана **-51.5%** — после первого удара цена делится ещё раз пополам [DATA].
- Полный жизненный цикл B&H (close дня листинга → последний close): медиана **-98.3%**, позитивных 1% (n=73) [DATA].
- Контраст migrations: день анонса swap/rebrand медиана **+7.9%**, позитивных 76% (n=25) — реакция противоположного знака, т.е. отрицательный эффект дня 0 специфичен именно смерти, а не любому «делистинговому» заголовку [DATA].
