# Verification 2026-09-19 — независимый аудит чисел комитетной волны + покрытие пунктов аудита

Дата: 2026-09-19. Объект: `paper/cjsj_manuscript.md` (текущее состояние после
исполнения `COMMITTEE_AUDIT_2026-09-19.md`) + сырые артефакты `data/`.
Метод: собственный код аудитора (pandas/numpy/scipy, один проход, без сети;
Bybit H1 пересчитан напрямую из `data/bybit_klines_cache/`, не запуском
`src/bybit_holdout.py`). Чужие скрипты читались только для понимания
дефиниций; все числа ниже пересчитаны независимо.

Итог: **Часть 1 — 21/21 проверенное число воспроизводится (0 расхождений).
Часть 2 — C1–C3 закрыты; M1–M3, M5, M7, M8, M10 закрыты; M4, M6, M9 частично;
minors 11/15 закрыты, 2 открыты, 1 частично, 1 информационный.**

## Часть 1. Пересчёт новых чисел из сырых артефактов

### C1 — survivorship_simulation.csv (56 месячных точек, 2022-01…2026-08)

| Число | В рукописи (III.C) | Пересчёт из CSV | Вердикт |
|---|---|---|---|
| VW max смещение | «at most +1.9 pp (May 2025)» | vw_bias_pp max = **+1.9173 pp @ 2025-05-01** | ✓ |
| VW на Nov-2024 | (аудит: +0.61) | **+0.6086 pp @ 2024-11-01** | ✓ |
| Max доля выпавших | «peaks at 23% of the panel» | share_dropped max = **23.19% @ 2026-07-01** | ✓ (у аудита «13.2%» — это доля именно на 2024-11, 0.1319; оба согласованы) |
| EW диапазон | «at most ±1.5 pp» | bias_pp ∈ **[−0.4810, +1.4224] pp** | ✓ |
| Худшая точка live vs full | «−28.7% against the true −30.6%» | @2025-05: vw_f7_live = **−28.7211**, vw_f7_full = **−30.6385** | ✓ |
| «never flips sign» | III.C | min(med_f7_live) = −13.89%, min(med_f7_full) = −13.73% — знак не флипает нигде | ✓ |
| Старый fwd_30 +8.3 pp | удалён | bias30_pp ∈ [−1.30, +1.75] — стейл-числа нет ни в CSV, ни в тексте | ✓ |
| Limitation 6 (175 строк) | «1,000-day REST cap for 175 of 470 rows» | раскрытие в тексте есть; согласуется с C1-находкой | ✓ |

### C3 — short_pnl_check.csv

| Число | В рукописи (III.E) | Пересчёт | Вердикт |
|---|---|---|---|
| Медиана шорта n=12 | «median … earns +25.6%» | первые 12 строк (группа `frozen_day0_perp`): **+25.62%** | ✓ |
| Среднее шорта n=12 | «the mean earns +16.0%» | **+15.95%** | ✓ |
| Артефакт | «per-name PnL net of funding and costs: data/short_pnl_check.csv» | файл существует, 24 строки: `frozen_day0_perp` (n=12, публикуемая) + `audit_top12_no_filter` (n=12, медиана +34.21/среднее +30.27 — альтернативная дефиниция, в тексте не цитируется) | ✓ |

### C2 — panel_exclusions.csv + listing_events_enriched.csv + day0_turnover.csv

| Число | В рукописи | Пересчёт | Вердикт |
|---|---|---|---|
| Состав исключений | 59 re-pairings + 56 tokenized-stock + 5 stablecoin | reason counts: **misdated 59, xstock 56, stable 5; total 120** | ✓ |
| Clean n | «clean panel (n = 350)» | 470 − 120 = **350** | ✓ |
| Clean week-one median | «−14.32%» | **−14.32%** | ✓ |
| Clean month median | «−30.99%» | **−30.99%** | ✓ |
| Clean VW (веса day0_turnover, argsort по значению) | «−28.89% vs −28.72%» | clean **−28.89%**, full **−28.72%** | ✓ |
| Clean Wilcoxon | «all Wilcoxon p ≤ 2.5×10⁻¹⁴» | fwd_7: **8.7×10⁻¹⁵**; fwd_30: **2.3×10⁻¹⁴** | ✓ |

