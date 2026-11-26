#!/usr/bin/env python3
"""
Deal Scout: finds the best Black Friday deals (with a clothing bias) and writes a static site.
(Credit card offers, cash back and card news live in the separate card-scout repo.)

Pipeline
  1. Gather   RSS feeds + ~100 Slickdeals keyword searches, 80 Shopify brand stores
              (retailer-verified prices), optional Reddit.
  2. Process  cross-feed signals (Frontpage/Popular), de-dupe, classify, stacked-discount math.
  3. Remember compare with the previous run (new deals, price drops, tracked lows, rate changes).
  4. Score    explainable Deal Quality Score -> tiers -> diversified "best of" lists.
  5. Publish  site/index.html, deals.json, deals.csv, history.json

Usage:
    python deal_scout.py              # full run
    python deal_scout.py --quick      # fewer Slickdeals searches, skip brand stores
    python deal_scout.py --open       # open the report when done
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import os
import sys
import time
import webbrowser
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

import requests

import config as C
import history
import scoring
import shopify
import stacks as STACKS
from feeds import clean_text, fetch, parse_feed
from models import NOW, Item

HERE = Path(__file__).resolve().parent
SITE = HERE / "site"
TEMPLATE = HERE / "template.html"


# ---------------------------------------------------------------------------
def reddit_items() -> list[Item]:
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        return []
    ua = "deal-scout/1.0 (personal deal aggregator)"
    try:
        tok = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, secret),
                            data={"grant_type": "client_credentials"}, headers={"User-Agent": ua},
                            timeout=20).json()["access_token"]
    except Exception as ex:  # noqa: BLE001
        print(f"  ! reddit auth failed: {ex}")
        return []
    out = []
    for sub, kind, boost in C.REDDIT_SUBS:
        try:
            r = requests.get(f"https://oauth.reddit.com/r/{sub}/hot", params={"limit": 75, "raw_json": 1},
                             headers={"Authorization": f"bearer {tok}", "User-Agent": ua}, timeout=20)
            posts = r.json()["data"]["children"]
        except Exception:  # noqa: BLE001
            continue
        for p in posts:
            d = p["data"]
            if d.get("stickied"):
                continue
            pub = datetime.fromtimestamp(d["created_utc"], timezone.utc)
            img = d.get("thumbnail", "")
            out.append(Item(
                title=clean_text(d["title"], 300), link="https://www.reddit.com" + d["permalink"],
                source=f"r/{sub}", kind=kind, boost=boost, summary=clean_text(d.get("selftext", ""), 300),
                image=img if img.startswith("http") else "", votes=d.get("score"), comments=d.get("num_comments"),
                published=pub.isoformat(), age_days=(NOW - pub).total_seconds() / 86400,
                feed_tags=[d.get("link_flair_text") or ""]))
        print(f"  ✓ r/{sub}: {len(posts)}")
        time.sleep(1)
    return out



def sd_url(q: str) -> str:
    """Slickdeals search URL; multi-word queries are quoted for a phrase match ("free people" otherwise
    matched any post with both words)."""
    return C.SLICKDEALS_SEARCH_URL.format(q=quote_plus(f'"{q}"' if " " in q else q))


def gather_feeds(quick: bool) -> tuple[list[Item], list[dict]]:
    jobs = [(f["url"], f["name"], f["kind"], f.get("boost", 0)) for f in C.FEEDS]
    clothing_q = C.SLICKDEALS_CLOTHING_QUERIES[:15] if quick else C.SLICKDEALS_CLOTHING_QUERIES
    general_q = C.SLICKDEALS_GENERAL_QUERIES[:6] if quick else C.SLICKDEALS_GENERAL_QUERIES
    for q in clothing_q + general_q:
        jobs.append((sd_url(q), f"Slickdeals: {q}", "deal", 0))

    items, status = [], []

    def run(job):
        url, name, kind, boost = job
        content = fetch(url)
        if content is None:
            return name, url, kind, None
        try:
            return name, url, kind, parse_feed(content, name, kind, boost)
        except Exception as ex:  # noqa: BLE001
            print(f"  ! parse error {name}: {ex}")
            return name, url, kind, None

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for name, url, kind, res in ex.map(run, jobs):
            ok = res is not None
            status.append({"name": name, "url": url, "kind": kind, "ok": ok, "count": len(res or [])})
            if not ok:
                print(f"  ✗ {name}")
            if res:
                items.extend(res)
    r_items = reddit_items()
    if r_items:
        items.extend(r_items)
        status.append({"name": "Reddit", "url": "https://reddit.com", "kind": "deal", "ok": True, "count": len(r_items)})
    else:
        status.append({"name": "Reddit (needs API keys)", "url": "https://www.reddit.com/prefs/apps",
                       "kind": "deal", "ok": False, "count": 0})
    print(f"  feeds: {len(items)} items from {sum(s['ok'] for s in status)}/{len(status)}")
    return items, status


TRACKING = re.compile(r"^(?:utm_|iref$|ref$|ref_$|cmpid$|cid$|clickid$|affid$|mc_)", re.I)


def strip_tracking(url: str) -> str:
    """Drop analytics query params (utm_*, iref...) but keep the host exactly as given."""
    try:
        p = urlsplit(url)
    except ValueError:
        return url
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not TRACKING.match(k)]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))


# ---------------------------------------------------------------------------
def write_outputs(items, status, brand_sales, hist, stack_data) -> Path:
    SITE.mkdir(exist_ok=True)
    deals = [i for i in items if i.kind == "deal"]
    arts = [i for i in items if i.kind == "article"]
    # Page weight: low-scoring non-clothing deals are dropped (they never surface), clothing is all kept.
    deals = [i for i in deals if i.is_clothing or i.watch or i.score >= C.MIN_NONCLOTHING_SCORE]
    keep = scoring.pick_for_page(deals) + arts[:120]
    keep.sort(key=lambda x: -x.score)

    DROP = {"boost", "feed_tags", "history_key", "thread_id", "comments", "store_median", "published",
            "stack_pts"}

    def slim(it: Item) -> dict:
        """Only what the page uses, without empty/default values (the page fills defaults back in)."""
        d = {}
        for k, v in asdict(it).items():
            if k in DROP or v is None or v is False or v == "" or v == [] or (k == "variants" and v == 1):
                continue
            d[k] = v
        if it.source.startswith("Brand store"):
            d.pop("summary", None)  # boilerplate for brand-store items
        elif d.get("summary"):
            d["summary"] = d["summary"][:200]
        if len(it.sources) <= 1:
            d.pop("sources", None)
        d["link"] = strip_tracking(it.link)
        d["age_days"] = round(it.age_days, 2)
        for k in ("expires", "first_seen"):  # UTC to the minute is plenty ("2026-11-30T04:59"; the page adds Z)
            if d.get(k):
                d[k] = d[k][:16]
        return d

    for s in brand_sales:
        s["strength"] = round(
            (s["promo_pct"] * (0.75 if s.get("promo_up_to") else 1.0)) * 0.6
            + s["median_pct"] * 0.6 * min(1.0, s["on_sale"] / 10)  # a 1-item "sale" isn't a sale
            + (s["on_sale"] > 0) * min(10, s["on_sale"] / 10) + (12 if s["premium"] else 0)
            + max(0, max(s["median_pct"], s["promo_pct"]) - s["baseline"]) * 0.4, 1)
    brand_sales.sort(key=lambda s: -s["strength"])

    data = {
        "generated": NOW.isoformat(),
        "counts": {
            "total": len(keep),
            "clothing": sum(1 for i in keep if i.is_clothing and i.kind == "deal"),
            "deals": len([i for i in keep if i.kind == "deal"]),
            "articles": len(arts[:200]),
            "brands": len(brand_sales), "brand_items": sum(s["on_sale"] for s in brand_sales),
            "new": sum(1 for i in keep if i.is_new),
            "sources_ok": sum(1 for s in status if s["ok"]), "sources_total": len(status),
            "runs_tracked": len(hist.get("runs", [])),
            "stacked": sum(1 for i in keep if i.stack), "stack_stores": len(stack_data),
            "fake_sale_flags": sum(1 for i in keep if {"orig_raised", "was_cheaper"} & set(i.flags)),
            "with_codes": sum(1 for i in keep if i.codes),
        },
        "items": [slim(i) for i in keep],
        "stacks": {k: v for k, v in stack_data.items() if any(i.stack == k for i in keep)
                   or any(s.get("stack") == k for s in brand_sales)},
        "brand_sales": brand_sales,
        "sources": status,
        "card_scout_url": C.CARD_SCOUT_URL,
        "clothing_multiplier": C.CLOTHING_MULTIPLIER,
        # items first seen in the first run were already up then: the page says "since at least" that day
        "tracking_since": (hist.get("runs") or [NOW.isoformat()])[0][:16],
        "watch_labels": [label for label, _ in C.WATCH],
        "watch_subs": {label: [name for name, _ in subs] for label, subs in C.WATCH_SUB.items()},
    }
    (SITE / "deals.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    cols = ["score", "tier", "kind", "category", "is_clothing", "title", "store", "price", "orig_price", "pct_off",
            "saved", "votes", "is_new", "is_bf", "clothing_tags", "gender", "brands",
            "reasons", "warnings", "codes", "price_note", "source", "published", "first_seen", "expires", "link"]
    with open(SITE / "deals.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in keep:
            d = asdict(i)
            w.writerow(["; ".join(d[c]) if isinstance(d[c], list) else d[c] for c in cols])

    page = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("/*__DATA__*/null", payload)
    out = SITE / "index.html"
    out.write_text(page, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    history.save(hist, SITE / "history.json")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="fewer Slickdeals searches, skip brand-store scan")
    ap.add_argument("--open", action="store_true", help="open the report in a browser when done")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    t0 = time.time()
    hist = history.load(SITE / "history.json")
    print(f"History: {len(hist['items'])} tracked items from {len(hist['runs'])} previous runs")
    print("Gathering (feeds and brand stores in parallel)…")
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        f_feeds = ex.submit(gather_feeds, args.quick)
        f_shop = ex.submit(lambda: ([], [], []) if args.quick else shopify.scan_all())
        feed_items, feed_status = f_feeds.result()
        shop_items, brand_sales, shop_status = f_shop.result()
    print(f"  brand stores: {len(shop_items)} items kept from {len(brand_sales)} stores")
    stack_data, stack_status = STACKS.load(C.CARD_SCOUT_URL)
    print(f"  card scout stack data: {len(stack_data)} stores")
    status = feed_status + shop_status + [stack_status]

    items = scoring.process(feed_items + shop_items)
    history.apply(hist, items)
    history.apply_promos(hist, brand_sales)
    STACKS.apply(stack_data, items, brand_sales)
    scoring.score_all(items)
    out = write_outputs(items, status, brand_sales, hist, stack_data)

    deals = [x for x in items if x.kind == "deal"]
    print(f"\nKept {len(items)} items ({sum(i.is_clothing for i in deals)} clothing deals) in {time.time() - t0:.0f}s")
    print("\nBest overall (diversified):")
    for i in scoring.diversify(deals, 15):
        print(f"  {i.score:6.1f} {i.tier[:5]:5} {i.title[:85]}\n{'':14}↳ {' · '.join(i.reasons[:4])}")
    print("\nStrongest brand sales:")
    for s in brand_sales[:8]:
        print(f"  {s['strength']:5.1f}  {s['store']}: {s['on_sale']} items, median {s['median_pct']}% | {s['promo'][:60]}")
    print(f"\nReport: {out}")
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
