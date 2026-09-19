"""C3: честный пересчёт пары «median week-one short +12% / mean −21%» (III.E).

ЗАМОРОЖЕННАЯ ДЕФИНИЦЯ (2026-09-19, пункт C3 комитетного аудита):
  Выборка = top-12 событий панели по usd_turnover (data/day0_turnover.csv)
  СРЕДИ имён с USDT-M perpetual, существовавшим на day-0:
  perp_found==1 И spot_to_perp_lag_d<=0 (data/funding_sweep.csv).
  Если таких < 12 — расширяем вниз по turnover до 12 с лагом <= 3 дней
  (факт: не понадобилось, квалифицировалось 80 имён, хватило топ-12).

PnL шорта на событие (неделя 1):
  pnl = -(perp_close[day0+7d] / perp_close[day0] - 1) + sum_funding_w1 - 0.0016
  - цены перпа: GET fapi.binance.com/fapi/v1/klines?symbol=<SYM>&interval=1d
    (дневная свеча day0 = open time 00:00 UTC даты day0; индекс 7 = day0+7д);
  - sum_funding_w1 из funding_sweep.csv, конвенция проверена по кэшу
    (fundingRate > 0 -> лонги платят шортам -> ДОХОД шорту; сумма в долях);
  - 0.0016 = 16 бп round-trip fees+slippage (как ~16 бп в тексте III.E).

Аудиторская реконструкция (для полноты): top-12 по turnover БЕЗ фильтра
day-0-перпа; short PnL = -(spot fwd_7 панели), без funding/fees (так аудит
получил +32.5/+29.3 — воспроизводится дословно); дополнительно считаем
вариант с fees для сопоставимости.

Кэш: data/short_pnl_cache/<SYM>.json. Выход: data/short_pnl_check.csv.
"""
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "short_pnl_cache"
OUT = ROOT / "data" / "short_pnl_check.csv"
BASE = "https://fapi.binance.com/fapi/v1/klines"
DAY = 86400000
FEES = 0.0016  # 16 бп round-trip

CACHE.mkdir(exist_ok=True)


def fapi_klines(sym, start_ms, limit=10):
    cf = CACHE / f"{sym}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    qs = urllib.parse.urlencode({"symbol": sym, "interval": "1d",
                                 "startTime": start_ms, "limit": limit})
    url = f"{BASE}?{qs}"
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            cf.write_text(json.dumps(data))
            time.sleep(0.4)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (418, 429):
                wait = 60 * (attempt + 1)
                print(f"  {sym}: HTTP {e.code}, бэкофф {wait}с", flush=True)
                time.sleep(wait)
            else:
                time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {sym}")


def main():
    fs = pd.read_csv(ROOT / "data" / "funding_sweep.csv")
    turn = pd.read_csv(ROOT / "data" / "day0_turnover.csv")
    enr = pd.read_csv(ROOT / "data" / "listing_events_enriched.csv")

    m = (turn.merge(fs[["symbol", "perp_found", "spot_to_perp_lag_d",
                        "sum_funding_w1", "n_funding_w1"]], on="symbol", how="inner")
             .merge(enr[["symbol", "fwd_7"]], on="symbol", how="left")
             .sort_values("usd_turnover", ascending=False).reset_index(drop=True))
    assert len(m) == 470

    # --- замороженная выборка ---
    day0ok = m[(m.perp_found == 1) & (m.spot_to_perp_lag_d <= 0)]
    print(f"Имён с day-0 перпом (perp_found=1, lag<=0): {len(day0ok)}", flush=True)
    frozen = day0ok.head(12).copy()
    expanded = False
    if len(frozen) < 12:  # расширение: лаг <= 3д, вниз по turnover
        need = 12 - len(frozen)
        extra = m[(m.perp_found == 1) & (m.spot_to_perp_lag_d > 0)
                  & (m.spot_to_perp_lag_d <= 3)
                  & (~m.symbol.isin(frozen.symbol))].head(need)
        frozen = pd.concat([frozen, extra])
        expanded = True
    frozen["sample"] = "frozen_day0_perp"
    print(f"Замороженная выборка: {len(frozen)} имён"
          f"{' (расширена лагом<=3д)' if expanded else ''}", flush=True)

    # --- аудиторская выборка ---
    audit = m.head(12).copy()
    audit["sample"] = "audit_top12_no_filter"

    rows = []
    for _, r in pd.concat([frozen, audit]).iterrows():
        sym = r.symbol
        day0_ms = int(pd.Timestamp(r.day0_date, tz="UTC").timestamp() * 1000)
        row = {"sample": r["sample"], "symbol": sym, "day0_date": r.day0_date,
               "usd_turnover": r.usd_turnover,
               "spot_to_perp_lag_d": r.spot_to_perp_lag_d,
               "spot_fwd_7": r.fwd_7,
               "sum_funding_w1": r.sum_funding_w1 if pd.notna(r.sum_funding_w1) else None}

        # аудиторская метрика (воспроизводит +32.5/+29.3): -spot_fwd_7
        row["audit_pnl_spot"] = -r.fwd_7 if pd.notna(r.fwd_7) else None
        row["audit_pnl_spot_net"] = (row["audit_pnl_spot"] - FEES
                                     if row["audit_pnl_spot"] is not None else None)

        # замороженная метрика: перп-цены + funding + fees
        has_day0_perp = (r.perp_found == 1) and pd.notna(r.spot_to_perp_lag_d) \
            and r.spot_to_perp_lag_d <= 0
        if has_day0_perp:
            kl = fapi_klines(sym, day0_ms)
            if isinstance(kl, list) and len(kl) >= 8:
                c0, c7 = float(kl[0][4]), float(kl[7][4])
                row["perp_close_day0"] = c0
                row["perp_close_day7"] = c7
                row["perp_ret_w1"] = c7 / c0 - 1
                fund = r.sum_funding_w1 if pd.notna(r.sum_funding_w1) else 0.0
                row["funding_w1_used"] = fund
                row["short_pnl_net"] = -row["perp_ret_w1"] + fund - FEES
            else:
                row["short_pnl_net"] = None
                row["note"] = f"klines<8 ({len(kl) if isinstance(kl, list) else kl})"
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"Записано {OUT} ({len(out)} строк)", flush=True)

    f = out[out["sample"] == "frozen_day0_perp"]
    a = out[out["sample"] == "audit_top12_no_filter"]
    print("\n=== FROZEN (top-12 с day-0 перпом, перп-цены + funding - 16бп) ===")
    print(f[["symbol", "day0_date", "perp_ret_w1", "funding_w1_used",
             "short_pnl_net"]].to_string(index=False))
    print(f"median = {f.short_pnl_net.median()*100:+.2f}%  "
          f"mean = {f.short_pnl_net.mean()*100:+.2f}%")
    print("\n=== AUDIT reconstruction (top-12 без фильтра, -spot fwd_7) ===")
    print(f"raw:  median = {a.audit_pnl_spot.median()*100:+.2f}%  "
          f"mean = {a.audit_pnl_spot.mean()*100:+.2f}%")
    print(f"net(-16бп): median = {a.audit_pnl_spot_net.median()*100:+.2f}%  "
          f"mean = {a.audit_pnl_spot_net.mean()*100:+.2f}%")


if __name__ == "__main__":
    main()
