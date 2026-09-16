"""Полный funding-свип панели (заменяет проверку n=12 полной выборкой).

Для каждого из 470 имён панели проверяем наличие USDT-M perpetual на Binance
и собираем funding-события за окна [day0, day0+7д] и [day0, day0+30д].

Маршрут: GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=<SYM>&
startTime=...&endTime=...&limit=500 (фактический потолок 500 записей/запрос,
limit>1000 = ошибка; пагинация по startTime). Анонимно. После ~120-150
быстрых запросов бывает 429 -> пауза + бэкофф 60с.

Два запроса на символ:
  A) inception: startTime=2019-09-01, limit=1 -> первая funding-запись =
     прокси основания перпа -> spot_to_perp_lag_d (отрицательный = перп
     старше спота). Пустой ответ -> perp_found=0 (кейс MIRUSDT, логируем).
  B) окно [day0, day0+30д], limit=500, пагинация если ровно 500.
Каденс funding менялся (8ч до ~2023, 4ч после 2025-05) - не предполагаем,
считаем медианный интервал по факту записей окна.

Знак шорта: fundingRate>0 -> лонги платят шортам -> шорт ПОЛУЧАЕТ.
sum_funding_* > 0 = доход шорту, < 0 = издержка шорта.

Кэш: data/funding_cache/<SYM>.json (сырые ответы, перезапуск бесплатен).
Выход: data/funding_sweep.csv
"""
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.home() / "binance-listing-study"
CACHE = ROOT / "data" / "funding_cache"
OUT = ROOT / "data" / "funding_sweep.csv"
BASE = "https://fapi.binance.com/fapi/v1/fundingRate"
GENESIS_MS = 1567296000000  # 2019-09-01, запуск Binance Futures
DAY = 86400000
SLEEP = 0.4

CACHE.mkdir(exist_ok=True)


def fapi_get(params):
    """Один GET с бэкоффом на 429/418. None после 6 неудач."""
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}?{qs}"
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (418, 429):
                wait = 60 * (attempt + 1) if attempt < 3 else 90
                print(f"  HTTP {e.code}, бэкофф {wait}с", flush=True)
                time.sleep(wait)
            elif e.code == 400:
                return {"error": str(e)}
            else:
                time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def fetch_symbol(sym, day0_ms):
    """Сырые данные символа: inception-запись + события окна. Кэшируется."""
    cf = CACHE / f"{sym}.json"
    if cf.exists():
        return json.loads(cf.read_text())

    inception = fapi_get({"symbol": sym, "startTime": GENESIS_MS, "limit": 1})
    time.sleep(SLEEP)
    if inception is None:
        return {"symbol": sym, "inception": None, "window": None}  # транзиент - не кэшируем

    window, start = [], day0_ms
    while True:
        batch = fapi_get({"symbol": sym, "startTime": start,
                          "endTime": day0_ms + 30 * DAY, "limit": 500})
        if not isinstance(batch, list) or not batch:
            break
        window.extend(batch)
        if len(batch) < 500:
            break
        start = batch[-1]["fundingTime"] + 1
        time.sleep(SLEEP)
    time.sleep(SLEEP)

    data = {"symbol": sym, "inception": inception, "window": window}
    cf.write_text(json.dumps(data))
    return data


def summarize(sym, day0_ms, data):
    row = {"symbol": sym, "perp_found": 0, "first_funding_ts": None,
           "spot_to_perp_lag_d": np.nan, "n_funding_w1": 0, "sum_funding_w1": np.nan,
           "n_funding_m1": 0, "sum_funding_m1": np.nan, "med_interval_h": np.nan,
           "coverage_w1": np.nan, "coverage_m1": np.nan, "note": ""}
    inc = data.get("inception")
    if inc is None:
        row["note"] = "fetch_failed"
        return row
    if isinstance(inc, dict):
        row["note"] = f"api_error: {inc.get('error', '')[:60]}"
        return row
    if not inc:
        row["note"] = "empty_history"  # кейс MIRUSDT
        return row

    first_ts = int(inc[0]["fundingTime"])
    row["perp_found"] = 1
    row["first_funding_ts"] = pd.to_datetime(first_ts, unit="ms", utc=True).isoformat()
    row["spot_to_perp_lag_d"] = (first_ts - day0_ms) / DAY

    ev = data.get("window") or []
    if not ev:
        row["note"] = "perp_exists_no_window_events"
        return row
    ts = np.array([int(e["fundingTime"]) for e in ev])
    rate = np.array([float(e["fundingRate"]) for e in ev])

    w1 = ts < day0_ms + 7 * DAY
    row["n_funding_w1"] = int(w1.sum())
    row["sum_funding_w1"] = float(rate[w1].sum())
    row["n_funding_m1"] = int(len(ts))
    row["sum_funding_m1"] = float(rate.sum())

    if len(ts) > 1:
        row["med_interval_h"] = float(np.median(np.diff(ts)) / 3600000)
        # покрытие: n * медианный интервал / длина окна, кап на 1
        row["coverage_w1"] = min(1.0, row["n_funding_w1"] * row["med_interval_h"] / (7 * 24))
        row["coverage_m1"] = min(1.0, len(ts) * row["med_interval_h"] / (30 * 24))
    return row


def main():
    enr = pd.read_csv(ROOT / "data" / "listing_events_enriched.csv")
    turn = pd.read_csv(ROOT / "data" / "day0_turnover.csv")
    df = enr.merge(turn[["symbol", "day0_date"]], on="symbol", how="left")
    # юнит-безопасно: pandas 3 может дать datetime64[s], // Timedelta надёжно
    df["day0_ms"] = ((pd.to_datetime(df.day0_date, utc=True)
                      - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1))
    print(f"Символов: {len(df)}", flush=True)

    rows, t0 = [], time.time()
    for i, r in enumerate(df.itertuples(), 1):
        data = fetch_symbol(r.symbol, r.day0_ms)
        rows.append(summarize(r.symbol, r.day0_ms, data))
        if i % 25 == 0:
            el = time.time() - t0
            print(f"...{i}/{len(df)} ({el:.0f}с, eta {el/i*(len(df)-i):.0f}с)", flush=True)

    out = pd.DataFrame(rows)
    out.insert(1, "day0_date", df.day0_date.values)
    out.to_csv(OUT, index=False)
    print(f"Записано {OUT} ({len(out)} строк)", flush=True)

    found = out[out.perp_found == 1]
    print(f"\nperp_found: {len(found)}/{len(out)}", flush=True)
    print("Пустая история:", out[out.note == "empty_history"].symbol.tolist(), flush=True)
    print("Ошибки fetch:", out[out.note == "fetch_failed"].symbol.tolist(), flush=True)
    lag = found.spot_to_perp_lag_d.dropna()
    print(f"Лаг спот->перп (дни): медиана {lag.median():.1f}, "
          f"доля перп-раньше-спота {(lag < 0).mean():.3f}, доля |лаг|<=1д {(lag.abs() <= 1).mean():.3f}", flush=True)


if __name__ == "__main__":
    main()
