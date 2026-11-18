"""
Scan clothing brands' Shopify storefronts directly.

For each store we read sale collections via the public /products.json endpoint,
which includes every variant's price, compare-at price and availability. That
gives retailer-verified discounts and stock levels, unlike deal-site headlines.
We also read the homepage announcement bar for sitewide promos
("BLACK FRIDAY: 40% OFF EVERYTHING").
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import statistics
import time

from bs4 import BeautifulSoup

import brands as BR
import gender as G
from feeds import fetch, session
from models import NOW, Item



SKIP_TITLE = re.compile(r"gift ?card|e-?gift|shipping protection|\broute\b|warranty|insurance|donation|"
                        r"mystery|sample|swatch|test product|do not purchase", re.I)


EXACT_SALE = re.compile(r"^(?:sale|sales|shop-sale|all-sale|sale-all|on-sale|the-sale|sale-items|black-?friday|"
                        r"black-friday-sale|bfcm|bfcm-sale|cyber-?monday|cyber-week|holiday-sale|archive-sale|final-sale)$")
BAD_HANDLE = re.compile(r"wholesale|pre-?sale|non-sale|exclu|full-price|feed|google|gift|klaviyo|hidden|test|"
                        r"upsell|bundle-builder|quiz")
DEPT_WORDS = re.compile(r"accessor|bottom|top|shoe|bag|sock|hat|kid|boy|girl|baby|home|bra|underwear|swim|jewel|"
                        r"best-?seller|under-\d|\d+-off")


def _handle_score(h: str, year: int) -> float:
    if not h or BAD_HANDLE.search(h):
        return -1
    if EXACT_SALE.match(h):
        s = 100
    elif re.match(r"(?:black-?friday|bfcm|cyber)", h):
        s = 80
    elif re.search(r"(?:^|-)sale(?:$|-)", h):
        s = 60
    elif re.search(r"outlet|clearance|markdown|last-chance|archive|warehouse|seconds|final|deals", h):
        s = 40
    else:
        return -1
    years = [int(y) for y in re.findall(r"20\d\d", h)]
    if years and max(years) < year:
        s -= 70  # an old season's collection
    if DEPT_WORDS.search(h):
        s -= 25
    return s - 0.2 * len(h)


def pick_sale_handles(domain: str) -> list[str]:
    """One request to /collections.json, then rank sale-looking handles."""
    j = _get_json(f"https://{domain}/collections.json?limit=250")
    handles = [c.get("handle", "") for c in (j or {}).get("collections", [])]
    if not handles:  # collections.json blocked/throttled: fall back to common guesses
        return ["sale", "black-friday"]
    scored = sorted(((_handle_score(h, NOW.year), h) for h in set(handles)), reverse=True)
    return [h for s, h in scored if s > 20][:2]


def _get_json(url: str):
    raw = fetch(url, retries=1, timeout=25, max_wait=6)
    if not raw or not raw.lstrip().startswith(b"{"):
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _collection_products(domain: str, handle: str, pages: int) -> list[dict]:
    out = []
    for page in range(1, pages + 1):
        j = _get_json(f"https://{domain}/collections/{handle}/products.json?limit=250&page={page}")
        prods = (j or {}).get("products") or []
        out.extend(prods)
        if len(prods) < 250:
            break
    return out


def _all_products(domain: str, pages: int) -> list[dict]:
    out = []
    for page in range(1, pages + 1):
        j = _get_json(f"https://{domain}/products.json?limit=250&page={page}")
        prods = (j or {}).get("products") or []
        out.extend(prods)
        if len(prods) < 250:
            break
    return out


PROMO_RE = re.compile(r"(up to\s+|extra\s+|take\s+)?(\d{1,2})\s?%\s*off", re.I)
PROMO_GOOD = re.compile(r"black friday|cyber|sitewide|site-wide|site wide|storewide|everything|entire|"
                        r"all (?:styles|orders|items|full[- ]price)|early access|holiday|sale|\bbf\b|bfcm", re.I)
PROMO_BAD = re.compile(r"first (?:order|purchase)|sign ?up|subscribe|e-?mail|newsletter|\btext\b|\bsms\b|"
                       r"join|refer|welcome|app\b|military|student|teacher|nurse|first responder|next order|"
                       r"your next|recycl|trade-?in|shop by|discounted price|regular price|sale price|"
                       r"\b0% off|\d+% off \d+% off|in the loop|saving \$|\$\d+\.\d\d \d+% off", re.I)
TRAILING_NAV = re.compile(r"\s+(?:shop (?:women|men|now|kids|all|the sale|early access)|terms\*?|see details)\b.*$", re.I)


def _tidy(snippet: str) -> str:
    m = re.match(r"^(.{12,}?)\s+\1", snippet)  # "X X" repeated banner text
    if m:
        snippet = m.group(1)
    return TRAILING_NAV.sub("", snippet).strip(" ,.-|*—–")
JUNK_PREFIX = re.compile(r"^.*?(?:skip to (?:main )?content|continue to checkout|your cart is empty|"
                         r"cart \(\s*\d+\s*\)|enable accessibility)\s*", re.I)


def detect_promo(domain: str) -> tuple[str, int, bool]:
    """Return (snippet, pct, is_up_to) for the strongest sitewide-looking promo on the homepage."""
    try:
        with session.get(f"https://{domain}/", timeout=20, stream=True) as r:
            if r.status_code != 200:
                return "", 0, False
            buf = b""
            for chunk in r.iter_content(32768):
                buf += chunk
                if len(buf) > 900_000:
                    break
    except Exception:  # noqa: BLE001
        return "", 0, False
    html = buf.decode("utf-8", errors="replace")
    html = re.sub(r"<(script|style|svg|noscript|template)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    soup = BeautifulSoup(html, "lxml")
    best = ("", 0, False, 0)
    seen = set()
    # Announcement bars and hero banners are short elements; read the smallest element
    # around each "% off" instead of a fixed window of page text (which drags in nav junk).
    for node in soup.find_all(string=PROMO_RE):
        el, snippet = node.parent, str(node)
        for _ in range(3):
            if el is None or el.name in ("body", "html", "main", "header", "nav", "footer"):
                break
            t = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
            if len(t) > 150:
                break
            snippet, el = t, el.parent
        snippet = re.sub(r"\s+", " ", snippet.replace("\xa0", " ").replace("&nbsp", " ")).strip(" ,.-|*")
        if not snippet or snippet in seen or len(snippet) > 150:
            continue
        seen.add(snippet)
        if PROMO_BAD.search(snippet) or not PROMO_GOOD.search(snippet):
            continue
        for m in PROMO_RE.finditer(snippet):
            pct = int(m.group(2))
            if pct < 10:
                continue
            up_to = (m.group(1) or "").strip().lower() == "up to"
            sitewide = bool(re.search(r"sitewide|site-wide|site wide|everything|storewide|entire|all orders", snippet, re.I))
            event = bool(re.search(r"black friday|cyber|bfcm|early access", snippet, re.I))
            strength = pct * (0.75 if up_to else 1.0) + 15 * sitewide + 8 * event
            if strength > best[3]:
                best = (_tidy(JUNK_PREFIX.sub("", snippet)), pct, up_to, strength)
    return best[0], best[1], best[2]


def promo_item(store: str, domain: str, url: str, promo: str, pct: int, up_to: bool) -> Item:
    eff = round(pct * 0.75) if up_to else pct
    it = Item(
        title=f"{store} sitewide: {promo}", link=url or f"https://{domain}/", source=f"Brand store: {store}",
        kind="deal", store=store, pct_off=eff, published=NOW.isoformat(), age_days=0.0,
        summary=f"Live promo on {store}'s homepage right now ({'up to ' if up_to else ''}{pct}% off).",
        history_key=f"{domain}:promo",
    )
    it.brands = [store]
    it.gender = [BR.audience_for([store]) or "Everyone"]
    it.flags.append("sitewide_promo")
    it.reasons.append("Live sitewide promo on the brand's homepage")
    return it


def _product_item(store: str, domain: str, p: dict) -> Item | None:
    title = p.get("title") or ""
    if SKIP_TITLE.search(title) or SKIP_TITLE.search(p.get("product_type") or ""):
        return None
    variants = p.get("variants") or []
    if not variants:
        return None
    avail = [v for v in variants if v.get("available")]
    if not avail:
        return None
    best = None
    for v in avail:
        try:
            price = float(v.get("price") or 0)
            comp = float(v.get("compare_at_price") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0 or comp <= price or comp > price * 12:
            continue
        pct = 1 - price / comp
        if best is None or pct > best[0] or (pct == best[0] and price < best[1]):
            best = (pct, price, comp)
    if best is None:
        return None
    pct, price, comp = best
    tags = p.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    tag_text = " ".join(t.replace("-", " ").replace("_", " ").replace(":", " ") for t in tags)
    gender = G.detect(title, "", [store], store, tags=f"{p.get('product_type', '')} {tag_text}")
    img = ""
    if p.get("images"):
        img = p["images"][0].get("src", "")
        if img and "?" not in img:
            img += "?width=400"
    it = Item(
        title=f"{store}: {title}", link=f"https://{domain}/products/{p.get('handle', '')}",
        source=f"Brand store: {store}", kind="deal", store=store, image=img,
        summary=f"{p.get('product_type') or 'Item'} on sale direct from {store}. "
                f"{len(avail)} of {len(variants)} sizes/colors in stock.",
        price=round(price, 2), orig_price=round(comp, 2), pct_off=round(pct * 100),
        saved=round(comp - price, 2), in_stock_ratio=round(len(avail) / len(variants), 2),
        published=NOW.isoformat(), age_days=0.0, feed_tags=[p.get("product_type") or ""] + tags[:6],
        history_key=f"{domain}:{p.get('handle', '')}",
    )
    it.brands = [store]
    it.gender = gender
    it.flags.append("retailer_verified")
    return it


def scan_store(store: str, domain: str, promo_cache: dict | None = None) -> tuple[list[Item], dict]:
    products: dict[int, dict] = {}
    used_handle = ""
    for n, h in enumerate(pick_sale_handles(domain)):
        prods = _collection_products(domain, h, pages=2 if n == 0 else 1)
        if prods:
            used_handle = used_handle or h
            for p in prods:
                products[p["id"]] = p
    items = [x for x in (_product_item(store, domain, p) for p in products.values()) if x]
    scanned = len(products)
    if len(items) < 25:
        allp = _all_products(domain, pages=1)
        scanned = max(scanned, len(allp))
        seen = {i.history_key for i in items}
        for p in allp:
            it = _product_item(store, domain, p)
            if it and it.history_key not in seen:
                items.append(it)
                seen.add(it.history_key)

    if promo_cache is not None and domain in promo_cache:
        promo, promo_pct, up_to = promo_cache[domain]
    else:
        promo, promo_pct, up_to = detect_promo(domain)
    pcts = [i.pct_off for i in items]
    median = statistics.median(pcts) if pcts else 0
    for i in items:
        i.store_median = median
    items.sort(key=lambda i: (-(i.pct_off or 0), -(i.orig_price or 0)))
    url = f"https://{domain}/collections/{used_handle}" if used_handle else f"https://{domain}/"
    audience = {k: sum(1 for i in items if k in i.gender) for k in ("Men's", "Women's", "Kids", "Everyone")}
    # Keep a balanced slice so a Men's or Women's view still has this brand's best items.
    keep, seen = [], set()
    for pool, n in ((items, 8), ([i for i in items if "Men's" in i.gender], 6),
                    ([i for i in items if "Women's" in i.gender], 6), ([i for i in items if "Kids" in i.gender], 2)):
        for i in pool[:n]:
            if i.history_key not in seen:
                seen.add(i.history_key)
                keep.append(i)
    keep.sort(key=lambda i: (-(i.pct_off or 0), -(i.orig_price or 0)))
    top = []
    for k in ("Men's", "Women's", "Kids", "Everyone", None):
        for i in [x for x in items if k is None or k in x.gender][:6]:
            if all(t["link"] != i.link for t in top):
                top.append({"title": i.title.split(": ", 1)[-1], "price": i.price, "orig": i.orig_price,
                            "pct": i.pct_off, "link": i.link, "image": i.image, "gender": i.gender})
    top.sort(key=lambda t: -(t["pct"] or 0))
    if promo and promo_pct >= 20:
        pi = promo_item(store, domain, url, promo, promo_pct, up_to)
        keep.insert(0, pi)
    summary = {
        "store": store, "domain": domain, "url": url,
        "scanned": scanned, "on_sale": len(pcts), "median_pct": round(median), "max_pct": max(pcts) if pcts else 0,
        "promo": promo, "promo_pct": promo_pct, "promo_up_to": up_to,
        "premium": BR.is_premium([store]), "baseline": BR.baseline_for([store]),
        "audience": audience, "brand_audience": BR.audience_for([store]) or "Everyone",
        "top": top[:24],
    }
    return keep, summary


def scan_all(workers: int = 8) -> tuple[list[Item], list[dict], list[dict]]:
    results: dict[str, tuple] = {}
    promo_cache: dict[str, tuple] = {}

    def run(kv, cache=None):
        store, domain = kv
        try:
            its, summ = scan_store(store, domain, cache)
            promo_cache[domain] = (summ["promo"], summ["promo_pct"], summ["promo_up_to"])
            return store, domain, its, summ
        except Exception as ex:  # noqa: BLE001
            print(f"  ! shopify {store}: {ex}")
            return store, domain, [], None

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for store, domain, its, summ in ex.map(run, BR.SHOPIFY_STORES.items()):
            results[store] = (domain, its, summ)

    # Second, slower pass for stores that returned nothing (usually HTTP 429 throttling)
    retry = [(s, d) for s, (d, its, summ) in results.items() if summ is None or summ["scanned"] == 0]
    if retry:
        print(f"  retrying {len(retry)} throttled brand stores slowly…")
        time.sleep(20)
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            for store, domain, its, summ in ex.map(lambda kv: run(kv, promo_cache), retry):
                if summ is not None and (results[store][2] is None or summ["scanned"] > 0):
                    results[store] = (domain, its, summ)

    items, summaries, status = [], [], []
    for store, (domain, its, summ) in results.items():
        ok = summ is not None and (summ["scanned"] > 0 or bool(summ["promo"]))
        status.append({"name": f"Brand store: {store}", "url": f"https://{domain}", "kind": "brand",
                       "ok": ok, "count": summ["on_sale"] if summ else 0})
        if summ is not None:
            summaries.append(summ)
            items.extend(its)
    print(f"  brand stores: {sum(1 for s in summaries if s['scanned'])} scanned, "
          f"{sum(1 for s in summaries if s['promo'])} with live promos")
    return items, summaries, status
