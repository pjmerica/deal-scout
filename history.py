"""
Run-to-run memory. On GitHub Actions the previous history.json is downloaded from
the live Pages site (no commits needed); locally it's read from site/history.json.

Per deal key it keeps: first/last seen, last price, lowest price, the first "original"
(compare-at) price, and a short price series (one point per change). That powers:
  NEW           appeared since the previous run (never items from the baseline run)
  price_drop    cheaper than at the last check
  tracked_low   below every price recorded (after 24 h of tracking)
  Fake-sale detector (retailer-verified brand-store prices only):
  orig_raised   the "original" price went up since we first saw it (inflate-then-discount)
  was_cheaper   the price was lower at some point in the last 14 days
Per brand store: when its sitewide promo first appeared.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from feeds import fetch, normalize_link
from models import NOW, Item

DEFAULT_URL = "https://pjmerica.github.io/deal-scout/history.json"
KEEP_DAYS = 30
NEW_HOURS = 12
SERIES_MAX = 30
LOOKBACK_DAYS = 14


def load(local: Path) -> dict:
    url = os.environ.get("HISTORY_URL", DEFAULT_URL)
    data = None
    if os.environ.get("GITHUB_ACTIONS") or not local.exists():
        raw = fetch(url, retries=1)
        if raw:
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
    if data is None and local.exists():
        try:
            data = json.loads(local.read_text(encoding="utf-8"))
        except ValueError:
            data = None
    data = data or {}
    data.setdefault("items", {})
    data.setdefault("promos", {})
    data.setdefault("runs", [])
    return data


def key_for(it: Item) -> str:
    if it.history_key:
        return it.history_key
    if it.thread_id:
        return f"sd:{it.thread_id}"
    return normalize_link(it.link)[:200]


def _ago(iso: str) -> float:
    try:
        return (NOW - datetime.fromisoformat(iso)).total_seconds() / 3600
    except ValueError:
        return 1e9


def _day(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso)
        return f"{d:%b} {d.day}"
    except ValueError:
        return "earlier"


def _recent(first_iso: str, hist: dict) -> bool:
    """True if first seen in the previous run (but not the baseline run that seeded history)."""
    runs = hist["runs"]
    if len(runs) < 2:
        return False
    return first_iso >= runs[-1] and first_iso != runs[0] and _ago(first_iso) <= NEW_HOURS


def apply(hist: dict, items: list[Item]) -> None:
    """Annotate items with history signals and update the history in place."""
    first_run = not hist["runs"]
    H = hist["items"]
    now = NOW.isoformat()
    for it in items:
        k = key_for(it)
        h = H.get(k)
        if h is None:
            H[k] = {"first": now, "last": now, "price": it.price, "min": it.price, "pct": it.pct_off,
                    "orig": it.orig_price, "series": [[now, it.price]] if it.price else []}
            it.first_seen = now
            if not first_run:
                it.is_new = True
            continue
        it.first_seen = h["first"]
        if _recent(h["first"], hist):
            it.is_new = True
        prev, low = h.get("price"), h.get("min")
        series = h.get("series") or ([[h["last"], prev]] if prev else [])
        verified = "retailer_verified" in it.flags

        # at a brand store, a price under 40% of the last one is a different variant or pack size, not a drop (see
        # same_variant below); deal-site headlines keep it (a price mistake can be 70% off)
        floor = 2.5 if verified else float("inf")
        if it.price and prev and prev - 0.5 > it.price >= prev / floor:
            it.flags.append("price_drop")
            it.reasons.append(f"Price dropped ${prev - it.price:,.0f} since last check")
        if it.price and low and low - 0.5 > it.price >= low / floor and _ago(h["first"]) >= 24:
            it.flags.append("tracked_low")
            it.reasons.append("Lowest price Deal Scout has recorded")

        # --- fake-sale detector (retailer data only: headline prices from deal sites are too noisy)
        if verified and it.price:
            orig0 = h.get("orig")
            # An "original" price that more than doubles or halves is a different variant, not inflation: Swiftwick's
            # Pursuit Crew read $22 (one pair) one run and $110 (a multi-pack) the next (2026-11-27). Real
            # inflate-then-discount is 10-50% (Comfrt $108 -> $150, Robert Graham $498 -> $598).
            same_variant = not (orig0 and it.orig_price and not 0.5 <= it.orig_price / orig0 <= 2)
            if same_variant and orig0 and it.orig_price and it.orig_price > orig0 * 1.05 + 1:
                it.flags.append("orig_raised")
                it.warnings.append(f"Original price raised ${orig0:,.0f} → ${it.orig_price:,.0f} since {_day(h['first'])}")
            window = [(t, p) for t, p in series if p and _ago(t) <= LOOKBACK_DAYS * 24]
            if window and same_variant:
                t_min, p_min = min(window, key=lambda x: x[1])
                if it.price > p_min * 1.03 + 0.5 and it.price <= p_min * 2.5:  # 2.5x: a pack-size switch, not a rise
                    it.flags.append("was_cheaper")
                    it.warnings.append(f"Was ${p_min:,.2f} on {_day(t_min)}, cheaper than now".replace(".00", ""))
            prices = [p for _, p in series if p] + [it.price]
            if len(series) >= 1 and _ago(h["first"]) >= 24:
                lo, hi = min(prices), max(prices)
                it.price_note = (f"Tracked since {_day(h['first'])}: ${lo:,.0f}–${hi:,.0f}" if hi - lo >= 1
                                 else f"Same price since {_day(h['first'])}")

        h["last"] = now
        if it.price:
            if not series or abs((series[-1][1] or 0) - it.price) >= 0.01:
                series.append([now, it.price])
            h["series"] = series[-SERIES_MAX:]
            h["price"] = it.price
            h["min"] = min(x for x in (low, it.price) if x)
        if it.orig_price and not h.get("orig"):
            h["orig"] = it.orig_price
        if it.pct_off:
            h["pct"] = max(h.get("pct") or 0, it.pct_off)


def flag_brand_picks(items: list[Item], summaries: list[dict]) -> None:
    """Carry the fake-sale warnings onto the Brands tab's top picks, which shopify.scan_store builds before history runs:
    Janji's "M's Rover Merino Half-Zip" was $64 on Nov 19 and $76.80 on Nov 26, shown as a top pick with no note.
    A flagged pick gets "warn" and moves after the clean ones."""
    flagged = {i.link: i for i in items if {"orig_raised", "was_cheaper"} & set(i.flags)}
    for s in summaries:
        top = s.get("top") or []
        for t in top:
            it = flagged.get(t.get("link"))
            if it:
                t["warn"] = next((w for w in it.warnings if w.startswith(("Was $", "Original price raised"))), "")
        top.sort(key=lambda t: bool(t.get("warn")))  # stable: keeps the %-off order within each group


def apply_promos(hist: dict, summaries: list[dict]) -> None:
    P = hist["promos"]
    for s in summaries:
        if not s.get("promo"):
            continue
        h = P.get(s["domain"])
        if not h or h.get("text") != s["promo"]:
            P[s["domain"]] = {"text": s["promo"], "first": NOW.isoformat()}
            s["promo_new"] = bool(hist["runs"])
        else:
            s["promo_new"] = _recent(h["first"], hist)


def save(hist: dict, path: Path) -> None:
    cutoff = NOW - timedelta(days=KEEP_DAYS)
    hist["items"] = {k: v for k, v in hist["items"].items()
                     if datetime.fromisoformat(v["last"]) >= cutoff}
    hist["runs"] = (hist["runs"] + [NOW.isoformat()])[-200:]
    path.write_text(json.dumps(hist, separators=(",", ":")), encoding="utf-8")
