# Сбор дат анонсов листингов Binance USDT — отчёт

Дата сборки: 2026-09-15. Статус: завершено. Все числа — [DATA] из файлов,
перечисленных в конце.

## Результат

- **Покрытие: 468/470 (99.6%)**. Несматченные: NBTUSDT, MULTIUSDT (оба delisted).
- Источник CMS: 427 строк, Telegram: 41 строка.
- Confidence: high 317, medium 110, low 41.

## Источники

1. **CMS detail API** (`/bapi/composite/v1/public/cms/article/detail/query`):
   полный свип 2255 статей каталога 48 («New Cryptocurrency Listing» и
   смежные — в каталоге оказались и «Notice of Addition/New Trading Pairs») +
   6 rescue-статей из support-каталога. Кэш: `data/cms_details_cache/`
   (2261 JSON). Поле `publishDate` (unix ms, UTC).
2. **Telegram** `t.me/s/binance_announcements`: 8784 сообщений,
   2017-09-17 → 2026-09-15, 440 страниц `?before=<msg_id>`.
   Дамп: `data/tg_announcements_scrape.json`; 4989 сообщений несут article code.

## Методология матчинга

Для каждого `symbol` панели (base = symbol без USDT) строится объединённый
пул кандидатов из CMS-статей и TG-сообщений.

Паттерны (ранг = приоритет):

| ранг | pattern | что извлекается | confidence |
|---|---|---|---|
| 0 | will_list | «Binance Will List X (TICKER)» — тикеры из скобок | high |
| 1 | lists | «Binance Lists X (TICKER)» | high |
| 2 | hodler | «Introducing X (TICKER) on Binance HODLer Airdrops» | high |
| 3 | launchpool | Launchpool-анонс | high |
| 4 | megadrop | Megadrop-анонс | high |
| 5 | launchpad | Launchpad sale / «Will Open Trading for TICKER» | high |
| 6 | adds_pairs | «Binance Adds … Trading Pairs» — пары TICKER/USDT из тела | medium |
| 6 | notice_pairs | «Notice of Addition/New Trading Pairs» — только ДОБАВЛЯЕМЫЕ пары (секция «open trading for», remove-секция исключается) | medium |
| 7 | rebrand | «Token Swap / Migration / Redenomination / Merge / Update the Ticker» — новый тикер после «to/into» | medium |
| 8 | tg_text / tg_adds | то же по тексту TG-сообщения | low |
| 9 | tg_rebrand | rebrand-анонс в TG | low |

Правила отбора из пула:

- ontime = кандидаты с `announce_ts ≤ day0+1д`; выбор по (ранг, близость к
  day0). TG-кандидатам +1ч к дистанции — при почти-ничьей побеждает CMS.
- **Guard от переиспользованных тикеров** (`proximity_override`): если
  приоритетный кандидат дальше 90 дней от day0, а другой кандидат ближе
  минимум на 30 дней (и в пределах 365 дней) — берётся ближний. Закрывает
  коллизии типа SKY (Skycoin 2018 vs Sky Protocol 2025) и пары,
  добавленные к давно листованному токену (POLY, ELF, IQ, CREAM, PIVX…).
  Срабатываний: 29.
- **RESCUE** (6 символов): rebrand/migration-статьи вне catalog48, найденные
  через TG, догружены по article code; тело каждой проверено на упоминание
  нового тикера: FIRO (XZC→FIRO, 2021-01-15), PUNDIX (NPXS redenomination,
  2021-03-31), BTTC (BTT migration, 2022-01-10), XNO (NANO→XNO, 2022-01-19),
  T (NU+KEEP merge, 2022-02-09), EPX (EPS→EPX, 2022-04-22).
- Особые случаи экстракции: mixed-case скобки («(XAUt)» → XAUT), CJK-тикеры
  (币安人生 — сырой матч по скобкам), однобуквенные тикеры (A, S, D… — только
  строгие скобки, полностью строчные «(s)» отброшены).

Лаг считается на дневном уровне: `day0_date` — дата (без времени), поэтому
лаг = `day0_date − normalize(announce_ts)` в днях. Часовой лаг систематически
смещён (медиана −3.5ч — артефакт полуночи day0), в отчёте не используется.

## Лаги анонс → день 0 [DATA]

- медиана 0 д | p25 0 | p75 1 | p90 8 | p99 23 | max 120
- =0 дней: 294/468 (62.8%); ≤1 дня: 78.0%; ≤3 дней: 82.5%; ≤7 дней: 88.9%
- нарушений «анонс позже day0+1д»: 0

