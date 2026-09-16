"""Минутный информационный шок анонсов листинга Binance на чужих биржах.

Binance публикует анонс (timestamp до секунды), а токен уже торгуется на
Coinbase или Bybit -> минутные бары вокруг announce_ts разделяют утечку
ДО публикации (-3ч -> 0) и информационный шок ПОСЛЕ (0 -> +3ч).

Источники (анонимные паблик API, проверены живыми пробами 2026-09-16):
  Coinbase Exchange: /products/{id}/candles?granularity=60&start&end
    - макс 300 бакетов/запрос, ответ newest-first, пустые бакеты опускаются;
    - история делистнутых продуктов отдаётся (NU-USD 2021, WBTC-USD 2023);
    - окно +/-3ч = 361 бар -> 2 запроса со сплитом у announce_ts.
  Bybit v5: /v5/market/kline?category=spot&interval=1&limit=1000
    - глубина от запуска спота (авг 2021); мёртвые символы -> пустой list.

Покрытие: кандидат = биржа торговала токен ДО announce_ts. Приоритет Coinbase
(death-inclusive), фолбэк Bybit. Граница "first_date == день анонса"
решается рантаймом (бар, содержащий announce_ts, либо предыдущий в окне).

Кэш: data/announce_shock_cache/{symbol}_{venue}_{stamp}.json (сырые бары).
Выходы: data/announcement_shock.csv, charts/announcement_shock_minutes.png,
        paper/announcement_shock.md
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.home() / "binance-listing-study"
DATA = ROOT / "data"
CACHE = DATA / "announce_shock_cache"
CACHE.mkdir(exist_ok=True)

CB_API = "https://api.exchange.coinbase.com"
BB_API = "https://api.bybit.com/v5/market/kline"
CB_SLEEP = 0.35          # ~3 req/s при паблик-лимите 10 req/s
BB_SLEEP = 0.20
WIN_S = 3 * 3600         # +/-3ч вокруг анонса
ASOF_TOL_S = 1800        # бар старше 30 мин от цели -> NaN + флаг thin
HORIZONS_MIN = (1, 5, 15, 60, 180)
HKEY = {1: "ret_p1m", 5: "ret_p5m", 15: "ret_p15m", 60: "ret_p1h", 180: "ret_p3h"}
METRIC_COLS = ["ret_m180_0"] + [HKEY[h] for h in HORIZONS_MIN]

lines = []


def md(s=""):
    lines.append(s)
    print(s, flush=True)


def get_json(url, retries=4):
    """GET -> parsed JSON; None при 404/исчерпании ретраев (дыра, не краш)."""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


# ---------------------------------------------------------------- fetch ----
def cb_bars(product, t0):
    """1-мин бары Coinbase [t0-3ч, t0+3ч+5мин], 2 запроса. None=мёртв/ошибка."""
    out = {}
    for a, b in ((t0 - WIN_S, t0), (t0, t0 + WIN_S + 300)):
        q = (f"granularity=60&start={pd.Timestamp(a, unit='s', tz='UTC').isoformat()}"
             f"&end={pd.Timestamp(b, unit='s', tz='UTC').isoformat()}")
        d = get_json(f"{CB_API}/products/{product}/candles?{q}")
        if d is None or isinstance(d, dict):   # dict = тело ошибки
            return None
        for r in d:                            # [time, low, high, open, close, vol]
            out[int(r[0])] = [int(r[0]), float(r[3]), float(r[2]),
                              float(r[1]), float(r[4]), float(r[5])]
        time.sleep(CB_SLEEP)
    return [out[k] for k in sorted(out)]


def bb_bars(symbol, t0):
    """1-мин бары Bybit [t0-3ч, t0+3ч], 1 запрос. None=ошибка, []=нет данных."""
    url = (f"{BB_API}?category=spot&symbol={symbol}&interval=1"
           f"&start={(t0 - WIN_S) * 1000}&end={(t0 + WIN_S) * 1000 + 59_999}&limit=1000")
    j = get_json(url)
    time.sleep(BB_SLEEP)
    if j is None or j.get("retCode") != 0:
        return None
    rows = {}
    for k in j["result"]["list"]:              # [start_ms, o, h, l, c, vol, turn]
        ts = int(k[0]) // 1000
        rows[ts] = [ts, float(k[1]), float(k[2]), float(k[3]),
                    float(k[4]), float(k[5])]
    return [rows[k] for k in sorted(rows)]


def load_bars(sym, venue, product, t0):
    """Кэш -> сеть. Возвращает (bars|None|[], from_cache)."""
    stamp = pd.Timestamp(t0, unit="s", tz="UTC").strftime("%Y%m%dT%H%M")
    cf = CACHE / f"{sym}_{venue}_{stamp}.json"
    if cf.exists():
        return json.loads(cf.read_text())["bars"], True
    bars = cb_bars(product, t0) if venue == "coinbase" else bb_bars(product, t0)
    cf.write_text(json.dumps({"venue": venue, "product": product, "bars": bars}))
    return bars, False


# --------------------------------------------------------------- metrics ----
def event_metrics(bars, t0):
    """p0 и кумулятивные ответы. Конвенции:
    p0 = close бара, содержащего t0; бакета нет (Coinbase опускает пустые)
         -> ближайший предыдущий бар, gap фиксируется; нет и его -> None
         (рынка ещё не было -> событие не покрыто);
    форвард-цель t0+h -> close последнего бара с open <= цели (asof), старше
         30 мин от цели -> NaN + thin;
    -3ч -> первый бар окна, дальше 30 мин от левого края -> NaN + thin.
    """
    if not bars:
        return None
    ts = np.array([b[0] for b in bars], dtype=np.int64)
    cl = np.array([b[4] for b in bars], dtype=float)
    exact = np.where((ts <= t0) & (t0 < ts + 60))[0]
    if len(exact):
        i0, gap0 = int(exact[0]), 0.0
    else:
        prev = np.where(ts < t0)[0]
        if not len(prev):
            return None
        i0 = int(prev[-1])
        gap0 = round(float(t0 - ts[i0]) / 60, 2)
    p0 = cl[i0]
    if not np.isfinite(p0) or p0 <= 0:
        return None
    m = {"p0_open_ts": int(ts[i0]), "p0_gap_min": gap0, "p0": p0,
         "n_bars": len(ts), "thin": 0}

    def asof_fwd(target):
        idx = np.where((ts <= target) & (ts >= ts[i0]))[0]
        if not len(idx) or target - ts[idx[-1]] > ASOF_TOL_S:
            return None
        return cl[idx[-1]]

    c_back = None
    after = np.where(ts >= t0 - WIN_S)[0]
    if len(after) and ts[after[0]] - (t0 - WIN_S) <= ASOF_TOL_S:
        c_back = cl[after[0]]
    m["ret_m180_0"] = p0 / c_back - 1 if c_back else np.nan
    if c_back is None:
        m["thin"] = 1
    for h in HORIZONS_MIN:
        c_h = asof_fwd(t0 + 60 * h)
        m[HKEY[h]] = c_h / p0 - 1 if c_h else np.nan
        if c_h is None:
            m["thin"] = 1
    return m


def minute_curve(bars, t0, p0):
    """Кумулятивный ответ на сетке -180..+180 мин (asof, толеранс 30 мин)."""
    ts = np.array([b[0] for b in bars], dtype=np.int64)
    cl = np.array([b[4] for b in bars], dtype=float)
    cur = {}
    for mm in range(-180, 181):
        target = t0 + 60 * mm
        idx = np.where(ts <= target)[0]
        cur[mm] = (cl[idx[-1]] / p0 - 1) if len(idx) and target - ts[idx[-1]] <= ASOF_TOL_S else np.nan
    return cur


def pre_3d_from_daily(venue, product, t0):
    """3-дневный пред-анонсный набег на дневных кэшах той же биржи (без сети):
    close(d-1)/close(d-4)-1, asof с толерансом 3 дня на пропуски."""
    f = (DATA / "coinbase_candles_cache" / f"{product}.json") if venue == "coinbase" \
        else (DATA / "bybit_klines_cache" / f"{product}.json")
    if not f.exists():
        return np.nan
    rows = json.loads(f.read_text())
    if not rows:
        return np.nan
    if venue == "coinbase":                    # [t_s, low, high, open, close, vol]
        d = {int(r[0]) // 86400: float(r[4]) for r in rows}
    else:                                      # [ms, o, h, l, c, v]
        d = {int(r[0]) // 86_400_000: float(r[4]) for r in rows}
    day = t0 // 86400

    def asof_day(dd):
        for k in range(dd, dd - 3, -1):
            if k in d:
                return d[k]
        return None

    c1, c4 = asof_day(day - 1), asof_day(day - 4)
    return c1 / c4 - 1 if (c1 and c4) else np.nan


def empty_rec(c, venue="none", product="", same_day=np.nan, vdel=np.nan, n_bars=0):
    rec = dict(symbol=c["symbol"], venue=venue, product=product,
               announce_ts_utc=str(c["ts"]), match_pattern=c["match_pattern"],
               confidence=c["confidence"], same_day=same_day, venue_delisted=vdel,
               p0_open_ts=np.nan, p0_gap_min=np.nan, p0=np.nan, n_bars=n_bars,
               thin=np.nan, pre_3d_runup=np.nan)
    for col in METRIC_COLS:
        rec[col] = np.nan
    return rec


# ------------------------------------------------------------------ main ----
def main():
    t_start = time.time()
    ann = pd.read_csv(DATA / "announcement_dates.csv")
    ann["ts"] = pd.to_datetime(ann["announce_ts_utc"], utc=True)
    ov = pd.read_csv(DATA / "coinbase_overlap.csv")
    ov["cb_first_date"] = pd.to_datetime(ov["cb_first_date"], utc=True)
    bbcal = pd.read_csv(DATA / "listing_calendar_bybit.csv")

    cb_by_sym = ov.set_index("symbol")
    bb_first = bbcal.set_index("symbol")["first_month"].to_dict()
    bb_dead = bbcal.set_index("symbol")["delisted"].to_dict()

    md(f"Событий в панели: {len(ann)}")

    # --- 1. кандидаты -----------------------------------------------------
    cands = []
    for r in ann.itertuples():
        t0 = int(r.ts.timestamp())
        cb = None
        if r.symbol in cb_by_sym.index:
            row = cb_by_sym.loc[r.symbol]
            if isinstance(row, pd.DataFrame):    # дубль символа в overlap
                row = row.iloc[0]
            if row["cb_first_date"] <= r.ts.normalize():
                cb = dict(product=row["cb_product"],
                          same_day=int(row["cb_first_date"] == r.ts.normalize()),
                          delisted=int(row["cb_delisted"]))
        bb = None
        fm = bb_first.get(r.symbol)
        if fm is not None and fm <= r.ts.strftime("%Y-%m"):
            bb = dict(product=r.symbol, same_day=int(fm == r.ts.strftime("%Y-%m")),
                      delisted=int(bb_dead.get(r.symbol, 0)))
        cands.append(dict(symbol=r.symbol, ts=r.ts, t0=t0,
                          match_pattern=r.match_pattern, confidence=r.confidence,
                          cb=cb, bb=bb))
    md(f"Кандидаты Coinbase (cb_first_date <= день анонса): "
       f"{sum(1 for c in cands if c['cb'])}")
    md(f"Кандидаты Bybit (first_month <= месяц анонса): "
       f"{sum(1 for c in cands if c['bb'])}")

    # --- 2. сбор ----------------------------------------------------------
    recs, n_net = [], 0
    for i, c in enumerate(cands, 1):
        venue = product = None
        bars = None
        for try_venue, info in (("coinbase", c["cb"]), ("bybit", c["bb"])):
            if info is None:
                continue
            bars, from_cache = load_bars(c["symbol"], try_venue, info["product"], c["t0"])
            n_net += 0 if from_cache else 1
            if bars:
                venue, product = try_venue, info["product"]
                same_day, vdel = info["same_day"], info["delisted"]
                break
        if venue is None:
            recs.append(empty_rec(c))
            continue
        m = event_metrics(bars, c["t0"])
        if m is None:
            recs.append(empty_rec(c, venue, product, same_day, vdel, len(bars)))
            continue
        rec = dict(empty_rec(c, venue, product, same_day, vdel))
        rec.update(m)
        rec["pre_3d_runup"] = pre_3d_from_daily(venue, product, c["t0"])
        rec["_curve"] = minute_curve(bars, c["t0"], m["p0"])
        recs.append(rec)
        if i % 50 == 0:
            print(f"...{i}/{len(cands)} ({time.time()-t_start:.0f}с, сеть: {n_net})",
                  flush=True)

    df = pd.DataFrame([{k: v for k, v in r.items() if k != "_curve"} for r in recs])
    df.to_csv(DATA / "announcement_shock.csv", index=False)
    cov = df[df.p0.notna()]
    md(f"\nСетевых загрузок: {n_net} (остальное из кэша или без кандидата)")
    md(f"Покрыто (есть p0): {len(cov)} / {len(df)}")

    # --- 3. feasibility-гейт ----------------------------------------------
    if len(cov) < 40:
        md("\n## СТОП: покрытие < 40 событий\n")
        md(f"Покрыто {len(cov)} из {len(df)}. Распределение по исходам:")
        md(df.groupby("venue").size().to_string())
        (ROOT / "paper" / "announcement_shock.md").write_text("\n".join(lines))
        print("гейт не пройден -> отчёт о невозможности записан", flush=True)
        return

    # --- 4. покрытие -------------------------------------------------------
    md("\n## Покрытие\n")
    md(f"- Всего событий: {len(df)}; с минутными данными вокруг анонса: **{len(cov)}** "
       f"({len(cov)/len(df)*100:.0f}%)")
    for v, n in cov.groupby("venue").size().items():
        dl = cov[cov.venue == v]
        md(f"- {v}: **{n}** (делистнутых на вене: {int(dl.venue_delisted.sum())}, "
           f"граничных same-day: {int(dl.same_day.sum())}, thin: {int(dl.thin.sum())})")
    cov_y = cov.assign(year=pd.to_datetime(cov.announce_ts_utc).dt.year)
    md("\nПо годам анонса: " + ", ".join(f"{y}: {n}" for y, n in
                                        cov_y.groupby("year").size().items()))
    md(f"\nМедиана p0_gap_min: {cov.p0_gap_min.median():.1f} мин "
       f"(0 = бар содержит announce_ts; >0 = тонкий рынок, взят предыдущий бар)")

    # --- 5. опорные точки --------------------------------------------------
    anchors = [("−3ч→0 (утечка)", "ret_m180_0"), ("0→+1мин", "ret_p1m"),
               ("0→+5мин", "ret_p5m"), ("0→+15мин", "ret_p15m"),
               ("0→+1ч", "ret_p1h"), ("0→+3ч", "ret_p3h")]
    md("\n## Медианные кумулятивные ответы (5 опорных точек + предокно)\n")
    md("| Горизонт | N | медиана | среднее | %>0 |")
    md("|---|---|---|---|---|")
    meds = {}
    for lab, col in anchors:
        x = cov[col].dropna() * 100
        meds[col] = x.median()
        md(f"| {lab} | {len(x)} | {x.median():+.2f}% | {x.mean():+.2f}% | "
           f"{(x > 0).mean()*100:.0f}% |")
    strong1 = (cov.ret_p1m.abs() > 0.005).mean() * 100
    md(f"\nДоля событий с |откликом за 1 мин| > 0.5%: {strong1:.0f}% "
       f"(у остальных рынок тонкий или реакция растянута)")

    # --- 6. декомпозиция набега --------------------------------------------
    md("\n## Декомпозиция пред-анонсного набега\n")
    dec = cov.dropna(subset=["pre_3d_runup"])
    if len(dec) >= 20:
        pre = dec.pre_3d_runup * 100
        md(f"Событий с дневным pre-3d на той же бирже: {len(dec)}")
        md(f"- Медианный набег за 3 дня до анонса: **{pre.median():+.2f}%**")
        md(f"- из них за последние 3 часа ДО публикации: **{meds['ret_m180_0']:+.2f}%**")
        md(f"- после публикации за 3 часа: **{meds['ret_p3h']:+.2f}%**, "
           f"в т.ч. за первую минуту: **{meds['ret_p1m']:+.2f}%**")
        pos = dec[dec.pre_3d_runup > 0.01]
        if len(pos) >= 10:
            share = (pos.ret_m180_0.clip(lower=0) / pos.pre_3d_runup).median() * 100
            md(f"- у событий с набегом >1% (N={len(pos)}) медианная доля набега, "
               f"сделанного в последние 3ч до анонса: {share:.0f}%")

    # --- 7. вердикт ----------------------------------------------------------
    md("\n## Вердикт: утечка vs шок\n")
    leak, shock = meds["ret_m180_0"], meds["ret_p3h"]
    verdict = ("ШОК доминирует: рынок узнаёт о листинге из анонса"
               if shock > leak else
               "УТЕЧКА доминирует: цена набегает ДО публикации")
    md(f"−3ч→0: {leak:+.2f}% vs 0→+3ч: {shock:+.2f}% (медианы) -> **{verdict}**")

    # --- 8. график -----------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Serif", "figure.facecolor": "white",
        "axes.facecolor": "white", "axes.edgecolor": "#444444",
        "axes.labelcolor": "#111111", "text.color": "#111111",
        "xtick.color": "#333333", "ytick.color": "#333333",
        "font.size": 11, "axes.grid": True, "grid.color": "#dddddd",
        "grid.linewidth": 0.6,
    })
    RED, BLUE = "#c0392b", "#2471a3"
    grid = np.arange(-180, 181)
    curves = [r["_curve"] for r in recs if isinstance(r.get("_curve"), dict)]
    mat = np.array([[c.get(int(g), np.nan) for g in grid] for c in curves], dtype=float)
    med = np.nanmedian(mat, axis=0) * 100
    q25 = np.nanpercentile(mat, 25, axis=0) * 100
    q75 = np.nanpercentile(mat, 75, axis=0) * 100
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.fill_between(grid, q25, q75, color=BLUE, alpha=0.18, label="IQR (25–75%)")
    ax.plot(grid, med, color=BLUE, lw=1.8,
            label=f"Median cumulative return (N={mat.shape[0]} events)")
    ax.axvline(0, color=RED, lw=1.2, ls="--")
    ax.axhline(0, color="#888888", lw=0.7)
    for h in (1, 5, 15, 60, 180):
        ax.plot(h, med[grid == h][0], "o", color=RED, ms=4, zorder=5)
    ax.text(2, ax.get_ylim()[0], "announcement", color=RED, fontsize=9,
            rotation=90, va="bottom")
    ax.set_xlim(-180, 180)
    ax.set_xticks([-180, -120, -60, 0, 1, 15, 60, 120, 180])
    ax.set_xlabel("Minutes relative to Binance listing announcement")
    ax.set_ylabel("Return vs announcement price, %")
    ax.set_title("Minute-level price shock of Binance listing announcements\n"
                 "(tokens already trading on Coinbase/Bybit; aligned at t=0)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    (ROOT / "charts").mkdir(exist_ok=True)
    fig.savefig(ROOT / "charts" / "announcement_shock_minutes.png", dpi=300)
    plt.close(fig)
    print("saved charts/announcement_shock_minutes.png", flush=True)

    # --- 9. отчёт --------------------------------------------------------------
    hdr = ["# Minute-level announcement shock on other venues",
           "",
           "Данные: [DATA] Coinbase Exchange API (granularity=60) и Bybit v5 (interval=1),",
           "окно ±3ч вокруг announce_ts из data/announcement_dates.csv (468 событий).",
           "Приоритет Coinbase (death-inclusive), фолбэк Bybit. Пустые бакеты Coinbase",
           "опускаются API -> на тонких рынках p0 = ближайший предыдущий бар (p0_gap_min).",
           "Конвенции: форвард-цель = close последнего бара с open <= цели; бар старше",
           "30 мин от цели -> NaN (флаг thin). Кэш сырых баров: data/announce_shock_cache/.",
           ""]
    (ROOT / "paper" / "announcement_shock.md").write_text("\n".join(hdr + lines))
    print(f"OK -> paper/announcement_shock.md ({time.time()-t_start:.0f}с)", flush=True)


if __name__ == "__main__":
    main()
