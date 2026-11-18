"""
Run-to-run memory. On GitHub Actions the previous history.json is downloaded from
the live Pages site (no commits needed); locally it's read from site/history.json.

Tracks, per deal key: first seen, last price, lowest price seen. Per brand store: when its sitewide promo first appeared.
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


def _recent(first_iso: str, hist: dict) -> bool:
    """True if first seen in the previous run (but not the baseline run that seeded history)."""
    runs = hist["runs"]
    if len(runs) < 2:
        return False
    return first_iso >= runs[-1] and first_iso != runs[0] and _ago(first_iso) <= NEW_HOURS


def apply(hist: dict, items: list[Item]) -> None:
    """Annotate items with history signals and update the history in place.
    NEW = appeared in this run or the previous one (never items from the baseline run)."""
    first_run = not hist["runs"]
    H = hist["items"]
    for it in items:
        k = key_for(it)
        h = H.get(k)
        if h is None:
            H[k] = {"first": NOW.isoformat(), "last": NOW.isoformat(), "price": it.price, "min": it.price,
                    "pct": it.pct_off}
            if not first_run:
                it.is_new = True
            continue
        if _recent(h["first"], hist):
            it.is_new = True
        prev, low = h.get("price"), h.get("min")
        if it.price and prev and it.price < prev - 0.5:
            it.flags.append("price_drop")
            it.reasons.append(f"Price dropped ${prev - it.price:,.0f} since last check")
        if it.price and low and it.price < low - 0.5 and _ago(h["first"]) >= 24:
            it.flags.append("tracked_low")
            it.reasons.append("Lowest price Deal Scout has recorded")
        h["last"] = NOW.isoformat()
        if it.price:
            h["price"] = it.price
            h["min"] = min(x for x in (low, it.price) if x)
        if it.pct_off:
            h["pct"] = max(h.get("pct") or 0, it.pct_off)


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
