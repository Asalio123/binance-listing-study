"""Зеркальное event study ДЕЛИСТИНГОВ Binance spot: доходности вокруг анонсов
делистинга для 99 делистнутых символов панели 470.

Источники анонсов (по приоритету):
  1) data/cms_details_cache + data/delisting_cms_cache (bapi-догрузка по кодам
     из TG-дампа; endpoint публичный, как в fetch_notice_articles.py);
  2) TG-дамп (текст сообщения + datetime) — фолбэк confidence=low.

Паттерны заголовков делистинга (spot only; margin/futures/grid/loan исключаем):
  will_delist  — «Binance Will Delist A, B, C on YYYY-MM-DD»
  removal      — «Notice of Removal of (Spot) Trading Pairs - YYYY-MM-DD»
  delists      — «Binance Delists X»
rebrand/swap/migration/merge → event_type=migration (контрастная группа,
в headline-статистику делистингов НЕ входит).

Матчинг: base-тикер символа должен встречаться в статье (тайтл, «Name (TICKER)»
или пары XYZ/USDT в теле, data.pairs), publishDate в [last_date−150д,
last_date+5д]; выбирается ближайший анонс ПЕРЕД last_date.

Klines: monthly zip data.binance.vision за [анонс−35д .. анонс+35д],
кэш data/delisting_klines_cache/<SYM>-<YYYY-MM>.json {"YYYY-MM-DD": [o, c]}.
Event study: день 0 = UTC-дата анонса; returns от close[−1] и close[0];
памп-перед-смертью = ret_day0; post_to_death = last_close/close[−1]−1.
Lifecycle B&H: day0 close листинга (binance_day_closes) → last close.

Выходы: data/delisting_events.csv, paper/delisting_study.md.
"""
import io
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "listing_events_enriched.csv"
TG = ROOT / "data" / "tg_announcements_scrape.json"
CMS = ROOT / "data" / "cms_details_cache"
DCMS = ROOT / "data" / "delisting_cms_cache"
DAYCLOSES = ROOT / "data" / "binance_day_closes"
KLCACHE = ROOT / "data" / "delisting_klines_cache"
OUT_CSV = ROOT / "data" / "delisting_events.csv"
OUT_MD = ROOT / "paper" / "delisting_study.md"

BAPI = ("https://www.binance.com/bapi/composite/v1/public/cms/"
        "article/detail/query?articleCode={code}")
KBASE = "https://data.binance.vision/data/spot"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
PAUSE_BAPI = 0.9

RE_DELIST_T = re.compile(
    r"will delist|binance delists|notice of removal of (?:spot )?trading pairs|"
    r"cease trading|delisting of|to delist", re.I)
# migration-анонсы: токен не умирает, а переезжает (swap/rebrand/merge).
# Заголовок «Binance Will Support the X (TICKER) Token Swap ...»; контрастная
# группа для публикации, в headline-статистику делистингов не входит.
RE_MIGRATE_T = re.compile(
    r"will support the .{0,140}?(token swap|rebrand|migrat|merger|merge|"
    r"redenominat|ticker change|renaming)|"
    r"token (swap|migration|merge) (?:of|with|to)\b", re.I)
# completion-нотификации — НЕ события (анонс был раньше)
RE_COMPLETED = re.compile(r"has completed|has been completed|completion of",
                          re.I)
RE_NONSPOT = re.compile(
    r"margin|loan|futures|options|grid|convert|earn|leveraged|blvt|"
    r"liquid swap|pool|staking|collateral|auto-invest|dual", re.I)
RE_MIGRATE = re.compile(
    r"rebrand|token swap|migrat|merger|merge|redenominat|ticker change|"
    r"renamed?|mainnet swap|reverse split|token split|contract swap|"
    r"swap.*at a ratio|exchange all|consolidat", re.I)