### M4 — bootstrap_vw_ci.csv (16 строк, сверены все)

| Статистика | CSV point [CI] | Текст | Вердикт |
|---|---|---|---|
| vw_median_fwd7 | −28.72 [−39.45, −19.79] | «−28.72% … CI [−39.45, −19.79]» | ✓ |
| vw_median_madj7_btcadj | −35.46 [−49.32, −22.31] | «−35.46% BTC-adjusted, CI [−49.32, −22.31]» | ✓ |
| wedge_delisting_vw | +0.96 [−3.41, +3.24] | «+0.96 pp (CI [−3.41, +3.24]…)» | ✓ |
| q5_minus_q1 (gradient) | −22.94 [−32.61, −13.25] | «Q5−Q1 = −22.9 pp, CI [−32.6, −13.3]» | ✓ |
| quintile_q1…q5 CIs | [−7.21,+.70] [−14.18,−1.85] [−20.50,−6.14] [−25.99,−12.95] [−33.15,−14.93] | «[−7.2,+0.7], [−14.2,−1.9], [−20.5,−6.1], [−26.0,−13.0], [−33.2,−14.9]» | ✓ (все округления корректны) |
| ew_minus_vw | 17.27 | Discussion: «disagree by 17 percentage points» | ✓ |

### BTC-adj квинтили из post_window_car.csv (текущий, n=470)

madj_7 без NaN (470/470 usable) — проблема «n=460» из аудита снята регенерацией
артефакта; текст n=460 нигде не упоминает. Квинтили по day-0 USD turnover:

| Квинтиль | Пересчёт | Текст | Вердикт |
|---|---|---|---|
| Q1 | −3.45% | −3.5% | ✓ |
| Q2 | −8.53% | −8.5% | ✓ |
| Q3 | −15.25% | −15.3% | ✓ |
| Q4 | −19.84% | −19.8% | ✓ |
| Q5 | −29.08% | −29.1% | ✓ |

Заодно: raw fwd_7 квинтили Fig. 6 — пересчёт −0.60/−4.99/−14.50/−16.78/−23.54
против текста −0.6/−5.0/−14.5/−16.8/−23.5 → ✓.

### Регрессия заголовочных чисел (не должны были сдвинуться — не сдвинулись)

| Число | Текст | Пересчёт | Вердикт |
|---|---|---|---|
| Table II медианы | −4.45/−8.87/−11.45/−14.51/−21.53 | −4.45/−8.87/−11.45/−14.51/−21.53 | ✓ |
| VW fwd_7 | −28.72% | −28.72% | ✓ |
| VW mean fwd_7 (новое, M6) | −17.40% | −17.40% | ✓ |
| Bybit H1 | −10.34%, n=415, p=5.4×10⁻¹⁴, 27.5% pos | из кэша: когорта 419 → usable 415 (пустые: CATUSDT, ZKUSDT, MONUSDT, PUMPUSDT); медиана **−10.34%**, Wilcoxon **5.39×10⁻¹⁴**, pos **27.5%** | ✓ |
| Binance survivors fwd_7 | −11.11%, shift +0.35 pp | −11.11%, +0.35 pp (n=371) | ✓ |
| Покрытие анонсов | 468/470 = 99.6%, 427 CMS/41 TG, NBT+MULTI | 468/470 = 99.57%; 427/41; недатированы ровно NBTUSDT, MULTIUSDT | ✓ |
| Премия Coinbase | +24.4% pre3 / −17.9% post7 | +24.40% (n=58) / −17.86% (n=78); заодно pre7 +25.42, pre1 +12.87 | ✓ |
| Минутный шок | +9.4% pre-3h / +3.3% post-3h, n=92 (CB 61, Bybit 31) | +9.42% / +3.29%; n=92 при фильтре ret_p3h≠NaN даёт ровно 61/31 | ✓ |
| Делистинги | −28.5% (5% pos) / −51.5% / −98.3% (1% pos) / +7.9% (76% pos); n=73 | −28.49% (5.5%) / **−51.48%** (колонка post_death_from_0, якорь = close дня анонса) / −98.25% (1.4%) / +7.88% (76.0%); event_type: delist 73, migration 25 | ✓ |
| Coinbase | 566/171; −4.49/−12.24/−22.26 | 566/171; −4.49/−12.24/−22.26 | ✓ |
| Bybit календарь | 829 USDT, 49.5% delisted; overlap 205 (44%) | 829 (из 1032 строк календаря после USDT+non-lev фильтра), 49.5%; overlap 205 | ✓ |
| Funding-пакет (M10) | 327 контрактов; медиана недели −0.36%; 17.7%; 17.0%/44.7%; треть >30д; ρ=+0.16, p=0.016, n=221 | 327; −0.363% (n=209, n_funding_w1>0); 14/79 = 17.7%; 80/470 = 17.0% (лаг≤0); 210/470 = 44.7% (лаг≤7д); 32.1% >30д; **ρ=+0.162, p=0.0159, n=221** | ✓ |

