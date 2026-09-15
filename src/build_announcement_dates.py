"""Матчинг кэша CMS-деталей + TG-дампа к панели 470 листингов.

Паттерны заголовков (приоритет сверху вниз):
  will_list   — «Binance Will List X (TICKER)»
  lists       — «Binance Lists X (TICKER)»
  hodler      — «Introducing X (TICKER) on Binance HODLer Airdrops»
  launchpool  — Launchpool-анонс
  megadrop    — Megadrop-анонс
  adds_pairs  — «Binance Adds ... Trading Pairs» (матчинг по TICKER/USDT в теле)
Futures/Options-заголовки из спот-матчинга исключаются.

Выход: data/announcement_dates.csv
  symbol, announce_ts_utc, trading_open_text, article_code, match_pattern,
  source (cms/tg), confidence (high/medium/low), notes
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path.home() / "binance-listing-study"
CACHE = ROOT / "data" / "cms_details_cache"
TG = ROOT / "data" / "tg_announcements_scrape.json"
PANEL = ROOT / "data" / "listing_events_enriched.csv"
DAY0 = ROOT / "data" / "day0_turnover.csv"
OUT = ROOT / "data" / "announcement_dates.csv"

PATTERNS = ["will_list", "lists", "hodler", "launchpool", "megadrop",
            "launchpad", "adds_pairs", "notice_pairs", "rebrand"]
RE_PAREN_RAW = re.compile(r"\(([^()]{1,20})\)")


def paren_tickers(s: str) -> set[str]:
    """Скобочные тикеры: регистронезависимо, нормализация в upper;
    полностью строчные содержимые («(s)», «(etc)») отбрасываются."""
    out = set()
    for x in RE_PAREN_RAW.findall(s):
        x = x.strip()
        if re.fullmatch(r"[A-Za-z0-9]{1,15}", x) and not x.islower():
            out.add(x.upper())
    return out


RE_PAREN = re.compile(r"\(([A-Z0-9]{1,15})\)")  # legacy, не использовать
RE_PAIR = re.compile(r"\b([A-Z0-9]{2,15})/USDT\b")
RE_OPEN_FOR = re.compile(r"trading for (?:the )?([A-Z0-9]{2,15})\b")
RE_REBRAND_TO = re.compile(
    r"\b(?:to|into)\b[^()]{0,60}?\(([A-Za-z0-9]{1,15})\)", re.I)
RE_REBRAND_BARE = re.compile(
    r"\b(?:to|into)\s+(?:the\s+)?(?:new\s+)?(?:ticker\s+)?([A-Z0-9]{2,15})\b")
RE_TRADING_OPEN = re.compile(
    r"((?:open(?:ing)? (?:of )?trading|trading (?:will )?open)[^.]{0,160}?"
    r"\d{4}-\d{2}-\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?\s*\(UTC\))",
    re.I)
RE_FUTURES = re.compile(r"futures|options|quarterly|perpetual|contract", re.I)
RE_NOTICE_PAIRS = re.compile(
    r"notice of (addition|new).{0,40}trading pairs?|"
    r"notice on new trading pairs|new trading pairs on binance spot", re.I)
RE_OPEN_SEG = re.compile(
    r"open(?:ing)? (?:of )?trading for (?:the )?([A-Za-z0-9/, ]+?)"
    r"(?:\s+spot)?\s+trading pairs?", re.I)
RE_REBRAND_TITLE = re.compile(
    r"rebrand|token swap|token migration|redenominat|token merge|"
    r"update the ticker", re.I)

# Рескью-карта: символ панели → статья вне catalog48 (support-каталог),
# найденная через TG; тело проверено на упоминание нового тикера.
RESCUE = {
    "BTTC": "2722e6da4f5141dd9b2fb07b5b1f3f75",
    "T": "96698a6a80f64cb1ae27f813032bfaa9",
    "PUNDIX": "8bdcb060635b491d912247fb00603d4d",
    "EPX": "cf9526489aa041508f4cd57612f34119",
    "FIRO": "4a06d6ab6abb4f08b12bb93d6fec30ec",
    "XNO": "3dc8f6de281f4781a246a1658a21cb80",
}

# Алиасы переименованных тикеров (панель → тикер на момент анонса),
# применяются только если точный матч не найден. Только проверенные по day0.
ALIASES: dict[str, list[str]] = {}


def body_text(body: str) -> str:
    """body — JSON-дерево нод либо (редко, старые статьи) HTML.
    Обход строго в порядке документа (важно для секций add/remove)."""
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


def classify(title: str) -> str | None:
    tl = title.lower()
    if RE_FUTURES.search(title) and "spot" not in tl:
        return None
    if "will list" in tl:
        return "will_list"
    if re.match(r"binance lists", tl):
        return "lists"
    if "hodler airdrop" in tl:
        return "hodler"
    if "launchpool" in tl:
        return "launchpool"
    if "megadrop" in tl:
        return "megadrop"
    if "launchpad" in tl or "will open trading" in tl:
        return "launchpad"
    if RE_REBRAND_TITLE.search(title):
        return "rebrand"
    if RE_NOTICE_PAIRS.search(title):
        return "notice_pairs"
    if re.search(r"adds?\b.*trading pair", tl) or "bstock" in tl:
        return "adds_pairs"
    return None


def load_articles() -> list[dict]:
    arts = []
    for p in sorted(CACHE.glob("*.json")):
        try:
            d = json.load(p.open()).get("data") or {}
        except json.JSONDecodeError:
            continue
        title = d.get("title") or ""
        pat = classify(title)
        if pat is None or d.get("publishDate") is None:
            continue
        text = body_text(d.get("body") or "")
        tickers = paren_tickers(title)
        if pat == "rebrand":
            tickers |= {t.upper() for t in RE_REBRAND_TO.findall(title)
                        if not t.islower()}
            tickers |= set(RE_REBRAND_BARE.findall(title))
        if pat == "notice_pairs":
            # только ДОБАВЛЯЕМЫЕ пары — из предложения «open trading for ...»;
            # секция remove/delist в выборку не попадает
            for seg in RE_OPEN_SEG.findall(text):
                tickers |= set(RE_PAIR.findall(seg))
        if pat in ("adds_pairs",):  # пары только из тела
            tickers |= set(RE_PAIR.findall(text))
        elif pat == "launchpad" and not tickers:
            tickers |= set(RE_OPEN_FOR.findall(title))
        if not tickers:  # фолбэк: пары из тела, если в заголовке нет скобок
            tickers |= set(RE_PAIR.findall(text))
        m_open = RE_TRADING_OPEN.search(text)
        arts.append({
            "code": p.stem, "title": title, "pattern": pat,
            "publish_ms": int(d["publishDate"]),
            "ts": pd.Timestamp(int(d["publishDate"]), unit="ms", tz="UTC"),
            "tickers": tickers,
            "raw_parens": set(RE_PAREN_RAW.findall(title)),
            "trading_open_text": m_open.group(1).strip() if m_open else "",
            "bstock": "bstock" in title.lower(),
            "leveraged": bool(re.search(r"leveraged token|blvt", title, re.I)),
        })
    return arts


RE_TG_LISTING = re.compile(
    r"will list|binance lists|hodler airdrops?|launchpool|megadrop|"
    r"launchpad|token sale", re.I)
RE_TG_ADDS = re.compile(r"adds?\b.*trading pairs?", re.I)
RE_TG_REBRAND = RE_REBRAND_TITLE
RE_TG_CODE = re.compile(r"announcement/(?:detail/)?([0-9a-f]{32})")


def tg_index() -> tuple[dict, dict, dict, dict]:
    """code → datetime (кроссчек); ticker → listing / adds-pairs /
    rebrand-сообщения (добивка)."""
    if not TG.exists():
        return {}, {}, {}, {}
    msgs = json.load(TG.open())
    by_code, by_ticker, adds, rebrand = {}, {}, {}, {}
    for m in msgs:
        codes = set()
        for h in m["hrefs"] + [m["text"]]:
            codes |= set(RE_TG_CODE.findall(h))
        for c in codes:
            by_code.setdefault(c, m["datetime"])
        head = m["text"].split("\n", 1)[0]
        if RE_TG_LISTING.search(m["text"]):
            for t in paren_tickers(head):
                by_ticker.setdefault(t, []).append(m)
        if RE_TG_ADDS.search(head):
            for t in RE_PAIR.findall(head):
                adds.setdefault(t, []).append(m)
        if RE_TG_REBRAND.search(m["text"]):
            ts = {t.upper() for t in RE_REBRAND_TO.findall(head)
                  if not t.islower()}
            ts |= set(RE_REBRAND_BARE.findall(head))
            for t in ts:
                rebrand.setdefault(t, []).append(m)
    return by_code, by_ticker, adds, rebrand


def main():
    panel = pd.read_csv(PANEL)
    day0 = pd.read_csv(DAY0, parse_dates=["day0_date"])
    day0_map = {r.symbol: pd.Timestamp(r.day0_date, tz="UTC")
                for r in day0.itertuples()}

    arts = load_articles()
    print(f"статей в кэше с listing-паттерном: {len(arts)}", flush=True)
    idx = {}
    by_code = {}
    for a in arts:
        by_code[a["code"]] = a
        for t in a["tickers"]:
            idx.setdefault(t, []).append(a)

    tg_by_code, tg_by_ticker, tg_adds, tg_rebrand = tg_index()

    def tg_cands(base: str) -> list[dict]:
        """Ранние TG-кандидаты: первое listing-сообщение и первое
        rebrand-сообщение по тикеру (раннее = анонс, не completion)."""
        out = []
        for pool, pat, note in ((tg_by_ticker, "tg_text", ""),
                                (tg_adds, "tg_adds", ""),
                                (tg_rebrand, "tg_rebrand", "rebrand_swap")):
            msgs = pool.get(base, [])
            if not msgs:
                continue
            m = min(msgs, key=lambda m: m["datetime"])
            codes = set()
            for h in m["hrefs"] + [m["text"]]:
                codes |= set(RE_TG_CODE.findall(h))
            m_open = RE_TRADING_OPEN.search(m["text"])
            ts = pd.Timestamp(m["datetime"])
            out.append({
                "code": sorted(codes)[0] if codes else "",
                "title": m["text"].split("\n", 1)[0],
                "pattern": pat, "publish_ms": int(ts.timestamp() * 1000),
                "ts": ts, "tickers": {base},
                "trading_open_text": m_open.group(1).strip() if m_open else "",
                "bstock": False, "leveraged": False,
                "source": "tg", "note_extra": note,
            })
        return out

    def rank(c: dict) -> int:
        order = {"will_list": 0, "lists": 1, "hodler": 2, "launchpool": 3,
                 "megadrop": 4, "launchpad": 5, "adds_pairs": 6,
                 "notice_pairs": 6, "rebrand": 7, "tg_text": 8, "tg_adds": 8,
                 "tg_rebrand": 9}
        return order[c["pattern"]]

    def lag_days(c: dict, d0: pd.Timestamp) -> int:
        return (d0.normalize() - c["ts"].normalize()).days

    rows, unmatched = [], []
    for sym in panel.symbol:
        base = sym.replace("USDT", "")
        d0 = day0_map.get(sym)
        forced = by_code.get(RESCUE.get(base, "")) or None
        used = base
        if forced is not None:
            cands = [forced]
        else:
            cands = []
            for t in [base] + ALIASES.get(base, []):
                if t in idx:
                    cands = idx[t]
                    used = t
                    break
            if not cands:  # фолбэк: сырое совпадение скобок (CJK-тикеры)
                cands = [a for a in arts if base in a["raw_parens"]]
            cands = cands + tg_cands(base)
        if not cands:
            unmatched.append(sym)
            continue

        if d0 is not None:
            ontime = [c for c in cands if c["ts"] <= d0 + pd.Timedelta(days=1)]
            late = [c for c in cands if c["ts"] > d0 + pd.Timedelta(days=1)]
        else:
            ontime, late = cands, []
        override = False
        if ontime:
            # TG-кандидатам +1ч к dist: при почти-ничьей предпочитаем CMS
            dist = (lambda c: abs((c["ts"] - d0).total_seconds())
                    + (3600 if c.get("source") == "tg" else 0)) \
                if d0 is not None else (lambda c: 0)
            best = min(ontime, key=lambda c: (rank(c), dist(c)))
            prox = min(ontime, key=dist)
            # guard от переиспользованных тикеров: приоритетный кандидат
            # далеко (>90д), а существенно ближе (на >30д) есть другой
            if (d0 is not None and lag_days(best, d0) > 90
                    and lag_days(prox, d0) <= 365
                    and lag_days(prox, d0) < lag_days(best, d0) - 30):
                best = prox
                override = True
        elif late:
            best = min(late, key=lambda c: (rank(c), c["publish_ms"]))
        else:
            unmatched.append(sym)
            continue

        notes = []
        if used != base:
            notes.append(f"alias:{used}")
        if forced is not None:
            notes.append("rebrand_swap")
        if best.get("note_extra"):
            notes.append(best["note_extra"])
        if override:
            notes.append("proximity_override")
        if best["bstock"]:
            notes.append("bstock")
        if best["leveraged"]:
            notes.append("leveraged")
        src = best.get("source", "cms")
        if src == "tg":
            conf = "low"
        else:
            conf = "medium" if best["pattern"] in ("adds_pairs", "rebrand",
                                                   "notice_pairs") \
                else "high"
        rows.append({
            "symbol": sym,
            "announce_ts_utc": best["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trading_open_text": best["trading_open_text"],
            "article_code": best["code"],
            "match_pattern": best["pattern"],
            "source": src,
            "confidence": conf,
            "notes": ";".join(notes),
        })

    # аномалии для всех строк (announce позже day0+1д; лаг >30 дней)
    for r in rows:
        d0 = day0_map.get(r["symbol"])
        if d0 is None:
            continue
        ts = pd.Timestamp(r["announce_ts_utc"])
        lag_d = (d0.normalize() - ts.normalize()).days
        if ts > d0 + pd.Timedelta(days=1):
            r["notes"] = ";".join(filter(None, [r["notes"],
                                                "anomaly:announce_after_listing"]))
        elif lag_d > 30:
            r["notes"] = ";".join(filter(None, [r["notes"],
                                                "anomaly:lag_gt_30d"]))

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"сматчено всего: {len(df)}/470 (CMS + TG) | "
          f"не сматчено: {len(unmatched)}", flush=True)
    print("несматченные:", " ".join(unmatched), flush=True)


    # --- стадия 3: кроссчек publishDate vs TG datetime (20 случайных) ---
    cms_rows = df[df.source == "cms"]
    shared = cms_rows[cms_rows.article_code.isin(tg_by_code)]
    if len(shared):
        samp = shared.sample(min(20, len(shared)), random_state=42)
        deltas = []
        for r in samp.itertuples():
            d_pub = pd.Timestamp(r.announce_ts_utc)
            d_tg = pd.Timestamp(tg_by_code[r.article_code])
            deltas.append(abs((d_pub - d_tg).total_seconds()) / 60)
            print(f"  xcheck {r.symbol}: CMS {r.announce_ts_utc} vs TG "
                  f"{tg_by_code[r.article_code]} | Δ{deltas[-1]:.0f} мин",
                  flush=True)
        print(f"кроссчек: n={len(deltas)}, медиана Δ "
              f"{pd.Series(deltas).median():.0f} мин, макс Δ "
              f"{max(deltas):.0f} мин", flush=True)

    # лаг-статистика: дневной уровень (day0_date — дата, не таймстамп)
    d0 = pd.read_csv(DAY0, parse_dates=["day0_date"])
    m = df.merge(d0, on="symbol", how="left")
    ann = pd.to_datetime(m.announce_ts_utc, utc=True)
    lag_d = (pd.to_datetime(m.day0_date, utc=True) - ann.dt.tz_convert("UTC").dt.normalize()).dt.days
    print(f"лаг (дни, дневной уровень): медиана {lag_d.median():.0f} | "
          f"p25 {lag_d.quantile(.25):.0f} | p75 {lag_d.quantile(.75):.0f} | "
          f"=0д: {(lag_d == 0).mean()*100:.1f}% | <=1д: {(lag_d <= 1).mean()*100:.1f}%",
          flush=True)


if __name__ == "__main__":
    main()
