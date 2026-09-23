"""Генератор data/announcement_premium_coinbase.csv (аудит 2026-09-19, minor #13:
артефакт был сиротой без воспроизводящего скрипта).

Для каждого события панели с известным таймстампом анонса Binance
(data/announcement_dates.csv) меряет доходность токена НА COINBASE вокруг даты
анонса: премия, набегающая до того, как ритейл Binance вообще может купить.

Дефиниции (календарные окна, как в тексте рукописи):
  D      = UTC-дата таймстампа анонса (announce_ts_utc)
  pre_k  = close(D) / close(D-k) - 1,   k in (7, 3, 1)
  post7  = close(D+7) / close(D) - 1
  close  = дневное закрытие Coinbase {base}-USD из data/coinbase_candles_cache/
           (формат свечи: [time, low, high, open, close, volume], time = полночь UTC)
Окно NaN, если какой-то из двух дат нет в кэше (токен ещё/уже не торговался).
Строка сохраняется, если хотя бы одно окно не-NaN. Порядок строк = порядок
панели listing_events_enriched.csv.

Отличие от v1-артефакта (2026-09-15): одна ячейка, POWRUSDT post7. В кэше
POWR-USD дыра 2021-11-20..22; v1 индексировал свечи ПОЗИЦИОННО и брал
7-ю доступную свечу (2021-11-27, close 0.6559 -> -8.07%) вместо календарной
даты D+7 (2021-11-24, close 0.7658 -> +7.33%). Регенерация несёт календарное
значение; остальные 315 ячеек совпадают с v1 бит-в-бит, все публикуемые
медианы и p-значения инвариантны (post7 median -17.86% при n=78).

Запуск офлайн (все входы закоммичены): python3 src/build_announcement_premium.py
"""
import json
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "coinbase_candles_cache"

OUT = DATA / "announcement_premium_coinbase.csv"


def load_closes(base: str) -> dict | None:
    f = CACHE / f"{base}-USD.json"
    if not f.exists():
        return None
    candles = json.loads(f.read_text())
    return {datetime.fromtimestamp(c[0], UTC).date(): c[4] for c in candles}


def main() -> None:
    ann = pd.read_csv(DATA / "announcement_dates.csv")
    ann = ann.set_index("symbol")["announce_ts_utc"].to_dict()
    panel = pd.read_csv(DATA / "listing_events_enriched.csv")["symbol"]

    rows = []
    for symbol in panel:
        ts = ann.get(symbol)
        if ts is None:
            continue
        closes = load_closes(symbol[:-4])  # strip USDT
        if closes is None:
            continue
        D = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        row = {"symbol": symbol}
        for k in (7, 3, 1):
            d0 = D - timedelta(days=k)
            row[f"pre{k}"] = closes[D] / closes[d0] - 1 if d0 in closes and D in closes else None
        d7 = D + timedelta(days=7)
        row["post7"] = closes[d7] / closes[D] - 1 if d7 in closes and D in closes else None
        if any(v is not None for k, v in row.items() if k != "symbol"):
            rows.append(row)

    out = pd.DataFrame(rows, columns=["symbol", "pre7", "pre3", "pre1", "post7"])
    out.to_csv(OUT, index=False)

    n = out.notna().sum()
    med = out[["pre7", "pre3", "pre1", "post7"]].median() * 100
    print(f"rows: {len(out)}; non-null: pre7={n['pre7']} pre3={n['pre3']} "
          f"pre1={n['pre1']} post7={n['post7']}")
    print(f"medians %: pre7={med['pre7']:.2f} pre3={med['pre3']:.2f} "
          f"pre1={med['pre1']:.2f} post7={med['post7']:.2f}")


if __name__ == "__main__":
    main()