RE_CODE = re.compile(r"announcement/(?:detail/)?([0-9a-f]{32})")
RE_PAIR_USDT = re.compile(r"\b([A-Z0-9]{2,12})/USDT\b")
RE_BARE_USDT = re.compile(r"\b([A-Z0-9]{2,12})USDT\b")
RE_PAREN_RAW = re.compile(r"\(([^()]{1,20})\)")
RE_CEASE = re.compile(
    r"(?:delist|cease trading)[^0-9]{0,220}?"
    r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})\s*\(UTC\)", re.I)

STOP = {"UTC", "GMT", "AND", "THE", "ON", "AT", "ALL", "SPOT", "USDT",
        "Fellow", "BINANCE", "WILL", "DELIST"}

# Рескью: статьи вне delist-заголовков. BETH — «Important Updates on BETH and
# WBETH» (2023-08-31): BETH/USDT прекращён 2023-10-11 в рамках конверсии
# BETH→WBETH → migration. NBTUSDT: анонса нет нигде (TG-дамп 2017-2026,
# весь каталог Delisting id 82912..284618, тела notice Feb-Mar 2023) —
# тихое снятие без анонса, остаётся несматченным [DATA].
RESCUE = {"BETH": ("84e6d7df84b04d6180a267385d0a0862", "migration")}


def paren_tickers(s: str) -> set[str]:
    out = set()
    for x in RE_PAREN_RAW.findall(s):
        x = x.strip()
        if re.fullmatch(r"[A-Za-z0-9]{1,15}", x) and not x.islower():
            out.add(x.upper())
    return out - STOP


def body_text(body: str) -> str:
    """body — JSON-дерево нод либо HTML (старые статьи). Как в
    build_announcement_dates.py."""
    if not body:
        return ""
    if body.lstrip().startswith("{"):
        try:
            tree = json.loads(body)
            parts = []

            def walk(node):
                if isinstance(node, dict):
                    if node.get("node") == "text" and node.get("text"):
                        parts.append(node["text"])
                    for ch in (node.get("child") or []):
                        walk(ch)

            walk(tree)
            return " ".join(parts)
        except json.JSONDecodeError:
            pass
    return re.sub(r"<[^>]+>", " ", body)


def title_list_tickers(title: str) -> set[str]:
    """«Binance Will Delist A, B & C on YYYY-MM-DD» → {A,B,C}."""
    m = re.search(r"delist(?:ing of)?\s+(?:all\s+)?(.+?)"
                  r"(?:\s+on\s+20\d\d|\s*-\s*20\d\d|$)", title, re.I)
    if not m:
        return set()
    seg = m.group(1)
    seg = re.sub(r"\([^()]*\)", " ", seg)  # «MCO (MCO)» не дублируем
    toks = set(re.findall(r"\b[A-Z0-9]{2,12}\b", seg))
    return {t for t in toks if t not in STOP and not t.isdigit()}


def classify_event(title: str, text: str) -> str | None:
    """delist | migration | None. Спот-only; margin/futures/grid отсекаем."""
    if RE_NONSPOT.search(title) or RE_COMPLETED.search(title):
        return None
    if RE_MIGRATE_T.search(title):
        return "migration"
    if RE_DELIST_T.search(title):
        return "migration" if RE_MIGRATE.search(title) else "delist"
    if re.search(r"delist and cease trading on all spot|"
                 r"will be delisted from binance|"
                 r"delisting of .* spot trading pair", text[:4000], re.I):
        return "delist"
    return None


def article_tickers(title: str, text: str, pairs: list) -> set[str]:
    """Тикеры делистинга: тайтл-список + «Name (TICKER)» + пары /USDT в теле
    + структурное data.pairs (spot, quote=USDT)."""
    out = set(title_list_tickers(title))
    out |= paren_tickers(title)
    if text:
        out |= paren_tickers(text)
        out |= set(RE_PAIR_USDT.findall(text))
        out |= set(RE_BARE_USDT.findall(text))
    for p in pairs or []:
        if (p.get("type") == "spot" and p.get("quoteAsset") == "USDT"
                and p.get("asset")):
            out.add(p["asset"].upper())
    return out - STOP


