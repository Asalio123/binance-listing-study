"""Common Crawl коллектор дат анонсов Binance (независимо от Internet Archive).

Для каждой коллекции CC-MAIN-* >= 2019: CDX-совместимый запрос с фильтром
will-list; слаг -> тикер-кандидат; earliest timestamp per token.
Resume по коллекциям через data/cc_state.json.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

D = Path.home() / "binance-listing-study" / "data"
STATE = D / "cc_state.json"
RAW = D / "cc_raw.jsonl"
OUT = D / "cc_dates.csv"
HEX = re.compile(r"[0-9a-f]{32}")
SKIP = ("futures", "quarterly", "margin", "contracts")
IDX = "https://index.commoncrawl.org/{cid}-index?url=binance.com%2Fen%2Fsupport%2Fannouncement%2F*&output=json&filter=url:.*will-list.*&collapse=urlkey"


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode(errors="replace")


def slug_token(url_):
    slug = urllib.parse.unquote(url_.rsplit("/", 1)[-1].lower())
    if any(s in slug for s in SKIP) or "will-list" not in slug:
        return None
    core = HEX.sub("", slug).strip("-")
    m = re.search(r"will-list-(.+)", core)
    if not m:
        return None
    toks = m.group(1).strip("-").split("-")
    tok = toks[-1] if toks else ""
    return tok.upper() if len(tok) >= 2 else None


def main():
    import urllib.error

    state = json.loads(STATE.read_text()) if STATE.exists() else {"done": [], "failed": []}
    done = set(state["done"])
    # coll-info.json мёртв на новом кластере -> генерируем кандидатов по паттерну
    weeks = [2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50]
    colls = [f"CC-MAIN-{y}-{w:02d}" for y in range(2019, 2027) for w in weeks]
    colls = [c for c in colls if c not in done]
    print(f"Кандидатов коллекций: {len(colls)}", flush=True)

    raw_f = open(RAW, "a")
    best = {}
    t0 = time.time()
    for cid in colls:
        rows_n = 0
        ok = False
        for attempt in range(3):
            try:
                try:
                    txt = get(IDX.format(cid=cid))
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        ok = True  # коллекции с таким id не существует
                        break
                    raise
                if txt.lstrip().startswith("<"):
                    raise ValueError("index server html error")
                for line in txt.splitlines():
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if str(rec.get("status")) != "200":
                        continue
                    tok = slug_token(rec["url"])
                    if not tok:
                        continue
                    ts = rec.get("timestamp", "")
                    if len(ts) < 8 or not ts[:8].isdigit():
                        continue
                    rows_n += 1
                    raw_f.write(json.dumps({"coll": cid, "url": rec["url"], "ts": rec["timestamp"]}) + "\n")
                    d = pd.Timestamp(ts[:8])
                    if tok not in best or d < best[tok][0]:
                        best[tok] = (d, cid)
                ok = True
                break
            except Exception as e:
                wait = 10 * (attempt + 1)
                print(f"{cid}: попытка {attempt+1} FAIL {e}, ждём {wait}с", flush=True)
                time.sleep(wait)
        if ok:
            done.add(cid)
            state["done"] = sorted(done)
            STATE.write_text(json.dumps(state))
            print(f"{cid}: {rows_n} строк | уникальных токенов: {len(best)} | {time.time()-t0:.0f}с", flush=True)
        else:
            state["failed"].append(cid)
            STATE.write_text(json.dumps(state))
            print(f"{cid}: FAILED, помечена для ретрая", flush=True)
        time.sleep(1)
    raw_f.close()

    rows_out = [(k, v[0].date().isoformat(), v[1]) for k, v in sorted(best.items())]
    pd.DataFrame(rows_out, columns=["token", "first_seen_date", "collection"]).to_csv(OUT, index=False)
    print(f"\nГотово: {len(rows_out)} токенов с датами -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
