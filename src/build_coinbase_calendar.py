"""Death-inclusive календарь листингов Coinbase Exchange + событийная панель.

Источник: api.exchange.coinbase.com (анонимно, ~10 req/s паблик; держим ~3 req/s).
/products -> список продуктов (status: online|delisted).
/products/{id}/candles?granularity=86400&start&end -> [time, low, high, open, close, volume],
макс 300 свечей на запрос, ответ от новых к старым; история делистнутых отдаётся,
после смерти -> HTTP 200 с пустым массивом.

Пагинация назад окнами по 299 дней от сегодня до 2016-01-01: первая непустая
свеча = листинг, последняя (для delisted) = смерть. Пустое свежее окно у
делистнутого -> шагаем назад, пока не найдём данные. Два подряд пустых окна
ниже найденных данных -> стоп (защита от дыр в торговле).

Кэш: data/coinbase_candles_cache/{product_id}.json — полный слепок свечей,
скрипт возобновляемый (кэш есть -> продукт пропускается).

Выходы:
  data/coinbase_calendar.csv  (product_id, base, quote, first_date, last_date, status)
  data/coinbase_events.csv    (листинги 2021+: fwd returns +1/+3/+7/+14/+30, trunc-флаги)
  data/coinbase_overlap.csv   (пересечение с Binance-панелью по базовому активу)
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "coinbase_candles_cache"
CACHE.mkdir(exist_ok=True)

API = "https://api.exchange.coinbase.com"
GENESIS = pd.Timestamp("2016-01-01", tz="UTC")
TODAY = pd.Timestamp.now("UTC").normalize()
WIN = pd.Timedelta(days=299)          # < 300 свечей на запрос
SLEEP = 0.32                          # ~3 req/s
HORIZONS = (1, 3, 7, 14, 30)


def get(url, retries=5):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 * (i + 1))
                continue
            raise
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"retries exhausted: {url}")


def candles(pid, start, end):
    q = f"granularity=86400&start={start.isoformat()}&end={end.isoformat()}"
    d = get(f"{API}/products/{pid}/candles?{q}")
    if isinstance(d, dict):            # сообщение об ошибке телом
        raise RuntimeError(f"{pid}: {d}")
    return d


def fetch_history(pid):
    """Все дневные свечи продукта, пагинация назад от сегодня.

    end у API инклюзивен: граничная свеча возвращается повторно, поэтому
    сдвигаем end только при наличии СТРОГО более старых свечей, иначе прыгаем
    на start. Три подряд окна без новых данных ниже найденных -> стоп
    (терпим дыры в торговле до ~900 дней).
    """
    out = []
    end = TODAY
    found = False                      # нашли хоть одну свечу
    stale = 0                          # окна без строго более старых данных
    while end > GENESIS:
        start = max(end - WIN, GENESIS)
        rows = candles(pid, start, end)
        end_unix = int(end.timestamp())
        older = [r for r in rows if r[0] < end_unix]
        if older:
            found = True
            stale = 0
            out.extend(rows)
            end = pd.Timestamp(min(r[0] for r in older), unit="s", tz="UTC")
        else:
            stale += 1
            if found and stale >= 3:
                break
            end = start
        time.sleep(SLEEP)
    uniq = {r[0]: r for r in out}      # границы окон дублируют свечи
    return [uniq[k] for k in sorted(uniq)]


def main():
    products = get(f"{API}/products")
    prods = [p for p in products if p["quote_currency"] in ("USD", "USDT")]
    print(f"Продуктов всего: {len(products)} | USD/USDT: {len(prods)}", flush=True)

    # --- 1. сбор свечей с кэшем ---
    done = 0
    for p in prods:
        pid = p["id"]
        f = CACHE / f"{pid}.json"
        if not f.exists():
            rows = fetch_history(pid)
            f.write_text(json.dumps(rows))
            time.sleep(SLEEP)
        done += 1
        if done % 50 == 0:
            print(f"...{done}/{len(prods)}", flush=True)

    # --- 2. календарь ---
    recs = {}
    for p in prods:
        pid = p["id"]
        rows = json.loads((CACHE / f"{pid}.json").read_text())
        if not rows:
            recs[pid] = dict(product_id=pid, base=p["base_currency"],
                             quote=p["quote_currency"], first_date=None,
                             last_date=None, status=p["status"])
            continue
        ts = [r[0] for r in rows]
        recs[pid] = dict(product_id=pid, base=p["base_currency"],
                         quote=p["quote_currency"],
                         first_date=pd.Timestamp(min(ts), unit="s", tz="UTC").strftime("%Y-%m-%d"),
                         last_date=pd.Timestamp(max(ts), unit="s", tz="UTC").strftime("%Y-%m-%d"),
                         status=p["status"])
    cal = pd.DataFrame(recs.values()).sort_values("first_date", na_position="last")
    cal.to_csv(DATA / "coinbase_calendar.csv", index=False)
    n_dl = int((cal.status == "delisted").sum())
    print(f"Календарь: {len(cal)} продуктов, delisted={n_dl}, "
          f"без свечей={int(cal.first_date.isna().sum())}", flush=True)

    # --- 3. событийная панель (листинги 2021+) ---
    events = []
    for p in prods:
        pid = p["id"]
        c = recs[pid]
        if c["first_date"] is None or c["first_date"] < "2021-01-01":
            continue
        rows = json.loads((CACHE / f"{pid}.json").read_text())
        closes = [r[4] for r in rows]
        c0 = closes[0]
        if not c0 or c0 <= 0:
            continue
        ev = dict(product_id=pid, base=c["base"], quote=c["quote"],
                  day0_date=c["first_date"],
                  delisted=int(c["status"] == "delisted"))
        for h in HORIZONS:
            if len(closes) > h:
                ev[f"fwd_{h}"] = closes[h] / c0 - 1
                ev[f"trunc_{h}"] = 0
            else:
                ev[f"fwd_{h}"] = closes[-1] / c0 - 1
                ev[f"trunc_{h}"] = 1
        events.append(ev)
    ev = pd.DataFrame(events).sort_values("day0_date")
    ev.to_csv(DATA / "coinbase_events.csv", index=False)
    print(f"Событий 2021+: {len(ev)} | delisted={int(ev.delisted.sum())} | "
          f"trunc_30={int(ev.trunc_30.sum())}", flush=True)

    # --- 4. пересечение с Binance-панелью ---
    bn = pd.read_csv(DATA / "listing_events_enriched.csv")
    bn["base"] = bn.symbol.str.replace("USDT$", "", regex=True)
    # точная дата листинга Binance = минимальный таймстамп в binance_day_closes
    bn_dates = {}
    ddir = DATA / "binance_day_closes"
    for sym in bn.symbol:
        files = sorted(ddir.glob(f"{sym}-*.json"))
        t0 = None
        for f in files:
            d = json.loads(f.read_text())
            if d:
                t = min(int(k) for k in d)
                t0 = t if t0 is None else min(t0, t)
        if t0 is not None:
            bn_dates[sym] = pd.Timestamp(t0, tz="UTC").strftime("%Y-%m-%d")
    bn["binance_day0"] = bn.symbol.map(bn_dates)
    print(f"Binance-панель: {len(bn)} | с точной датой: {int(bn.binance_day0.notna().sum())}",
          flush=True)

    cb_first = (cal.dropna(subset=["first_date"])
                  .sort_values("first_date")
                  .groupby("base").first())          # самый ранний продукт на базу
    rows = []
    for _, r in bn.iterrows():
        b = r["base"]
        if b not in cb_first.index:
            continue
        cb = cb_first.loc[b]
        lag = None
        if r["binance_day0"] is not None and not pd.isna(r["binance_day0"]):
            lag = (pd.Timestamp(r["binance_day0"]) - pd.Timestamp(cb["first_date"])).days
        rows.append(dict(symbol=r.symbol, base=b, cb_product=cb["product_id"],
                         cb_first_date=cb["first_date"], binance_day0=r["binance_day0"],
                         lag_days=lag, cb_delisted=int(cb["status"] == "delisted")))
    ov = pd.DataFrame(rows).sort_values("lag_days")
    ov.to_csv(DATA / "coinbase_overlap.csv", index=False)
    n_pre = int((ov.lag_days > 0).sum())
    n_same = int((ov.lag_days == 0).sum())
    print(f"Пересечений по базе: {len(ov)} | Coinbase раньше: {n_pre} "
          f"(медиана лага {ov.lag_days.median():.0f} дн) | тот же день: {n_same}", flush=True)


if __name__ == "__main__":
    main()
