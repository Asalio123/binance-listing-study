"""Даты анонсов через Wayback CDX: prefix-запросы по каждому тикеру (быстро и надёжно)."""
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

D = Path.home() / "binance-listing-study" / "data"
CAL = D / "listing_events_enriched.csv"
OUT = D / "binance_announcements.csv"
HEX = re.compile(r"[0-9a-f]{32}")
BASEURL = ("http://web.archive.org/cdx/search/cdx?url=binance.com/en/support/announcement/"
           "binance-will-list-{tok}&matchType=prefix&fl=original,timestamp&collapse=urlkey&limit=20")


def query(token):
    url = BASEURL.format(tok=urllib.parse.quote(token.lower()))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        txt = urllib.request.urlopen(req, timeout=60).read().decode(errors="replace")
    except Exception:
        return None
    rows = []
    for line in txt.splitlines():
        parts = line.split(" ", 1)
        if not parts[0].isdigit() or len(parts[0]) < 8:
            continue
        u = parts[1] if len(parts) > 1 else ""
        slug = urllib.parse.unquote(u.rsplit("/", 1)[-1].lower())
        if any(s in slug for s in ("futures", "quarterly", "margin")):
            continue
        rows.append((int(parts[0][:8]), slug))
    if not rows:
        return None
    rows.sort()
    return rows[0]  # самая ранняя фиксация = дата анонса


def main():
    cal = pd.read_csv(CAL)
    tokens = sorted(set(cal["symbol"].str.replace("USDT", "", regex=False).str.lower()))
    print(f"Токенов к запросу: {len(tokens)}", flush=True)

    done_path = D / "announcements_progress.csv"
    done = {}
    if done_path.exists():
        prev = pd.read_csv(done_path)
        done = dict(zip(prev.token, prev.first_capture_date))
    todo = [t for t in tokens if t not in done]
    print(f"Уже есть: {len(done)} | осталось: {len(todo)}", flush=True)
    t0 = time.time()

    def work(tok):
        r = query(tok)
        return tok, (f"{r[0]:08d}" if r else "")

    n_new = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, (tok, datestr) in enumerate(pool.map(work, todo), 1):
            if datestr:
                done[tok] = f"{datestr[:4]}-{datestr[4:6]}-{datestr[6:]}"
                n_new += 1
            if i % 40 == 0:
                pd.DataFrame(sorted(done.items()), columns=["token", "first_capture_date"]).to_csv(done_path, index=False)
                print(f"[{i}/{len(todo)}] {time.time()-t0:.0f}с | найдено дат: {len(done)}", flush=True)
    pd.DataFrame(sorted(done.items()), columns=["token", "first_capture_date"]).to_csv(done_path, index=False)
    print(f"\nГотово: {n_new} новых дат | всего {len(done)}/{len(tokens)}")


if __name__ == "__main__":
    main()