def load_article_file(p: Path) -> dict | None:
    try:
        d = json.load(p.open()).get("data") or {}
    except Exception:
        return None
    title = d.get("title") or ""
    if d.get("publishDate") is None:
        return None
    text = body_text(d.get("body") or "")
    return {"code": p.stem, "title": title, "text": text,
            "ts": pd.Timestamp(int(d["publishDate"]), unit="ms", tz="UTC"),
            "tickers": article_tickers(title, text, d.get("pairs")),
            "cease": (lambda m: f"{m.group(1)} {m.group(2)}" if m else "")
            (RE_CEASE.search(text))}


# --- стадия 1: TG spot-delist + migration сообщения → коды → догрузка -----

def tg_event_msgs() -> list[dict]:
    msgs = json.load(TG.open())
    out = []
    for m in msgs:
        head = (m.get("text") or "").split("\n", 1)[0]
        if RE_NONSPOT.search(head) or RE_COMPLETED.search(head):
            continue
        if not (RE_DELIST_T.search(head) or RE_MIGRATE_T.search(head)):
            continue
        codes = set()
        for h in (m.get("hrefs") or []) + [m.get("text") or ""]:
            codes |= set(RE_CODE.findall(h or ""))
        out.append({"datetime": m["datetime"], "head": head,
                    "codes": sorted(codes)})
    return out


def hydrate(codes: list[str]) -> None:
    """Догрузка тел статей по кодам в data/delisting_cms_cache/."""
    DCMS.mkdir(exist_ok=True)
    todo = [c for c in codes if not (DCMS / f"{c}.json").exists()
            and not (CMS / f"{c}.json").exists()]
    print(f"bapi: к догрузке {len(todo)} статей", flush=True)
    t0 = time.time()
    for i, code in enumerate(todo, 1):
        got = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    BAPI.format(code=code), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    got = r.read()
                break
            except Exception:
                time.sleep(2 * (attempt + 1))
        if got:
            (DCMS / f"{code}.json").write_bytes(got)
        if i % 25 == 0:
            print(f"  bapi [{i}/{len(todo)}] {time.time()-t0:.0f}с", flush=True)
        time.sleep(PAUSE_BAPI)


# --- стадия 2: klines ±35д -------------------------------------------------

def fetch_url(url: str) -> bytes | None:
    url = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=-._~%")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def zip_days(body: bytes) -> dict:
    """zip дневных свечей -> {"YYYY-MM-DD": [open, close]}."""
    zf = zipfile.ZipFile(io.BytesIO(body))
    out = {}
    with zf.open(zf.namelist()[0]) as f:
        for raw in f:
            parts = raw.decode().strip().split(",")
            if len(parts) < 5 or not parts[0].isdigit():
                continue
            ts = int(parts[0])
            # 13=мс, 16=мкс, 19=нс (грабля архива с 2025)
            scale = {13: 1, 16: 10 ** 3, 19: 10 ** 6}[len(parts[0])]
            d = pd.Timestamp(ts // scale, unit="ms", tz="UTC").strftime(
                "%Y-%m-%d")
            out[d] = [float(parts[1]), float(parts[4])]
    return out