## Валидация

1. **TG-кроссчек publishDate** (20 случайных CMS-матчей, random_state=42):
   медиана |Δ| = 2 мин, макс = 10 мин — CMS publishDate и TG datetime
   согласованы во всех эпохах 2021–2026 [DATA: data/announcements_build.log].
2. **trading_open_text vs day0**: из тела извлечён текст «open trading … at
   YYYY-MM-DD HH:MM (UTC)» для 220/468 строк; дата открытия совпала с
   day0_date в 99.1% (218/220). Несовпадения: PHAUSDT (аномалия, см. ниже),
   BNSOLUSDT (анонс 2024-10-09 с «open trading 2024-10-10», фактический спот
   по панели 2024-10-17 — у Binance был postpone margin-листинга; дата анонса
   корректна) [DATA].
3. Спот-чеки: PEPE 2023-05-05, SHIB 2021-05-10, TRUMP 2025-01-19 — точное
   совпадение с известными датами [DATA].

## Аномалии (отдельный список)

| symbol | announce | day0 | лаг | причина |
|---|---|---|---|---|
| PHAUSDT | 2021-02-25 | 2021-06-25 | 120 д | токен листован в феврале (PHA/BUSD и др.), USDT-пара добавлена в июне без найденного анонса; взят will_list токена |
| EPXUSDT | 2022-04-22 | 2022-05-23 | 31 д | миграция EPS→EPX анонсирована 04-22, отложена 05-17 («Delay in…»), завершена 05-23 — лаг объясним |
| SKYUSDT | 2025-07-18 | 2025-09-17 | 61 д | анонс ребрендинга MKR→SKY; длинное окно нотиса до завершения свопа |

Флаги в `notes`: `anomaly:lag_gt_30d` (3), `anomaly:announce_after_listing` (0).

## Особые категории

- **bstock** (токенизированные акции 2025–26): 56 строк, помечены по статье
  («bStocks» в заголовке), НЕ по суффиксу B (ARB/CKB/SHIB — обычные токены).
- **rebrand_swap**: 36 строк (6 CMS-rescue + 30 TG) — пары, рождённые
  свопом/ребрендингом без Will List (KAIA, LUMIA, S, A, POL, RENDER…).
- **leveraged**: 0 — в панели leveraged-токенов нет (JUP/SYRUP — обычные).

## Несматченные (2/470)

- **NBTUSDT** (day0 2022-03-11, delisted): «NBT» и «NBT/USDT» не встречаются
  ни в одном из 2261 тел статей CMS, ни в 8784 TG-сообщениях, ни в заголовках
  каталога. Гипотеза: тихое добавление пары без публичного анонса либо анонс
  в канале вне охвата.
- **MULTIUSDT** (day0 2022-04-06, delisted): MULTI/USDT найден только в
  margin-статье 2023-11-07. Спот-анонса нет ни в CMS, ни в TG. Гипотеза:
  тихое добавление USDT-пары к Multichain без анонса.

## Покрытие по годам (day0)

| год day0 | matched | всего |
|---|---|---|
| 2021 | 125 | 125 |
| 2022 | 39 | 41 |
| 2023 | 58 | 58 |
| 2024 | 63 | 63 |
| 2025 | 102 | 102 |
| 2026 | 81 | 81 |

Delisted в matched: 97/99 (оба промаха — delisted).

## Операционные заметки

- Rate limit реален: HTTP 429 возникал каждые ~120–150 быстрых запросов;
  бэкофф 60/120/240 с справлялся. Полный свип 2255 деталей занял ~2 ч с
  перезапуском (первый процесс убит на 1225/2255; кэш сделал сбор
  возобновляемым без потерь).
- TG-скрейп: 440 страниц, ~13 мин, без банов.

## Файлы

- `data/announcement_dates.csv` — итог (symbol, announce_ts_utc,
  trading_open_text, article_code, match_pattern, source, confidence, notes).
- `src/fetch_announcements_cms.py` — свип CMS detail (кэш, бэкофф).
- `src/fetch_notice_articles.py` — догрузка notice-статей по TG-ссылкам.
- `src/fetch_announcements_tg.py` — скрейп TG-канала (пагинация before=).
- `src/build_announcement_dates.py` — матчинг, валидация, CSV.
- `data/cms_details_cache/` (2261), `data/tg_announcements_scrape.json`,
  `data/cms_fetch.log`, `data/notice_fetch.log`, `data/announcements_build.log`.
