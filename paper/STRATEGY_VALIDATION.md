# Strategy validation appendix — полная таблица кандидатов (вынесено из манускрипта CJSJ)

Снято из секции III.D рукописи 2026-09-15 (ред-тим: секция читалась как
инвест-сигнал и не верифицируется читателем из этого репо). В манускрипте
остался один абзац «Application». Ничего ниже не пересчитано — числа как в
препринте v4. Движок бэктеста живёт в отдельном приватном торговом репозитории
(momentum-система по мем-секторам); здесь — только таблица вердиктов и
итоговые метрики.

**Baseline и рамка.** Ежедневная momentum-система по ликвидным
мем-секторам: long top-k по trailing return, фильтр тренда BTC, сайзинг по
обратной волатильности. Базовый Sharpe 1.30, эффективное окно 2019+ для
мемов, издержки 8 bps round-trip (вероятно занижают slippage в стресс-режимах
— Limitation 5 рукописи). Протестировано 25+ кандидатов.

**Table IV (перенесена без изменений).** Candidate refinements tested against
the fixed momentum baseline.

| Candidate change | Verdict | Evidence |
|---|---|---|
| Market-breadth gate: trade only if ≥40% of universe above SMA50 | **accepted** | Sharpe 1.30→2.06; flat plateau across thresholds 30–45%; stable in both halves |
| Stablecoin-supply growth gate (>0.5%/30d) | **accepted** | robust across 12 window/threshold combinations (Sharpe 1.40–1.50 standalone) |
| Momentum lookback 14d instead of 20d | accepted | mid-table improvement, not knife-edge |
| Fresh-listing exclusion (<21d) | accepted (defensive) | motivated by Table II of the manuscript |
| Intraday trailing stops (2–8%) | **rejected** | destroys returns (CAGR 145%→4–92%) via noise exits and missed V-rebounds |
| Time-of-day tilt (US session) | rejected | no effect on memes (+0.05% vs night +0.09%) |
| RV-percentile exposure cap | withdrawn | harmful once breadth gate active |

**Full stack** (14d lookback + breadth + stablecoin gates): Sharpe 2.53, CAGR
187%, max drawdown −52%; split-half Sharpes 2.50/2.83.

**Кавэты (как в рукописи).** Twenty-plus tested hypotheses make selection
inflation real. All strategy numbers are in-sample upper bounds until the
live tracking, which continues, confirms them.
