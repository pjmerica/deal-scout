#!/usr/bin/env python3
"""
Deal Scout - scrapes Black Friday deals (biased toward clothing) and credit card
offers from dozens of RSS feeds, scores them, and writes a static site:

    site/index.html   interactive report (works on GitHub Pages)
    site/deals.json   all scored items
    site/deals.csv    spreadsheet-friendly export

Usage:
    python deal_scout.py              # full run
    python deal_scout.py --quick      # skip the long Slickdeals keyword sweep
    python deal_scout.py --open       # open the report when done
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import html
import json
import math
import os
import re
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

import config as C

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

HERE = Path(__file__).resolve().parent
SITE = HERE / "site"
TEMPLATE = HERE / "template.html"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Item:
    title: str
    link: str
    source: str
    kind: str                      # deal | article | card
    published: str = ""            # ISO timestamp
    age_days: float = 0.0
    summary: str = ""
    image: str = ""
    store: str = ""
    price: float | None = None
    orig_price: float | None = None
    pct_off: int | None = None
    votes: int | None = None
    comments: int | None = None
    staff_pick: bool = False
    feed_tags: list[str] = field(default_factory=list)
    # derived
    is_clothing: bool = False
    clothing_tags: list[str] = field(default_factory=list)
    gender: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    is_bf: bool = False
    card_category: str = ""
    bonus_value: int | None = None
    score: float = 0.0
    boost: float = 0.0
    sources: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
session = requests.Session()
session.headers.update({"User-Agent": BROWSER_UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})


def fetch(url: str, retries: int = 2) -> bytes | None:
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=25)
            if r.status_code == 200 and r.content:
                return r.content
            if r.status_code in (429, 503):
                time.sleep(2 + attempt * 3)
                continue
            return None
        except requests.RequestException:
            time.sleep(1 + attempt)
    return None


def clean_text(s: str, limit: int = 400) -> str:
    if not s:
        return ""
    txt = BeautifulSoup(s, "lxml").get_text(" ", strip=True) if "<" in s else s
    txt = html.unescape(re.sub(r"\s+", " ", txt)).strip()
    txt = re.sub(r"\[/?(?:LIST|\*|B|I|URL[^\]]*)\]", " ", txt)  # Slickdeals BBCode
    txt = re.sub(r"\s+", " ", txt).strip()
    return (txt[: limit - 1] + "…") if len(txt) > limit else txt


def parse_date(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def normalize_link(url: str) -> str:
    try:
        p = urlsplit(url)
        q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "iref", "ref"))]
        return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), urlencode(q), ""))
    except ValueError:
        return url


def first_img(htmlish: str) -> str:
    m = re.search(r"""<img[^>]+src=["']([^"']+)["']""", htmlish or "", re.I)
    if m and not m.group(1).endswith((".gif",)) and "pixel" not in m.group(1):
        return html.unescape(m.group(1))
    return ""


def child_text(node, *names) -> str:
    for n in names:
        el = node.find(n)
        if el is not None:
            t = el.get_text() if el.get_text() else ""
            if t.strip():
                return t
    return ""


def parse_feed(content: bytes, source: str, kind: str, boost: float) -> list[Item]:
    soup = BeautifulSoup(content, "xml")
    entries = soup.find_all("item") or soup.find_all("entry")
    out: list[Item] = []
    for e in entries:
        title = clean_text(child_text(e, "title"), 300)
        if not title:
            continue
        link = child_text(e, "link")
        if not link:
            l = e.find("link")
            link = l.get("href", "") if l is not None else ""
        link = link.strip()
        encoded = child_text(e, "encoded", "content")
        desc_raw = child_text(e, "description", "summary")
        pub = parse_date(child_text(e, "pubDate", "published", "updated", "date"))
        tags = [c.get_text(strip=True) for c in e.find_all("category") if c.get_text(strip=True)]

        image = ""
        for tag in ("thumbnail-image",):
            el = e.find(tag)
            if el is not None and el.get_text(strip=True):
                image = el.get_text(strip=True)
        if not image:
            for el in e.find_all(["content", "thumbnail"]):
                if el.get("url") and (el.get("medium") in (None, "image") or el.name == "thumbnail"):
                    image = el["url"]
                    break
        if not image:
            enc = e.find("enclosure")
            if enc is not None and "image" in (enc.get("type") or ""):
                image = enc.get("url", "")
        if not image:
            image = first_img(encoded) or first_img(desc_raw)

        it = Item(title=title, link=link, source=source, kind=kind, boost=boost,
                  summary=clean_text(desc_raw or encoded, 360), image=image, feed_tags=tags[:12])
        if pub:
            it.published = pub.isoformat()
            it.age_days = max(0.0, (NOW - pub).total_seconds() / 86400)

        # Slickdeals extras
        m = re.search(r"Thumb Score:\s*([+-]?\d+)", encoded or "")
        if m:
            it.votes = int(m.group(1))
        # DealNews extras
        r_el = e.find("retailer")
        if r_el is not None:
            it.store = r_el.get_text(strip=True)
        p_el = e.find("price")
        if p_el is not None:
            try:
                it.price = float(p_el.get_text(strip=True))
            except ValueError:
                pass
        sp = e.find("staffPick")
        if sp is not None and sp.get_text(strip=True).lower() == "true":
            it.staff_pick = True
        # WordPress comment counts (slash:comments)
        for c in e.find_all("comments"):
            t = c.get_text(strip=True)
            if t.isdigit():
                it.comments = int(t)
        out.append(it)
    return out


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


def gather(quick: bool) -> tuple[list[Item], list[dict]]:
    jobs = [(f["url"], f["name"], f["kind"], f.get("boost", 0)) for f in C.FEEDS]
    sd_queries = C.SLICKDEALS_GENERAL_QUERIES + C.SLICKDEALS_CARD_QUERIES
    if not quick:
        sd_queries = C.SLICKDEALS_CLOTHING_QUERIES + sd_queries
    else:
        sd_queries = C.SLICKDEALS_CLOTHING_QUERIES[:12] + sd_queries
    for q in sd_queries:
        kind = "card" if q in C.SLICKDEALS_CARD_QUERIES else "deal"
        jobs.append((C.SLICKDEALS_SEARCH_URL.format(q=quote_plus(q)), f"Slickdeals: {q}", kind, 0))

    items: list[Item] = []
    status: list[dict] = []

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

    # Slickdeals gets hammered by many queries: keep concurrency modest
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for name, url, kind, res in ex.map(run, jobs):
            ok = res is not None
            status.append({"name": name, "url": url, "kind": kind, "ok": ok, "count": len(res or [])})
            print(f"  {'✓' if ok else '✗'} {name}: {len(res or [])}")
            if res:
                items.extend(res)

    r_items = reddit_items()
    if r_items:
        items.extend(r_items)
        status.append({"name": "Reddit", "url": "https://reddit.com", "kind": "deal", "ok": True,
                       "count": len(r_items)})
    else:
        status.append({"name": "Reddit (needs API keys)", "url": "https://www.reddit.com/prefs/apps",
                       "kind": "deal", "ok": False, "count": 0})
    return items, status


# ---------------------------------------------------------------------------
# Classification & scoring
# ---------------------------------------------------------------------------
def _wordre(terms):
    return re.compile(r"(?<![\w'])(?:" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
                      + r")(?![\w'])", re.I)


CLOTHING_CAT_RES = {cat: _wordre(terms) for cat, terms in C.CLOTHING_TERMS.items()}
CLOTHING_GENERIC_RE = _wordre(C.CLOTHING_GENERIC)
BRAND_RE = _wordre(C.CLOTHING_BRANDS)
WEAK = set(C.WEAK_RETAILERS)
CARD_JUNK_RE = re.compile(C.CARD_JUNK, re.I)
AWARD_RE = re.compile(r"award|one-way|round-?trip|\bstays?\b|\bbook\b|redeem|\bfly\b|from [\d,]+k? (?:points|miles)", re.I)
BRAND_CS = [(b, re.compile(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])")) for b in C.CLOTHING_BRANDS_CASE_SENSITIVE]
FALSE_POS_RE = re.compile("|".join(C.CLOTHING_FALSE_POSITIVE), re.I)
BF_RE = re.compile("|".join(C.BLACK_FRIDAY_TERMS), re.I)
SALE_RE = re.compile("|".join(C.SALE_TERMS), re.I)
CARD_REL_RE = re.compile("|".join(C.CARD_RELEVANCE), re.I)
CARD_CAT_RES = [(name, re.compile("|".join(p), re.I)) for name, p in C.CARD_CATEGORIES]
CARD_HOT_RES = [(re.compile(p, re.I), pts) for p, pts in C.CARD_HOT_TERMS.items()]
CARD_DEAD_RE = re.compile(C.CARD_DEAD_TERMS, re.I)
GENDER_RES = {g: re.compile("|".join(p), re.I) for g, p in C.GENDER_TERMS.items()}

PCT_RE = re.compile(r"(up to |extra |additional |take )?(\d{1,2})\s?% off", re.I)
PRICE_RE = re.compile(r"\$\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)")
REG_RE = re.compile(r"(?:reg\.?|regularly|was|list|orig(?:inal)?\.?|retail|msrp|value)\s*:?\s*\$\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)", re.I)
POINTS_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{2,3}k|\d{2,3}K)\s*(?:bonus\s*)?(?:points|miles|pts|membership rewards|ultimate rewards|thankyou|avios)", re.I)
CASH_BONUS_RE = re.compile(r"\$(\d{2,4}(?:,\d{3})?)\s*(?:cash\s*)?(?:bonus|sign-?up|welcome)", re.I)
STORE_FROM_TITLE = re.compile(r"(?:\bat|@|\bvia|\bfrom)\s+([A-Z][\w'&.\- ]{1,30}?(?:\.com)?)(?:\s*(?:\(|\+|$|,| -|\|))")


def _money(s: str) -> float:
    return float(s.replace(",", ""))


def classify_clothing(it: Item) -> None:
    text = f"{it.title} {it.summary[:160]}"
    title = it.title
    score = 0
    tags = []
    for cat, rx in CLOTHING_CAT_RES.items():
        if rx.search(title):
            tags.append(cat)
            score += 3
        elif rx.search(text):
            score += 1
    brands = {m.group(0).strip().lower() for m in BRAND_RE.finditer(text)}
    for b, rx in BRAND_CS:
        if rx.search(text):
            exc = C.CASE_SENSITIVE_EXCLUDE.get(b)
            if exc and re.search(exc, text):
                continue
            brands.add(b.lower())
    strong = {b for b in brands if b not in WEAK}
    if strong:
        score += 3 if any(b in title.lower() for b in strong) else 1
    elif brands:
        score += 1
    if CLOTHING_GENERIC_RE.search(text):
        score += 2
    feed_tag_text = " ".join(it.feed_tags).lower()
    if re.search(r"clothing|apparel|fashion|shoes|footwear", feed_tag_text) or "clothing" in it.source.lower():
        score += 2
    elif re.search(r"\b(?:wo)?mens\b|accessories", feed_tag_text):
        score += 1
    if FALSE_POS_RE.search(title):
        score -= 6
    it.is_clothing = score >= 3
    it.clothing_tags = tags
    it.brands = sorted({b.title() for b in brands})[:6]
    it.gender = [g for g, rx in GENDER_RES.items() if rx.search(title)]


def extract_pricing(it: Item) -> None:
    text = f"{it.title} {it.summary[:300]}"
    best = 0
    for m in PCT_RE.finditer(text):
        v = int(m.group(2))
        mod = (m.group(1) or "").lower().strip()
        if mod == "up to":
            v = int(v * 0.85)
        best = max(best, v)
    if re.search(r"\bbogo\b|buy one,? get one free", text, re.I):
        best = max(best, 50)
    if it.price is None:
        m = PRICE_RE.search(it.title)
        if m:
            it.price = _money(m.group(1))
    m = REG_RE.search(text)
    if m:
        it.orig_price = _money(m.group(1))
        if it.price and it.orig_price > it.price > 0:
            best = max(best, round(100 * (1 - it.price / it.orig_price)))
    if re.search(r"\bfree\b(?! shipping)", it.title, re.I) and re.search(r"\$0(?:\.00)?\b|for free|\bfree\b", it.title, re.I) and best == 0:
        best = 0
    it.pct_off = min(best, 95) if best else None
    if not it.store:
        m = STORE_FROM_TITLE.search(it.title)
        if m:
            it.store = m.group(1).strip(" .-")
        else:
            m = re.search(r"\b([A-Z][\w&'\-]+(?:\s[A-Z][\w&'\-]+)?)\s*\[\w[\w.\-]+\.\w+\]", it.summary)
            if m:
                it.store = m.group(1)


def decay(age: float, half_life: float) -> float:
    return max(0.2, 0.5 ** (age / half_life))


def score_deal(it: Item) -> None:
    s = 10.0 + it.boost
    if it.pct_off:
        s += it.pct_off * 0.6
    if it.votes is not None:
        s += (9 * math.log2(1 + it.votes)) if it.votes > 0 else max(-15, it.votes * 2)
    if it.comments:
        s += 2 * math.log2(1 + it.comments)
    if it.staff_pick:
        s += 10
    if it.is_bf:
        s += 8
    if re.search(r"free shipping", it.title, re.I):
        s += 2
    if re.search(r"expired|sold out|\bdead\b|out of stock", it.title, re.I):
        s -= 30
    if it.kind == "article":
        s -= 5
    if it.is_clothing:
        s = s * C.CLOTHING_MULTIPLIER + C.CLOTHING_FLAT_BONUS
    it.score = round(s * decay(it.age_days, C.DEAL_HALF_LIFE_DAYS), 1)


def score_card(it: Item) -> None:
    text = f"{it.title} {it.summary[:300]}"
    s = 8.0 + it.boost
    val = 0
    for m in ([] if AWARD_RE.search(it.title) else POINTS_RE.finditer(it.title)):
        raw = m.group(1).lower().replace(",", "")
        pts = int(raw[:-1]) * 1000 if raw.endswith("k") else int(raw)
        val = max(val, int(pts * C.POINT_VALUE_CENTS / 100))
    for m in CASH_BONUS_RE.finditer(it.title):
        val = max(val, int(_money(m.group(1))))
    if val:
        it.bonus_value = val
        s += min(45, val / 25)
    for rx, pts in CARD_HOT_RES:
        if rx.search(text):
            s += pts
    if it.brands or it.is_clothing:
        s += C.CARD_CLOTHING_RETAILER_BONUS
    if it.comments:
        s += 3 * math.log2(1 + it.comments)
    if it.votes and it.votes > 0:
        s += 6 * math.log2(1 + it.votes)
    if CARD_DEAD_RE.search(it.title):
        s -= 30
    for name, rx in CARD_CAT_RES:
        if rx.search(it.title):
            it.card_category = name
            break
    if not it.card_category:
        it.card_category = "Card & Points News"
        s -= 6
    it.score = round(s * decay(it.age_days, C.CARD_HALF_LIFE_DAYS), 1)


def process(items: list[Item]) -> list[Item]:
    kept: list[Item] = []
    for it in items:
        if it.published and it.age_days > C.MAX_AGE_DAYS:
            continue
        classify_clothing(it)
        it.is_bf = bool(BF_RE.search(f"{it.title} {it.summary[:200]}"))
        if it.kind == "card":
            if not CARD_REL_RE.search(it.title) or CARD_JUNK_RE.search(it.title):
                continue
            score_card(it)
        else:
            if it.kind == "article" and not SALE_RE.search(it.title):
                continue
            extract_pricing(it)
            score_deal(it)
        kept.append(it)
    return dedupe(kept)


def _title_key(t: str) -> str:
    t = re.sub(r"[^a-z0-9 ]", "", t.lower())
    return " ".join(t.split()[:10])


def dedupe(items: list[Item]) -> list[Item]:
    by_key: dict[str, Item] = {}
    for it in sorted(items, key=lambda x: -x.score):
        keys = [normalize_link(it.link), _title_key(it.title)]
        hit = next((by_key[k] for k in keys if k in by_key), None)
        if hit:
            if it.source not in hit.sources:
                hit.sources.append(it.source)
            # merge useful fields
            hit.votes = hit.votes if hit.votes is not None else it.votes
            hit.image = hit.image or it.image
            continue
        it.sources = [it.source]
        for k in keys:
            by_key[k] = it
    uniq = {id(v): v for v in by_key.values()}.values()
    for it in uniq:  # small bump for deals found by multiple feeds
        if len(it.sources) > 1:
            it.score = round(it.score + 4 * (len(it.sources) - 1), 1)
    return sorted(uniq, key=lambda x: -x.score)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_outputs(items: list[Item], status: list[dict]) -> Path:
    SITE.mkdir(exist_ok=True)
    data = {
        "generated": NOW.isoformat(),
        "counts": {
            "total": len(items),
            "clothing": sum(1 for i in items if i.is_clothing and i.kind != "card"),
            "deals": sum(1 for i in items if i.kind == "deal"),
            "cards": sum(1 for i in items if i.kind == "card"),
            "articles": sum(1 for i in items if i.kind == "article"),
            "sources_ok": sum(1 for s in status if s["ok"]),
            "sources_total": len(status),
        },
        "items": [asdict(i) for i in items],
        "sources": status,
        "playbook": [{"title": t, "body": b} for t, b in C.CARD_PLAYBOOK],
    }
    (SITE / "deals.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    cols = ["score", "kind", "is_clothing", "title", "store", "price", "orig_price", "pct_off", "votes",
            "card_category", "bonus_value", "is_bf", "clothing_tags", "gender", "brands", "source", "published", "link"]
    with open(SITE / "deals.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in items:
            d = asdict(i)
            w.writerow([", ".join(d[c]) if isinstance(d[c], list) else d[c] for c in cols])

    page = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("/*__DATA__*/null", payload)
    out = SITE / "index.html"
    out.write_text(page, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="fewer Slickdeals keyword searches")
    ap.add_argument("--open", action="store_true", help="open the report in a browser when done")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    t0 = time.time()
    print("Fetching sources…")
    raw, status = gather(args.quick)
    print(f"\nFetched {len(raw)} raw items from {sum(s['ok'] for s in status)}/{len(status)} sources")
    items = process(raw)
    out = write_outputs(items, status)
    c = sum(1 for i in items if i.is_clothing and i.kind != "card")
    print(f"Kept {len(items)} unique items ({c} clothing, {sum(i.kind == 'card' for i in items)} card offers) "
          f"in {time.time() - t0:.0f}s")
    print("\nTop 10 clothing deals:")
    for i in [x for x in items if x.is_clothing and x.kind == "deal"][:10]:
        print(f"  {i.score:6.1f}  {i.title[:100]}")
    print("\nTop 8 card offers:")
    for i in [x for x in items if x.kind == "card"][:8]:
        print(f"  {i.score:6.1f}  [{i.card_category}] {i.title[:90]}")
    print(f"\nReport: {out}")
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