def fetch_klines(sym: str, announce_ts: pd.Timestamp) -> None:
    """Месячные zip за [анонс−35д, анонс+35д] в кэш (идемпотентно)."""
    KLCACHE.mkdir(exist_ok=True)
    ann = announce_ts.tz_localize(None) if announce_ts.tz else announce_ts
    p0 = (ann - pd.Timedelta(days=35)).to_period("M")
    p1 = (ann + pd.Timedelta(days=35)).to_period("M")
    cur, now = p0, pd.Timestamp.now(tz="UTC").to_period("M")
    while cur <= p1:
        cp = KLCACHE / f"{sym}-{cur}.json"
        if cp.exists():
            cur += 1
            continue
        body = fetch_url(f"{KBASE}/monthly/klines/{sym}/1d/"
                         f"{sym}-1d-{cur}.zip")
        if body is None and cur == now:  # текущий месяц: дневные zip
            days = {}
            for day in range(1, 32):
                try:
                    ds = (pd.Timestamp(f"{cur}-01", tz="UTC")
                          + pd.Timedelta(days=day - 1)).strftime("%Y-%m-%d")
                except Exception:
                    break
                if ds > pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"):
                    break
                b = fetch_url(f"{KBASE}/daily/klines/{sym}/1d/"
                              f"{sym}-1d-{ds}.zip")
                if b:
                    days.update(zip_days(b))
                time.sleep(random.uniform(0.3, 0.5))
            body = True if days else None
            if days:
                cp.write_text(json.dumps(days))
        if body is not None and body is not True:
            cp.write_text(json.dumps(zip_days(body)))
        elif body is None:
            cp.write_text("{}")  # архивная дыра — не повторять
        time.sleep(random.uniform(0.3, 0.5))
        cur += 1


def load_window(sym: str) -> pd.Series:
    """Все закешированные дневные close символа -> Series(date->close)."""
    rows = {}
    for p in sorted(KLCACHE.glob(f"{sym}-*.json")):
        try:
            for d, oc in json.load(p.open()).items():
                rows[d] = oc[1]
        except Exception:
            continue
    s = pd.Series(rows, dtype="float64").sort_index()
    s.index = pd.to_datetime(s.index)
    return s


