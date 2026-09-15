"""Догрузка «Notice of Addition / New Trading Pairs»-статей (Notices-каталог,
вне catalog48) по ссылкам из TG-дампа. Кэш общий с fetch_announcements_cms.py.
"""
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path.home() / "binance-listing-study"
TG = ROOT / "data" / "tg_announcements_scrape.json"
CACHE = ROOT / "data" / "cms_details_cache"
URL = ("https://www.binance.com/bapi/composite/v1/public/cms/"
       "article/detail/query?articleCode={code}")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
RE_NOTICE = re.compile(
    r"notice of (addition|new).{0,40}trading pairs?|"
    r"notice on new trading pairs|new trading pairs on binance spot", re.I)
RE_CODE = re.compile(r"announcement/(?:detail/)?([0-9a-f]{32})")
PAUSE = 1.3


def main():
    CACHE.mkdir(exist_ok=True)
    msgs = json.load(TG.open())
    codes = {}
    for m in msgs:
        if not RE_NOTICE.search(m["text"].split("\n", 1)[0]):
            continue
        for h in m["hrefs"] + [m["text"]]:
            for c in RE_CODE.findall(h):
                codes.setdefault(c, m["datetime"])
    todo = [c for c in codes if not (CACHE / f"{c}.json").exists()]
    print(f"notice-статей: {len(codes)} | к загрузке: {len(todo)}", flush=True)

    t0 = time.time()
    for i, code in enumerate(todo, 1):
        got = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(URL.format(code=code),
                                             headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    got = json.loads(r.read().decode())
                if not isinstance(got.get("data"), dict) or \
                        got["data"].get("publishDate") is None:
                    raise ValueError("bad payload")
                break
            except urllib.error.HTTPError as e:
                wait = [60, 120, 240, 240][attempt] if e.code == 429 \
                    else 5 * (attempt + 1)
                print(f"HTTP {e.code} {code}, сплю {wait}с", flush=True)
                time.sleep(wait)
            except Exception as e:
                print(f"FAIL {code}: {e}, retry {attempt}", flush=True)
                time.sleep(5 * (attempt + 1))
        if got is not None:
            (CACHE / f"{code}.json").write_text(json.dumps(got))
        if i % 20 == 0:
            print(f"{i}/{len(todo)} | {time.time()-t0:.0f}с", flush=True)
        time.sleep(PAUSE)
    print("готово", flush=True)


if __name__ == "__main__":
    main()