## Часть 2. Покрытие пунктов комитетного аудита

### Critical

| Пункт | Статус | Доказательство |
|---|---|---|
| **C1** сюрвайворшип | **закрыт** | III.C переписан: «the equal-weight week-one median shifts by at most ±1.5 pp and never flips sign, the dollar-weighted median shifts by at most +1.9 pp (May 2025), and the share of events that had vanished from view peaks at 23%… −28.7% against the true −30.6%». Все числа верифицированы (Часть 1). «>half vanished» и «+11.6 pp» из текста ушли (grep). Limitation 6 расширен до 175 строк. |
| **C2** панель | **закрыт** (на уровне disclosure + робастнесс; полная передатировка — решение владельца, план §6 её сознательно откладывает) | II.A: «A listing here is the debut of the USDT pair: 59 events traded earlier on Binance under another quote currency (re-pairings), and the panel knowingly includes 56 tokenized-stock and 5 stablecoin-cross pairs…; Section III.E reports the clean panel (n = 350) alongside.» III.E: «Excluding the 59 re-pairing events and the 61 non-token pairs strengthens every number: week-one median −14.32%, month-one −30.99%… dollar-weighted… −28.89% vs −28.72%». Limitation 7. Все числа верифицированы. |
| **C3** шорт n=12 | **закрыт** | III.E: «on the twelve most-traded listings with a perpetual contract available from day 0 the median week-one short earns +25.6% while the mean earns +16.0%… (per-name PnL net of funding and costs: `data/short_pnl_check.csv`)». Числа воспроизводятся (+25.62/+15.95), дефиниция заморожена именем группы `frozen_day0_perp`, артефакт закоммичен. |

### Major