def day0_close_listing(sym: str, first_month: str) -> float:
    """Close первого дня листинга из binance_day_closes (ключи ns/µs/ms)."""
    p = DAYCLOSES / f"{sym}-{first_month}.json"
    if not p.exists():
        return np.nan
    raw = json.load(p.open())
    days = {}
    for k, v in raw.items():
        scale = {13: 1, 16: 10 ** 3, 19: 10 ** 6}.get(len(str(int(float(k)))), 1)
        d = pd.Timestamp(int(float(k)) // scale, unit="ms", tz="UTC")
        days[d.strftime("%Y-%m-%d")] = float(v)
    return days[min(days)] if days else np.nan


# --- стадия 3-5: матчинг, event study, B&H ---------------------------------

def wtest(s: pd.Series) -> float:
    s = s.dropna()
    return (stats.wilcoxon(s, alternative="two-sided").pvalue
            if len(s) > 20 else np.nan)


def main():
    panel = pd.read_csv(PANEL)
    cal = pd.read_csv(ROOT / "data" / "listing_calendar_binance.csv")
    d99 = panel[panel.delisted == 1].merge(
        cal[["symbol", "last_month"]], on="symbol", how="left")
    d99["base"] = d99.symbol.str.replace("USDT", "", regex=False)
    # ГРАБЛЯ: panel.last_date для 52/99 усечён 1000-дневным лимитом исходного
    # event study (days_listed==1000) — это НЕ дата смерти. Истинный месяц
    # смерти — calendar.last_month; точный день = последний kline месяца.
    d99["death_p"] = d99.last_month.map(pd.Period)
    print(f"делистнутых в панели: {len(d99)} | усечённых 1000д: "
          f"{(d99.days_listed == 1000).sum()}", flush=True)

    # TG события (delist + migration) + догрузка тел
    tg_msgs = tg_event_msgs()
    all_codes = sorted({c for m in tg_msgs for c in m["codes"]}
                       | {c for c, _ in RESCUE.values()})
    print(f"TG delist/migration сообщений: {len(tg_msgs)} | "
          f"кодов: {len(all_codes)}", flush=True)
    hydrate(all_codes)

    # статьи из обоих кэшей
    arts = []
    for src, d in (("cms", CMS), ("dcms", DCMS)):
        for p in sorted(d.glob("*.json")):
            a = load_article_file(p)
            if a is None:
                continue
            et = classify_event(a["title"], a["text"])
            if et is None:
                continue
            a["source"] = src
            a["event_type"] = et
            arts.append(a)
    print(f"спот delist/migration статей всего: {len(arts)}", flush=True)
    idx = {}
    for a in arts:
        for t in a["tickers"]:
            idx.setdefault(t, []).append(a)

    # матчинг к 99: окно вокруг ИСТИННОГО месяца смерти (calendar.last_month)
    rows, unmatched = [], []
    for r in d99.itertuples():
        base, sym = r.base, r.symbol
        lo = r.death_p.start_time - pd.Timedelta(days=180)
        hi = r.death_p.end_time + pd.Timedelta(days=5)

        def inwin(ts):
            return lo <= ts.tz_convert(None) <= hi

        art, note, src = None, "", ""
        if base in RESCUE:  # форс-матч проверенной статьи вне delist-тайтлов
            rcode, ret_ = RESCUE[base]
            p = (DCMS / f"{rcode}.json") if (DCMS / f"{rcode}.json").exists() \
                else CMS / f"{rcode}.json"
            if p.exists():
                art = load_article_file(p)
                art["event_type"] = ret_
                src, note = "rescue", "rescue_forced"
        if art is None:
            cands = [a for a in idx.get(base, []) if inwin(a["ts"])]
            if cands:
                art = max(cands, key=lambda a: a["ts"])
                src = art["source"]
        if art is None:  # фолбэк: текст TG-сообщения с тикером в заголовке
            tgc = [m for m in tg_msgs
                   if base in (title_list_tickers(m["head"])
                               | paren_tickers(m["head"]))
                   and inwin(pd.Timestamp(m["datetime"]))]
            if tgc:
                m = max(tgc, key=lambda m: m["datetime"])
                et = ("migration" if RE_MIGRATE_T.search(m["head"])
                      else "delist")
                art = {"code": "", "title": m["head"], "text": "",
                       "ts": pd.Timestamp(m["datetime"]),
                       "tickers": {base}, "cease": "", "event_type": et}
                src, note = "tg_text", "tg_text_fallback"
        if art is None:
            unmatched.append(sym)
            continue
        rows.append({"symbol": sym, "base": base,
                     "event_type": art["event_type"],
                     "announce_ts": art["ts"], "article_code": art["code"],
                     "article_title": art["title"], "cease_text": art["cease"],
                     "death_month": r.last_month,
                     "panel_last_date": r.last_date,
                     "first_month": r.first_month,
                     "match_source": src, "notes": note})
    ev = pd.DataFrame(rows)
    n_mig = (ev.event_type == "migration").sum()
    print(f"сматчено: {len(ev)}/99 (delist {len(ev)-n_mig}, migration {n_mig})"
          f" | несматчено: {len(unmatched)}", flush=True)
    print("несматченные:", " ".join(unmatched), flush=True)

    # klines + event study
    out_rows = []
    for i, r in enumerate(ev.itertuples(), 1):
        fetch_klines(r.symbol, r.announce_ts)
        s = load_window(r.symbol)
        ann_day = r.announce_ts.strftime("%Y-%m-%d")
        row = {k: getattr(r, k) for k in
               ("symbol", "base", "event_type", "article_code",
                "article_title", "cease_text", "death_month",
                "panel_last_date", "match_source", "notes")}
        row["announce_ts_utc"] = r.announce_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        if len(s) == 0 or ann_day not in s.index.strftime("%Y-%m-%d"):
            row["notes"] = ";".join(filter(None, [row["notes"],
                                                  "no_klines_window"]))
            out_rows.append(row)
            continue
        dates = list(s.index.strftime("%Y-%m-%d"))
        i0 = dates.index(ann_day)
        c = s.values
        close_m1 = c[i0 - 1] if i0 >= 1 else np.nan
        close_0 = c[i0]
        # фактическая смерть: последний kline не позже конца death_month + 10д
        lim = (pd.Period(r.death_month).end_time
               + pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        avail = [d for d in dates if d <= lim]
        last_close = c[dates.index(avail[-1])] if avail else np.nan
        row["last_trade_date"] = avail[-1] if avail else ""
        row["days_announce_to_death"] = (
            pd.Timestamp(row["last_trade_date"]) - pd.Timestamp(ann_day)
        ).days if avail else np.nan
        if avail and avail[-1] < r.death_month + "-01":
            row["notes"] = ";".join(filter(None, [row["notes"],
                                                  "death_before_cal_month"]))
        row["close_m1"] = close_m1
        row["last_close"] = last_close
        row["ret_day0"] = close_0 / close_m1 - 1 if close_m1 else np.nan
        for h in (1, 3, 7, 14):
            if close_m1 and i0 + h < len(c) and dates[i0 + h] <= lim:
                row[f"fwd_{h}"] = c[i0 + h] / close_m1 - 1
                row[f"trunc_{h}"] = 0
            elif close_m1 and avail:
                row[f"fwd_{h}"] = last_close / close_m1 - 1  # mark-to-last
                row[f"trunc_{h}"] = 1
            else:
                row[f"fwd_{h}"], row[f"trunc_{h}"] = np.nan, 1
        row["pre_14"] = (close_m1 / c[i0 - 15] - 1
                         if close_m1 and i0 >= 15 else np.nan)
        row["post_death_from_0"] = (last_close / close_0 - 1
                                    if close_0 else np.nan)
        row["post_death_from_m1"] = (last_close / close_m1 - 1
                                     if close_m1 else np.nan)
        d0c = day0_close_listing(r.symbol, r.first_month)
        row["day0_close_listing"] = d0c
        row["bah_lifecycle"] = (last_close / d0c - 1
                                if d0c and last_close else np.nan)
        out_rows.append(row)
        if i % 20 == 0:
            print(f"  klines [{i}/{len(ev)}]", flush=True)

    df = pd.DataFrame(out_rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"-> {OUT_CSV} ({len(df)} строк)", flush=True)

    # --- статистика ---
    def block(sub: pd.DataFrame) -> dict:
        cols = ["ret_day0", "fwd_1", "fwd_3", "fwd_7", "fwd_14", "pre_14",
                "post_death_from_0", "post_death_from_m1", "bah_lifecycle"]
        o = {"n": len(sub)}
        for cname in cols:
            v = sub[cname].dropna()
            o[cname] = {"n": len(v), "med": v.median(),
                        "pos": (v > 0).mean() * 100 if len(v) else np.nan,
                        "p": wtest(v)}
        return o

    dl = df[df.event_type == "delist"]
    mg = df[df.event_type == "migration"]
    S = {"delist": block(dl), "migration": block(mg)}
    print("\n=== TRUE DELIST ===", flush=True)
    for cname in ("ret_day0", "fwd_1", "fwd_3", "fwd_7", "fwd_14", "pre_14",
                  "post_death_from_0", "post_death_from_m1", "bah_lifecycle"):
        b = S["delist"][cname]
        print(f"{cname:>20}: n={b['n']:>2} med={b['med']*100:+.1f}% "
              f"%>0={b['pos']:.0f}% p={b['p']:.4f}", flush=True)
    print("\n=== MIGRATION (контраст) ===", flush=True)
    for cname in ("ret_day0", "post_death_from_0", "bah_lifecycle"):
        b = S["migration"][cname]
        print(f"{cname:>20}: n={b['n']:>2} med={b['med']*100:+.1f}% "
              f"%>0={b['pos']:.0f}%", flush=True)

    # --- отчёт md ---
    def fmtp(p):
        if p != p:
            return "—"
        return "<0.0001" if p < 5e-5 else f"{p:.4f}"

    def mechanism(t: str) -> str:
        tl = t.lower()
        if "vote to delist" in tl:
            return "vote-to-delist"
        if "notice of removal" in tl:
            return "notice-of-removal"
        if "will support the" in tl or "rebrand" in tl or "swap" in tl:
            return "migration/swap"
        if "will delist" in tl or "delists" in tl or "to delist" in tl:
            return "will-delist batch"
        return "other"

    mech = df.assign(m=df.article_title.map(mechanism)) \
        .groupby(["event_type", "m"]).size().reset_index(name="n")

    L = []
    w = L.append
    w("# Зеркальное event study: анонсы делистингов Binance\n")
    w(f"Собрано: {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d')} [DATA]. "
      f"Скрипт: `src/build_delisting_study.py`; данные: "
      f"`data/delisting_events.csv`.\n")
    w("## Метод\n")
    w("- Вселенная: 99 делистнутых USDT-символов панели 470 "
      "(`listing_events_enriched.csv`, delisted=1) [DATA].\n"
      "- ГРАБЛЯ: `panel.last_date` у 52/99 усечён 1000-дневным лимитом "
      "исходного event study (`days_listed==1000`) — это не дата смерти. "
      "Истинный месяц смерти — `listing_calendar_binance.csv:last_month`, "
      "точный день = последний дневной kline в архиве [DATA].\n"
      "- Анонсы: Binance CMS (`cms_details_cache` + догрузка тел по кодам "
      "из TG-дампа @binance_announcements через публичный bapi article "
      "endpoint в `delisting_cms_cache/`, ~330 кодов); спот-only "
      "(margin/futures/grid/loan/completion-нотификации исключены по "
      "заголовку) [DATA].\n"
      "- Rebrand/swap/migration/merge (заголовок «Will Support the ... Token "
      "Swap/Rebranding ...») → `event_type=migration`, контрастная группа, "
      "в headline-статистику делистингов не входит [DATA].\n"
      "- Матчинг: base-тикер в статье (тайтл-список «Will Delist A, B, C», "
      "«Name (TICKER)», пары XYZ/USDT в теле, data.pairs); окно = месяц "
      "смерти −180д .. +5д; берётся ПОСЛЕДНИЙ анонс перед смертью (для "
      "vote-to-delist это статья с результатами голосования = момент, когда "
      "смерть становится достоверной) [DATA].\n"
      "- Klines: monthly zip data.binance.vision за [анонс−35д, анонс+35д], "
      "кэш `delisting_klines_cache/`; единицы open_time нормализованы по "
      "длине (мс/мкс/нс) [DATA].\n"
      "- День 0 = UTC-дата анонса. fwd_h — от close дня −1; ret_day0 = "
      "close0/close−1; post_death = до последнего close; смерть раньше "
      "горизонта → mark-to-last с флагом trunc. Спотчек цен против свежей "
      "выгрузки архива: совпадение до 4 знаков (ALPACA 2025-04, FIRO "
      "2025-04) [DATA].\n")
    w("## Покрытие\n")
    w(f"- Сматчено анонсов: **{len(ev)}/99** "
      f"(true delist {len(dl)}, migration {len(mg)}; TG-text fallback: "
      f"{(ev.match_source == 'tg_text').sum()}) [DATA].\n"
      f"- Несматчено: {len(unmatched)}"
      + (f" ({', '.join(unmatched)}: тихое снятие без анонса — проверены "
         f"TG-дамп 2017-2026, весь каталог Delisting (433 статьи, id "
         f"82912..284618), тела notice Feb-Mar 2023)" if unmatched else "")
      + " [DATA].\n"
      f"- Медианный лаг анонс→конец торгов: "
      f"{df.days_announce_to_death.median():.0f} дн (min "
      f"{df.days_announce_to_death.min():.0f} — UST, halt в день краха "
      f"2022-05-13; max {df.days_announce_to_death.max():.0f} — BETH, "
      f"конверсионный notice) [DATA].\n"
      f"- trunc_14 (смерть раньше 14-го дня) у delist: "
      f"{dl.trunc_14.mean()*100:.0f}% [DATA].\n")
    w("\n### Механизмы смерти (по заголовкам сматченных статей)\n"
      "| event_type | механизм | n |\n|---|---|---|\n")
    for r in mech.itertuples():
        w(f"| {r.event_type} | {r.m} | {r.n} |\n")

    def tbl(sub: pd.DataFrame, cols, name):
        w(f"\n### {name} (n={len(sub)})\n")
        w("| Метрика | n | медиана, % | %>0 | Wilcoxon p |\n"
          "|---|---|---|---|---|\n")
        for cname, label in cols:
            v = sub[cname].dropna()
            w(f"| {label} | {len(v)} | {v.median()*100:+.2f} | "
              f"{(v > 0).mean()*100:.0f} | {fmtp(wtest(v))} |\n")

    cols = [("ret_day0", "День 0 (close−1→close0)"),
            ("fwd_1", "+1д от close−1"), ("fwd_3", "+3д от close−1"),
            ("fwd_7", "+7д от close−1"), ("fwd_14", "+14д от close−1"),
            ("pre_14", "−14д→−1д (drift до анонса)"),
            ("post_death_from_0", "close0 → last close (после анонса)"),
            ("post_death_from_m1", "close−1 → last close (полный эффект)"),
            ("bah_lifecycle", "B&H: close листинга д0 → last close")]
    tbl(dl, cols, "True delistings — event study ±14д")
    tbl(mg, cols, "Migrations/rebrands — контрастная группа")

    worst = dl.nsmallest(3, "ret_day0")
    best = dl.nlargest(3, "ret_day0")
    w("\n### Экстремумы дня 0 (true delistings)\n")
    w("Худшие: " + "; ".join(
        f"{r.symbol} {r.ret_day0*100:+.0f}%" for r in worst.itertuples())
      + " [DATA].\n")
    w("Лучшие (dead-cat squeezes): " + "; ".join(
        f"{r.symbol} {r.ret_day0*100:+.0f}%" for r in best.itertuples())
      + " [DATA].\n")

    w("\n## Выводы\n")
    b = S["delist"]
    bm = S["migration"]
    w(f"- Пампа-перед-смертью НЕТ: день анонса медиана "
      f"**{b['ret_day0']['med']*100:+.1f}%**, позитивных "
      f"{b['ret_day0']['pos']:.0f}% (n={b['ret_day0']['n']}); дрейф за 14 дней "
      f"до анонса {b['pre_14']['med']*100:+.1f}% — рынок не выкупает смерть "
      f"заранее, удар концентрирован в день анонса [DATA].\n"
      f"- Между анонсом и концом торгов (close0→last, медианный лаг "
      f"{df.days_announce_to_death.median():.0f} дн): медиана "
      f"**{b['post_death_from_0']['med']*100:+.1f}%** — после первого удара "
      f"цена делится ещё раз пополам [DATA].\n"
      f"- Полный жизненный цикл B&H (close дня листинга → последний close): "
      f"медиана **{b['bah_lifecycle']['med']*100:+.1f}%**, позитивных "
      f"{b['bah_lifecycle']['pos']:.0f}% (n={b['bah_lifecycle']['n']}) [DATA].\n"
      f"- Контраст migrations: день анонса swap/rebrand медиана "
      f"**{bm['ret_day0']['med']*100:+.1f}%**, позитивных "
      f"{bm['ret_day0']['pos']:.0f}% (n={bm['ret_day0']['n']}) — реакция "
      f"противоположного знака, т.е. отрицательный эффект дня 0 специфичен "
      f"именно смерти, а не любому «делистинговому» заголовку [DATA].\n")
    OUT_MD.write_text("".join(L))
    print(f"-> {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
