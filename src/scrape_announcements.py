"""Реконструкция дат анонсов листингов Binance через Wayback CDX (по полугодиям, с ретраями)."""
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path.home() / "binance-listing-study" / "data" / "binance_announcements.csv"
RAW = Path.home() / "binance-listing-study" / "data" / "wayback_cdx_raw.txt"
BASEURL = ("http://web.archive.org/cdx/search/cdx?url=binance.com/en/support/announcement/*"
           "&fl=original,timestamp&collapse=urlkey&filter=statuscode:200"
           "&filter=original:.*will-list.*&from={y1}&to={y2}")
HEX = re.compile(r"[0-9a-f]{32}")
SKIP = ("futures", "quarterly", "contracts", "margin")
WINDOWS = [(f"{y}-{h:02d}", f"{y}-{h2:02d}") for y in range(2017, 2027) for h, h2 in [(1, 6), (7, 12)]]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=300).read().decode(errors="replace")


def main():
    t0 = time.time()
    raw_all = []
    for w_start, w_end in WINDOWS:
        url = BASEURL.format(y1=w_start, y2=w_end)
        got = None
        for attempt in range(3):
            try:
                got = fetch(url)
                print(f"{w_start}: {len(got.splitlines())} строк ({time.time()-t0:.0f}с)", flush=True)
                break
            except Exception as e:
                print(f"{w_start}: попытка {attempt+1} FAIL {e}", flush=True)
                time.sleep(8 * (attempt + 1))
        if got:
            raw_all.append(got)
        time.sleep(1)
    RAW.write_text("\n".join(raw_all))

    best = {}
    n_all = n_spot = 0
    for line in RAW.open():
        parts = line.strip().split(" ", 1)
        if len(parts) != 2:
            continue
        url_, ts = parts
        n_all += 1
        slug = urllib.parse.unquote(url_.rsplit("/", 1)[-1].lower())
        if any(s in slug for s in SKIP) or "will-list" not in slug:
            continue
        core = HEX.sub("", slug).strip("-")
        m = re.search(r"will-list-(.+)", core)
        if not m:
            continue
        tokens = m.group(1).strip("-").split("-")
        token = tokens[-1] if tokens else ""
        if len(token) < 2 or not ts.isdigit() or len(ts) < 8:
            continue
        n_spot += 1
        d = pd.Timestamp(ts[:8])
        key = token.upper()
        if key not in best or d < best[key][0]:
            best[key] = (d, url_)

    rows = [(k, v[0].date().isoformat(), v[1]) for k, v in sorted(best.items())]
    pd.DataFrame(rows, columns=["token", "first_capture_date", "url"]).to_csv(OUT, index=False)
    print(f"\nCDX строк: {n_all} | спот-подходящих: {n_spot} | уникальных токенов: {len(rows)}")


if __name__ == "__main__":
    main()
