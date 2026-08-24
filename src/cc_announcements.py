"""Даты анонсов листингов Binance из индексов Common Crawl (коллекции 2019+, resume-state, пагинация)."""
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path.home() / "binance-listing-study"
OUT = ROOT / "data" / "cc_dates.csv"
RAWL = ROOT / "data" / "cc_raw.jsonl"
STATE = ROOT / "data" / "cc_state.json"
COLLINFO = "https://index.commoncrawl.org/collinfo.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
HEX = re.compile(r"[0-9a-f]{32}")
SKIP = ("futures", "quarterly", "contracts", "margin")
MIN_YEAR = 2019
MAX_PAGES = 1000


def log(msg):
    print(f"{time.strftime('%m-%d %H:%M:%S')} {msg}", flush=True)


MIN_GAP = 9.0          # пейсинг ~7 req/min: серией быстрых запросов сервер
_last_req = [0.0]      # троттлит мусорными 400/502 (наблюдение 2026-08-24)
THROTTLE_CODES = {400, 403, 429, 500, 502, 503, 504}


def _pace():
    delta = time.time() - _last_req[0]
    if delta < MIN_GAP:
        time.sleep(MIN_GAP - delta)
    _last_req[0] = time.time()


def fetch_page(url, tries=8):
    """Тело ответа; '' при 404 (сервер так отвечает на нулевую выдачу и отсутствующий индекс).

    Троттлинг-коды лечим НЕ частыми ретраями (они держат лимит активным),
    а длинными эскалирующими паузами.
    """
    last = None
    for attempt in range(tries):
        _pace()
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=300).read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            last = e
            if e.code in THROTTLE_CODES:
                wait = min(300 * 2 ** min(attempt, 3), 2400) + random.uniform(0, 60)
                log(f"    троттлинг (HTTP {e.code}), пауза {wait:.0f}с")
            else:
                wait = 60 + random.uniform(0, 30)
                log(f"    ретрай {attempt + 1}/{tries} через {wait:.0f}с: HTTP {e.code}")
            time.sleep(wait)
        except Exception as e:
            last = e
            wait = 60 + random.uniform(0, 30)
            log(f"    ретрай {attempt + 1}/{tries} через {wait:.0f}с: {str(e)[:120]}")
            time.sleep(wait)
    raise RuntimeError(f"исчерпаны ретраи: {last}")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"done": [], "failed": []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))


def collections():
    d = json.loads(fetch_page(COLLINFO))
    out = []
    for x in d:
        m = re.fullmatch(r"CC-MAIN-(\d{4})-\d{2}", x.get("id", ""))
        if m and int(m.group(1)) >= MIN_YEAR:
            out.append(x["id"])
    return sorted(out)


def token_from(url_):
    slug = urllib.parse.unquote(url_.rsplit("/", 1)[-1].lower())
    if "will-list" not in slug or any(s in slug for s in SKIP):
        return None
    core = HEX.sub("", slug).strip("-")
    m = re.search(r"will-list-(.+)", core)
    if not m:
        return None
    tokens = [t for t in m.group(1).strip("-").split("-") if t]
    token = tokens[-1] if tokens else ""
    return token.upper() if len(token) >= 2 else None


def query_coll(cid):
    """Записи (url, timestamp) одной коллекции; пустой результат — норма, не ошибка.

    Серверные regex-фильтры на новом index.commoncrawl.org сломаны
    (точный match работает, .* — нет), поэтому фильтруем клиентски.
    404 на префиксный запрос = нулевая выдача; чтобы не спутать её
    с отсутствующим индексом коллекции, при пустой нулевой странице
    делаем контрольный проб корневого домена.
    """
    recs = []
    for page in range(MAX_PAGES):
        q = urllib.parse.urlencode({
            "url": "binance.com/en/support/announcement/*",
            "output": "json",
            "collapse": "urlkey",
            "page": page,
        })
        body = fetch_page(f"https://index.commoncrawl.org/{cid}-index?{q}")
        if body == "":
            if page == 0:
                probe = fetch_page(
                    f"https://index.commoncrawl.org/{cid}-index?"
                    + urllib.parse.urlencode({"url": "wikipedia.org/", "output": "json"}))
                if probe == "":
                    raise RuntimeError("ENDPOINT_404: индекс коллекции недоступен")
            return recs
        stripped = body.lstrip()
        if stripped.startswith("<"):
            raise RuntimeError("HTML вместо JSON-выдачи")
        if stripped.startswith("{"):
            try:
                msg = json.loads(body).get("message", "")
            except ValueError:
                msg = ""
            if msg and ("invalid" in msg.lower() or "no more" in msg.lower()):
                return recs
        n_new = 0
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if "url" in r and "timestamp" in r:
                recs.append((r["url"], str(r["timestamp"])))
                n_new += 1
        if n_new == 0:
            return recs
        time.sleep(2)
    log(f"    {cid}: достигнут MAX_PAGES, возможна усечённая выдача")
    return recs


def rebuild():
    if not RAWL.exists():
        log("raw пуст — CSV не строю")
        return
    best = {}
    for line in RAWL.open():
        r = json.loads(line)
        key, d, coll = r["token"], r["ts"], r["coll"]
        if key not in best or d < best[key][0]:
            best[key] = (d, coll)
    rows = [
        (k, f"{v[0][:4]}-{v[0][4:6]}-{v[0][6:8]}", v[1])
        for k, v in sorted(best.items())
    ]
    pd.DataFrame(rows, columns=["token", "first_seen_date", "source_coll"]).to_csv(OUT, index=False)
    log(f"итог: {len(rows)} уникальных токенов -> {OUT}")


def run_coll(cid, st):
    """Прогон одной коллекции; True если успех."""
    recs = query_coll(cid)
    n_tok = 0
    with RAWL.open("a") as f:
        for url_, ts in recs:
            tok = token_from(url_)
            if tok and ts.isdigit() and len(ts) >= 8:
                f.write(json.dumps({"token": tok, "ts": ts[:8], "coll": cid},
                                   ensure_ascii=False) + "\n")
                n_tok += 1
    st["done"].append(cid)
    log(f"  {cid}: строк={len(recs)}, токенов={n_tok}")
    return True


def main():
    t0 = time.time()
    st = load_state()
    done = set(st["done"])
    todo = [c for c in collections() if c not in done]
    log(f"к обработке: {len(todo)} коллекций (>= {MIN_YEAR}); уже done: {len(done)}, failed: {len(st['failed'])})")
    failures = []
    for i, cid in enumerate(todo):
        try:
            run_coll(cid, st)
        except Exception as e:
            failures.append(cid)
            log(f"[{i + 1}/{len(todo)}] {cid}: FAIL {str(e)[:150]}")
        save_state(st)
        time.sleep(2)
    # второй проход: упавшие во время плохих окон шард-ов часто оживают
    if failures:
        log(f"второй проход по {len(failures)} упавшим: {failures}")
        for cid in list(failures):
            try:
                run_coll(cid, st)
                failures.remove(cid)
            except Exception as e:
                log(f"  {cid}: FAIL {str(e)[:150]}")
            save_state(st)
            time.sleep(2)
    for cid in failures:
        st["failed"].append({"id": cid, "error": "исчерпаны ретраи в обоих проходах"})
    if failures or st["failed"]:
        save_state(st)
    rebuild()
    log(f"готово за {(time.time() - t0) / 60:.0f} мин; failed всего: {len(st['failed'])}")


if __name__ == "__main__":
    main()