| Пункт | Статус | Доказательство |
|---|---|---|
| **M1** TG-контроль | **закрыт** | III.G: «(A Telegram-timestamped subsample is uninformative here: n = 5, mostly rebrand notices.)»; ноги доказательства сохранены: «The pattern is identical on both venues, and a flat three-day run-up on the same venue rules out plain momentum selection.» |
| **M2** band H2 | **закрыт** | III.H: «A calibration note: the frozen prediction band [−15, −5] pp was taken from the specification with the volatility control… on the frozen specification the Binance estimate itself (−3.47) sits outside the band…». Обе оценки напечатаны: «−3.23 (t = −1.67)… (−3.47, t = −1.76 under the frozen controls)». |
| **M3** дата заморозки | **закрыт** | III.H + Table IV caption: «written on 2026-08-23 and frozen in version control on 2026-08-24». |
| **M4** инференс | **частично** | Сделано: bootstrap-CI для VW, BTC-adj, клина, квинтилей, градиента напечатаны и верифицированы (Часть 1); после Table II добавлено «Bootstrap confidence intervals of the medians exclude zero everywhere». Проблема n=460 снята регенерацией (post_window_car.csv: n=470, madj_7 без NaN). **Не сделано: Wilcoxon не демотирован** — абстракт по-прежнему ведёт «Wilcoxon p < 10⁻¹⁶», Table II держит колонку Wilcoxon p. |
| **M5** пермутационный тест | **закрыт** | III.A: «The headline +7d median does not clear the pool (p = 0.06). The test separates the late-horizon drift from pooled market days, but does not by itself rule out a market-wide post-peak regime.» |
| **M6** «typical dollar» | **частично** | Сделано: VW mean напечатан и верен — «The dollar-weighted mean, −17.40%, sits far above the median»; абстракт смягчён до «median-dollar outcome». **Остаток:** интро всё ещё «The typical dollar loses about 28%»; робастнесс градиента на taker_buy_quote_volume и эра-нормализация оборота не добавлены (в плане §6 были дешёвыми опциями). |
| **M7** литература | **закрыт** | [8] → Gao, Mao, Zhong, JFR 29(1) ✓; [9] → X. Yan ✓; [11] → AER 97(1):386–401 ✓. «Virtually all post-opening windows… (the sole exception, the day +3 return of +0.25%, is statistically insignificant)» ✓. Li et al. примирены явно: «They report no reversal over 5–180 day horizons; their object differs from ours in anchor and scope…». Ammann примирён в III.C (turnover-веса ≠ cap-веса, event ≠ portfolio) ✓. Добавлены [24] Félez-Viñas et al., [25] Howell et al., [26] Liu-Tsyvinski-Wu, [27] Hamrick et al. (P&D) ✓. |
| **M8** новизна | **закрыт** | «the first academic event study of first listings that is death-inclusive, turnover-weighted, and anchored at the buyer-accessible close; industry panels have documented the same fade without these design features (The Tie [16], 1,844 CEX listings; Animoca Research [28], 773 listings…)». Замечание: Messari 2026-03 из аудита не процитирован (формулировка при этом совпадает с предписанной). |
| **M9** гигиена репо | **частично** | Сделано: путей `[private-repo]` и `Path.home()` в src/ нет (grep пуст); `post_window_inference.py:142` — argsort по значению с комментарием; `data/pw_run.log` свежий (−35.46%, без −71.84%); `robustness_tables.md` funding-блок переписан (44.7%, n=209, regime break); `data/MANIFEST.md` и `build_cjsj.sh` на месте; CITATION.cff/.zenodo.json → v1.1.0 / 2026-09-19. **Остаток:** (а) `src/placebo_and_robustness.py:93` всё ещё печатает опровергнутое «funding drag… which typically exceeds the drift for most names» — при перегенерации robustness-таблиц фраза вернётся; (б) старая `paper/preprint.md:445` несёт то же предложение; (в) генератора `announcement_premium_coinbase.csv` в src/ нет (minor #13). |
| **M10** funding | **закрыт** | III.E: «the sign of funding flips by era: shorts were paid in 2021 and 2023–24, and pay in 2022 and from 2025» (2022 −0.67% подтверждено когортной таблицей funding_sweep.md); Spearman ρ=+0.16, p=0.016, n=221 верифицирован (+0.162/0.0159/221); «The frame is perpetuals-only; spot borrow availability is worse, so the access numbers are upper bounds.» Все funding-числа воспроизводятся (Часть 1). |

### Minor (§3 аудита, 15 пунктов)

| # | Пункт | Статус | Доказательство |
|---|---|---|---|
| 1 | n=73 у статистик смерти | закрыт | «For the 73 true delistings with a located announcement (98 of 99 delisted panel members are dated; migrations excluded)» |
| 2 | raw лаг-медианы | закрыт | «−10.3% to −13.4% by raw group; Kruskal-Wallis p = 0.51» |
| 3 | оба ρ | закрыт | «Spearman ρ = +0.32 for lags within a week, +0.17 across all 468 dated events» |
| 4 | n при +1215.8% | закрыт | «+1215.8% (n = 65)» |
| 5 | «no pump before the dump» (окно 14д) | **частично** | фраза в III.C осталась без квалификации окна; по данным pre_14: медиана −7.48%, 30.1% положительных (n=73) — направление держится, окно не названо |
| 6 | §D truncation-причина | закрыт | «this affects only ten recent listings, recency censoring, not the delisted names» |
| 7 | «through August 2026» | закрыт | абстракт и II.A: «January 2021 through July 2026»; «August 2026» осталось только как дата снятия индекса архива — корректно |
| 8 | 15.9× vs 13.7× | закрыт | «(median of per-event ratios; the ratio of medians is 13.7×)» — обе конвенции раскрыты |
| 9 | quote_vol_day0 единицы | закрыт | Table I: «Day-0 volume (base-asset units; label inherited from pipeline)»; MANIFEST.md документирует day0_turnover.csv |
| 10 | «25+ candidates» | закрыт | фраза удалена; III.D ссылается на `paper/STRATEGY_VALIDATION.md` |
| 11 | halves-stability конвенция | закрыт | «Mann–Whitney p = 0.27–0.33 across split conventions» |
| 12 | CC-passage (OPEN −827d) | оставлено | пассаж не изменён («the nearest surfaces 70 days after…»); аудит пометил как «невинно, но видно» — информационный пункт |
| 13 | генератор announcement_premium_coinbase.csv | **открыт** | grep по src/ пуст — артефакт невоспроизводим скриптами репо |
| 14 | «six rescue notices» | **открыт** | фраза «(plus six rescue notices outside the catalogue)» в III.G осталась; в артефактах несепарабельно (R6) — число неверифицируемо из репо |
| 15 | CITATION.cff/.zenodo.json | закрыт | v1.1.0, 2026-09-19 в обоих файлах |

### D1 (известный открытый пункт)

Editorial note в Data Availability на месте: «[Editorial note, remove before
submission: insert public GitHub URL and Zenodo DOI once the repository is
public; the release package is prepared.]» — гейтится на публикации репо
владельцем, как и заявлено.

## Найденные расхождения и остатки

Числовых расхождений нет: все 21 проверенное число комитетной волны и все
регрессионные заголовки воспроизводятся из сырых артефактов в пределах
округления. Остатки нечисловые:

1. **M4:** Wilcoxon не демотирован из абстракта/Table II (bootstrap-CI добавлены, но валидный слой не стал ведущим).
2. **M6:** интро сохраняет «The typical dollar loses about 28%» (абстракт уже смягчён); нет taker_buy-робастнесса и эра-нормализации оборота.
3. **M9:** `src/placebo_and_robustness.py:93` и `paper/preprint.md:445` несут опровергнутую фразу про funding drag; `announcement_premium_coinbase.csv` без генератора.
4. **Minor 5:** «no pump before the dump» без указания окна (14д; медиана pre_14 = −7.48%).
5. **Minor 14:** «six rescue notices» неверифицируемо из артефактов.
6. **Дефиницийная заметка (не ошибка):** делистинг −51.5% якорится на close дня анонса (post_death_from_0 = −51.48%); от pre-announcement close было бы −61.23% — формулировка «halves again from announcement» согласована с выбранным якорем.
7. **Дефиницийная заметка (не ошибка):** funding-медиана −0.36% посчитана на n=209 (n_funding_w1>0), а Spearman — на n=221 (sum_funding_w1 не-NaN); оба воспроизводятся точно, знаменатели унаследованы из funding_sweep.md.
8. **M8:** Messari 2026-03 из списка аудита не процитирован (The Tie и Animoca на месте).

## Метод

Один проход pandas/numpy/scipy без сети: survivorship/short-PnL/exclusions/
bootstrap/post_window/funding/delisting/announcement CSV пересчитаны напрямую;
Bybit H1 — независимый обход `bybit_klines_cache` (close[min(7,n−1)]/close[0]−1,
n≥2), без запуска `src/bybit_holdout.py`; взвешенные медианы — argsort по
значению, веса `day0_turnover.usd_turnover`. Покрытие пунктов аудита сверено
по тексту `cjsj_manuscript.md` и grep-проверкам репо.
