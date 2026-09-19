#!/usr/bin/env bash
# build_cjsj.sh — one-entry verification that the committed data artifacts
# reproduce the paper's headline numbers. Reads CSVs only, no network.
# Usage: ./build_cjsj.sh   (override interpreter with PYTHON=/path/to/python)
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"

"$PYTHON" - <<'EOF'
import re
import sys

import pandas as pd

fails = []

def check(name, got, want, tol=None):
    if tol is not None:
        ok = abs(got - want) <= tol
        detail = f"got {got:+.2f}, want {want:+.2f} (±{tol})"
    else:
        ok = got == want
        detail = f"got {got}, want {want}"
    print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        fails.append(name)

# --- 1. Panel funnel: calendar -> 470 events -------------------------------
print("1. Listing calendar funnel")
cal = pd.read_csv("data/listing_calendar_binance.csv")
check("calendar rows", len(cal), 3682)
usdt = cal[cal.symbol.str.endswith("USDT") & (cal.first_month >= "2021-01")]
check("USDT first_month>=2021-01", len(usdt), 472)
enr = pd.read_csv("data/listing_events_enriched.csv")
check("enriched panel rows", len(enr), 470)
# the funnel minus the panel must be exactly the two leveraged tokens;
# JUPUSDT/SYRUPUSDT end in "UPUSDT" but are regular tokens and belong in the panel
check("funnel minus panel == leveraged tokens",
      sorted(set(usdt.symbol) - set(enr.symbol)),
      ["1INCHDOWNUSDT", "1INCHUPUSDT"])
check("panel is a subset of the funnel", set(enr.symbol) <= set(usdt.symbol), True)

# --- 2. Table II medians from the enriched panel ---------------------------
print("2. Table II medians (%)")
cols = ["pop_day0", "fwd_1", "fwd_7", "fwd_30"]
want_med = {"pop_day0": 28.06, "fwd_1": -4.45, "fwd_7": -11.45, "fwd_30": -21.53}
want_pos = {"pop_day0": 79.0, "fwd_1": 33.0, "fwd_7": 29.0, "fwd_30": 29.0}
med = enr[cols].median() * 100
pos = (enr[cols] > 0).mean() * 100
for c in cols:
    check(f"median {c}", round(med[c], 2), want_med[c])
    check(f"%positive {c}", round(pos[c], 0), want_pos[c], tol=0.5)

# --- 3. Funding sweep summary ----------------------------------------------
print("3. Funding sweep")
fs = pd.read_csv("data/funding_sweep.csv")
w1 = fs[fs.n_funding_w1 > 0]
check("names with week-1 funding", len(w1), 209)
check("median week-1 funding sum (%)", round(w1.sum_funding_w1.median() * 100, 2), -0.36)
check("shortable from day 0", int((fs.spot_to_perp_lag_d <= 0).sum()), 80)
check("shortable within week 1", int((fs.spot_to_perp_lag_d < 7).sum()), 210)

# --- 4. Announcement coverage ----------------------------------------------
print("4. Announcement coverage")
ann = pd.read_csv("data/announcement_dates.csv")
check("announcement rows", len(ann), 468)
check("unique symbols", ann.symbol.nunique(), 468)
check("panel symbols covered", len(set(ann.symbol) & set(enr.symbol)), 468)

if fails:
    print(f"\n{len(fails)} CHECK(S) FAILED: {', '.join(fails)}")
    sys.exit(1)
print("\nALL CHECKS PASSED")
EOF
