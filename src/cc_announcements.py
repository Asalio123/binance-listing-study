"""Даты анонсов листингов Binance из индексов Common Crawl (коллекции 2019+, resume-state, пагинация)."""
import json
import random
import re
import subprocess
import time
import urllib.parse
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


MIN_GAP = 20.0         # вежливый пейсинг между запросами
_last_req = [0.0]
CUR_COLL = ["?"]
PROXY = "socks5h://127.0.0.1:10808"  # локальный туннель: напрямую из РФ
                                     # канал к commoncrawl флапает (504/400/SSL-ресеты)


def _pace():
    delta = time.time() - _last_req[0]
    if delta < MIN_GAP:
        time.sleep(MIN_GAP - delta)
    _last_req[0] = time.time()


def fetch_page(url, tries=5, end_ok=False):
    """Тело ответа; '' при 404 (нулевая выдача или отсутствующий индекс).

    end_ok: HTTP 400 считается концом пагинации — на новом сервере запрос
    страницы за пределами выдачи отвечает голым nginx 400 вместо JSON-сообщения
    (2026-08-24), это норма, а не ошибка.
    """
    last = ""
    for attempt in range(tries):
        _pace()
        base = ["curl", "-sS", "--max-time", "300", "-A", UA["User-Agent"],
                "-w", "\n%{http_code}"]
        for extra in (["-x", PROXY], []):
            p = subprocess.run(base + extra + [url], capture_output=True, text=True)
            body, _, code = p.stdout.rpartition("\n")
            code = code.strip() or "000"
            if code == "200":
                return body
            if code == "404" or (code == "400" and end_ok):
                return ""
            last = f"HTTP {code} {p.stderr.strip()[:80]}"
        import os
        if os.environ.get("CC_DEBUG") and code != "404":
            pv = subprocess.run(["curl", "-v", "-sS", "--max-time", "60", "-A",
                                 UA["User-Agent"], "-o", "/dev/null"] +
                                (["-x", PROXY] if extra else []) + [url],
                               capture_output=True, text=True)
            keep = [l for l in pv.stderr.splitlines()
                    if any(k in l for k in ("Connected", "HTTP/", "Server:", "Via:",
                                            "subject:", "SSL connection", "error"))]
            log("    DEBUG -v:\n      " + "\n      ".join(keep[-10:]))
            if code != "000":
                break
        wait = min(45 * 2 ** attempt, 300) + random.uniform(0, 20)
        log(f"    [{CUR_COLL[0]}] {last}, ретрай {attempt + 1}/{tries} через {wait:.0f}с")
        time.sleep(wait)
    raise RuntimeError(f"[{CUR_COLL[0]}] исчерпаны ретраи: {last}")


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
    seen = set()
    CUR_COLL[0] = cid
    for page in range(MAX_PAGES):
        q = urllib.parse.urlencode({
            "url": "binance.com/en/support/announcement/*",
            "output": "json",
            # collapse=urlkey валит бэкенд на непустых коллекциях (400/504),
            # поэтому без него — дедуп клиентский, выдача отсортирована
            # по urlkey->timestamp, первый захват и так ранний
            "page": page,
        })
        body = fetch_page(f"https://index.commoncrawl.org/{cid}-index?{q}",
                          end_ok=(page > 0))
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
                key = r.get("urlkey") or r["url"]
                if key in seen:
                    continue
                seen.add(key)
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
    # добор: упавшие коллекции при такой нестабильности сервера решаются
    # ретрай-лотереей — даём им ещё два прохода
    for extra_pass in range(2):
        if not failures:
            break
        log(f"проход {extra_pass + 2} по {len(failures)} упавшим: {failures}")
        still = []
        for cid in failures:
            try:
                run_coll(cid, st)
            except Exception as e:
                still.append(cid)
                log(f"  {cid}: FAIL {str(e)[:150]}")
            save_state(st)
            time.sleep(2)
        failures = still
    for cid in failures:
        st["failed"].append({"id": cid, "error": "исчерпаны ретраи во всех проходах"})
    if failures or st["failed"]:
        save_state(st)
    rebuild()
    log(f"готово за {(time.time() - t0) / 60:.0f} мин; failed всего: {len(st['failed'])}")


if __name__ == "__main__":
    main()
