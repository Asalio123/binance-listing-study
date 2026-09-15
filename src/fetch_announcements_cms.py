"""Сбор detail-записей CMS Binance (catalog 48 «New Cryptocurrency Listing»).

Источник: GET /bapi/composite/v1/public/cms/article/detail/query?articleCode=<code>
Ответ: publishDate (unix ms, UTC) + body (JSON-дерево нод).

Особенности:
- кэш каждого ответа в data/cms_details_cache/<code>.json — сбор возобновляем;
- приоритет кандидатам из матчинга заголовков (Will List / Lists / HODLer /
  Launchpool / Megadrop / Adds Trading Pairs / bStock / тикер панели в заголовке);
- пауза 1.2 с между запросами, на HTTP 429 — экспоненциальный бэкофф 60/120/240 с.
"""
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path.home() / "binance-listing-study"
CAT = ROOT / "data" / "cms_catalog48_titles_scout.json"
PANEL = ROOT / "data" / "listing_events_enriched.csv"
CACHE = ROOT / "data" / "cms_details_cache"
URL = ("https://www.binance.com/bapi/composite/v1/public/cms/"
       "article/detail/query?articleCode={code}")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
PAUSE = 1.2
BACKOFF = [60, 120, 240, 480, 480]

LISTING_TITLE = re.compile(
    r"will list|binance lists|hodler airdrop|launchpool|megadrop|"
    r"adds?\b.*trading pair|bstock|will add\b.*(?:usdt|pair)", re.I)


def is_candidate(title: str, bases: list[str]) -> bool:
    if LISTING_TITLE.search(title):
        return True
    for b in bases:  # тикер панели в скобках в заголовке
        if f"({b})" in title:
            return True
    return False


def fetch(code: str) -> dict:
    req = urllib.request.Request(URL.format(code=code), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    CACHE.mkdir(exist_ok=True)
    catalog = json.load(CAT.open())
    bases = [s.replace("USDT", "") for s in
             pd.read_csv(PANEL).symbol.unique() if len(s.replace("USDT", "")) > 2]

    cand, rest = [], []
    for title, code in catalog:
        (cand if is_candidate(title, bases) else rest).append((title, code))
    queue = cand + rest
    todo = [(t, c) for t, c in queue if not (CACHE / f"{c}.json").exists()]
    print(f"каталог: {len(catalog)} | кандидаты: {len(cand)} | "
          f"уже в кэше: {len(queue) - len(todo)} | к загрузке: {len(todo)}", flush=True)

    t0 = time.time()
    done = 0
    for title, code in todo:
        path = CACHE / f"{code}.json"
        got = None
        for attempt in range(len(BACKOFF) + 1):
            try:
                got = fetch(code)
                if not isinstance(got.get("data"), dict) or \
                        got["data"].get("publishDate") is None:
                    raise ValueError(f"bad payload: {str(got)[:120]}")
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                    print(f"429 rate-limit, сплю {wait}с "
                          f"({done}/{len(todo)})", flush=True)
                    time.sleep(wait)
                else:
                    print(f"HTTP {e.code} code={code}, retry {attempt}", flush=True)
                    time.sleep(5 * (attempt + 1))
            except Exception as e:
                print(f"FAIL {code}: {e}, retry {attempt}", flush=True)
                time.sleep(5 * (attempt + 1))
        if got is None:
            print(f"SKIP {code} после всех ретраев: {title[:60]}", flush=True)
            continue
        path.write_text(json.dumps(got))
        done += 1
        if done % 25 == 0:
            dt = time.time() - t0
            eta = dt / done * (len(todo) - done) / 60
            print(f"{done}/{len(todo)} | {dt/60:.1f} мин | ETA {eta:.1f} мин",
                  flush=True)
        time.sleep(PAUSE)
    print(f"готово: {done} новых, кэш всего {len(list(CACHE.glob('*.json')))}",
          flush=True)


if __name__ == "__main__":
    main()
