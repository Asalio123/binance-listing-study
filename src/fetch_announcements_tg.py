"""Скрейп публичного TG-канала binance_announcements (веб-превью t.me/s/).

Пагинация ?before=<msg_id>, ~20 сообщений на страницу. На каждое сообщение:
msg_id, datetime (ISO, UTC), текст, ссылки (href). Дамп — в
data/tg_announcements_scrape.json, инкрементально каждые 25 страниц;
возобновляемо с минимального собранного msg_id.
"""
import html as htmllib
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path.home() / "binance-listing-study"
OUT = ROOT / "data" / "tg_announcements_scrape.json"
URL = "https://t.me/s/binance_announcements"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
PAUSE = 0.7

RE_POST = re.compile(r'data-post="binance_announcements/(\d+)"')
RE_TIME = re.compile(r'<time datetime="([^"]+)"')
RE_TEXTDIV = re.compile(
    r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>',
    re.S)
RE_HREF = re.compile(r'href="([^"]+)"')
RE_TAG = re.compile(r"<[^>]+>")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode(errors="replace")


def parse_page(html: str) -> list[dict]:
    msgs = []
    for block in re.split(r'<div class="tgme_widget_message_wrap', html)[1:]:
        m_post = RE_POST.search(block)
        m_time = RE_TIME.search(block)
        if not m_post or not m_time:
            continue
        text, hrefs = "", []
        m_text = RE_TEXTDIV.search(block)
        if m_text:
            frag = m_text.group(1)
            hrefs = RE_HREF.findall(frag)
            frag = re.sub(r"<br\s*/?>", "\n", frag)
            text = htmllib.unescape(RE_TAG.sub("", frag)).strip()
        msgs.append({"msg_id": int(m_post.group(1)),
                     "datetime": m_time.group(1),
                     "text": text, "hrefs": hrefs})
    return msgs


def main():
    seen = {}
    if OUT.exists():
        for m in json.load(OUT.open()):
            seen[m["msg_id"]] = m
        before = min(seen)
        print(f"возобновление: {len(seen)} сообщений, before={before}", flush=True)
    else:
        before = None

    t0 = time.time()
    page = 0
    stall = 0
    while True:
        url = URL if before is None else f"{URL}?before={before}"
        html = None
        for attempt in range(4):
            try:
                html = fetch(url)
                break
            except Exception as e:
                print(f"page before={before} FAIL {e}, retry {attempt}", flush=True)
                time.sleep(5 * (attempt + 1))
        if html is None:
            print(f"аборт на before={before}", flush=True)
            break
        msgs = parse_page(html)
        new = [m for m in msgs if m["msg_id"] not in seen]
        for m in new:
            seen[m["msg_id"]] = m
        page += 1
        if msgs:
            new_before = min(m["msg_id"] for m in msgs)
            stall = 0 if before is None or new_before < before else stall + 1
            before = new_before
        else:
            stall += 1
        if page % 25 == 0:
            OUT.write_text(json.dumps(sorted(seen.values(),
                                             key=lambda m: m["msg_id"])))
            dt = time.time() - t0
            print(f"стр {page} | всего {len(seen)} | before={before} | "
                  f"{dt/60:.1f} мин", flush=True)
        if stall >= 2 or (msgs and before <= 1):
            break
        time.sleep(PAUSE)

    OUT.write_text(json.dumps(sorted(seen.values(), key=lambda m: m["msg_id"])))
    print(f"готово: {len(seen)} сообщений, страниц {page}", flush=True)


if __name__ == "__main__":
    main()
