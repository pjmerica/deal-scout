"""
Classification + the Deal Quality Score.

Every deal's score is a sum of explainable components; each component that
fires adds a human-readable reason (shown in the UI under the deal):

  discount      effective discount (stacked codes compound), plus how far it beats
                the brand's normal everyday sale level ("excess discount")
  savings       absolute dollars saved (log-scaled)
  history       evidence the price is a low: "best price we could find by $X",
                "all-time low", camelcamelcamel drops, Deal Scout's own price history
  community     Slickdeals thumbs (log), vote velocity, Frontpage / Popular placement
  editorial     DealNews staff pick, found by several independent sources
  quality       premium brand that rarely discounts, retailer-verified price, stock depth
  catches       in-store/YMMV, membership, refurbished, rebates, sponsored, sold out
  freshness     exponential decay with age; small urgency bump if ending soon
  clothing      score x CLOTHING_MULTIPLIER + CLOTHING_FLAT_BONUS
"""
from __future__ import annotations

import math
import re
from datetime import datetime

import brands as BR
import config as C
import gender as G
from feeds import normalize_link, parse_date
from models import NOW, Item


def _wordre(terms):
    return re.compile(r"(?<![\w'])(?:" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
                      + r")(?![\w'])", re.I)


CLOTHING_CAT_RES = {cat: _wordre(terms) for cat, terms in C.CLOTHING_TERMS.items()}
CLOTHING_GENERIC_RE = _wordre(C.CLOTHING_GENERIC)
BRAND_RE = _wordre(C.CLOTHING_BRANDS + list(BR.SHOPIFY_STORES))
OTHER_BRAND_RE = _wordre([b for b in BR.BASELINE if len(b) > 3])
BRAND_CS = [(b, re.compile(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])")) for b in C.CLOTHING_BRANDS_CASE_SENSITIVE]
WEAK = set(C.WEAK_RETAILERS)
FALSE_POS_RE = re.compile("|".join(C.CLOTHING_FALSE_POSITIVE), re.I)
BF_RE = re.compile("|".join(C.BLACK_FRIDAY_TERMS), re.I)
SALE_RE = re.compile("|".join(C.SALE_TERMS), re.I)
GENDER_RES = {g: re.compile("|".join(p), re.I) for g, p in C.GENDER_TERMS.items()}
CATEGORY_RES = [(cat, _wordre(terms)) for cat, terms in C.CATEGORY_TERMS.items()]
NOT_A_DEAL = re.compile(r"giveaway|sweepstakes|\bcontest\b|win a |enter to win", re.I)

# --- pricing -----------------------------------------------------------------
PCT_RE = re.compile(r"(up to |extra |additional |take an extra |an extra |take |plus |\+ ?)?(\d{1,2})\s?%\s*off", re.I)
RANGE_RE = re.compile(r"(\d{1,2})\s?%?\s*(?:-|to|–)\s*(\d{1,2})\s?%\s*off", re.I)
DOWN_RE = re.compile(r"down (\d{1,2})(?:\.\d+)?%", re.I)
PRICE_RE = re.compile(r"\$\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)")
REG_RE = re.compile(r"(?:reg\.?|regularly|was|list(?: price)?|orig(?:inal(?:ly)?)?\.?|retail|msrp|value|compare at|"
                    r"down from|normally)\s*:?\s*\$\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)", re.I)
TO_FROM_RE = re.compile(r"(?:to|for|is|at)\s+\$(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)\s*,?\s*(?:down\s+)?from\s+\$(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)", re.I)
DOLLARS_OFF_RE = re.compile(r"(?:save|\bget)\s+\$(\d{2,4})|\$(\d{2,4})\s+off\b", re.I)
STORE_FROM_TITLE = re.compile(r"(?:\bat|@|\bvia|\bfrom)\s+([A-Z][\w'&.\- ]{1,30}?(?:\.com)?)(?:\s*(?:\(|\+|$|,| -|\|))")

HISTORY_PATTERNS = [
    (re.compile(r"price (?:mistake|error)|pricing error|glitch", re.I), 18, "Possible price mistake"),
    (re.compile(r"all[- ]time low|\bATL\b|lowest price ever|record low|historic(?:al)? low|lowest[- ]ever|"
                r"lowest price we(?:'ve| have) ever seen", re.I), 15, "All-time low price"),
    (re.compile(r"best price we could find by \$([\d,]+)", re.I), 13, "Best price DealNews could find, by ${}"),
    (re.compile(r"\ba low by \$([\d,]+)|lowest price (?:we could find|by \$)", re.I), 12, "Lowest price found"),
    (re.compile(r"new low|lowest (?:price )?in \d+ (?:days|months)|lowest price of the (?:year|season)|"
                r"best price (?:ever|of the year)|cheapest (?:ever|we've seen)", re.I), 10, "New low price"),
    (re.compile(r"match(?:es|ing)? (?:its |the )?(?:lowest|best)(?: price)?|lowest price we(?:'ve| have) seen", re.I), 7,
     "Matches lowest price"),
]

CATCHES = [
    (re.compile(r"expired|sold out|\bdead\b|out of stock|no longer available", re.I), -40, "May be expired / sold out"),
    (re.compile(r"refurbished|renewed|open[- ]box|pre-?owned|\bused\b(?! to)|grade [ab]\b", re.I), -8, "Refurbished / used"),
    (re.compile(r"\bymmv\b|targeted|in-?store only|\bB&M\b|select stores|in stores? only|in-store pickup only", re.I), -6,
     "In-store only / YMMV"),
    (re.compile(r"members? only|membership|\bmembers?:|costco|sam's club|\bbj's\b|must be a member", re.I), -3,
     "Membership required"),
    (re.compile(r"after (?:mail-?in )?rebate|\bMIR\b|rebate", re.I), -3, "Rebate required"),
    (re.compile(r"final sale", re.I), -2, "Final sale"),
]

GENERIC_HINT = re.compile(r"^\[?(?:prime|ac|lightning)\]?|^[A-Z]{5,}\b(?! [A-Z])")
AMAZONISH = re.compile(r"amazon|walmart|temu|ebay|woot", re.I)


def _money(s: str) -> float:
    return float(s.replace(",", ""))


def decay(age: float, half_life: float) -> float:
    return max(0.2, 0.5 ** (age / half_life))


# --- classification ---------------------------------------------------------
def classify(it: Item) -> None:
    text = f"{it.title} {it.summary[:180]}"
    title = it.title
    brand_store = it.source.startswith("Brand store")
    score, tags = 0, []
    for cat, rx in CLOTHING_CAT_RES.items():
        if rx.search(title) or (brand_store and rx.search(" ".join(it.feed_tags[:1]))):
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
    ft = " ".join(it.feed_tags).lower()
    if re.search(r"clothing|apparel|fashion|shoes|footwear|kids' clothes", ft) or "clothing" in it.source.lower():
        score += 2
    elif re.search(r"\b(?:wo)?mens\b|accessories", ft):
        score += 1
    if FALSE_POS_RE.search(title):
        score -= 6
    it.is_clothing = brand_store and not FALSE_POS_RE.search(title) or score >= 3
    it.clothing_tags = tags
    other = {m.group(0).lower() for m in OTHER_BRAND_RE.finditer(title)}
    if not brand_store:
        it.brands = sorted({b.title() for b in brands | other})[:6]
    if not it.gender:
        if it.is_clothing:
            it.gender = G.detect(title, it.summary, it.brands, it.store, has_garment=bool(tags))
        else:
            it.gender = [g for g, rx in GENDER_RES.items() if rx.search(title)]
    if it.is_clothing:
        it.category = "Clothing & Shoes"
    else:
        it.category = "Other"
        for cat, rx in CATEGORY_RES:
            if rx.search(title) or rx.search(ft):
                it.category = cat
                break
    it.is_bf = bool(BF_RE.search(f"{it.title} {it.summary[:200]}"))


def _promo_discount(text: str) -> tuple[float, list[int]]:
    """Base % and stackable extra %s found in one piece of text."""
    base, extras = 0.0, []
    for m in RANGE_RE.finditer(text):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo < hi:
            base = max(base, (lo + hi) / 2)
    for m in PCT_RE.finditer(text):
        mod = (m.group(1) or "").strip().lower()
        v = int(m.group(2))
        if mod in ("extra", "additional", "take an extra", "an extra", "plus", "+"):
            if v not in extras:
                extras.append(v)
        elif mod == "up to":
            base = max(base, v * 0.8)
        else:
            base = max(base, v)
    m = DOWN_RE.search(text)
    if m:
        base = max(base, int(m.group(1)))
    if re.search(r"\bbogo\b(?! 50)|buy one,? get one free|buy 1,? get 1 free", text, re.I):
        base = max(base, 50)
    elif re.search(r"buy 2,? get 1 free|b2g1", text, re.I):
        base = max(base, 33)
    elif re.search(r"bogo 50|buy one,? get one 50", text, re.I):
        base = max(base, 25)
    return base, extras


def extract_pricing(it: Item) -> None:
    if "retailer_verified" in it.flags or "sitewide_promo" in it.flags:
        return  # already exact
    title, summ = it.title, it.summary[:400]
    text = f"{title} {summ}"
    # Title first: the summary often lists several separate offers, and compounding them over-counts.
    base, extras = _promo_discount(title)
    if not base and not extras:
        base, extras = _promo_discount(summ)
    assumed = False
    if extras and not base and re.search(r"sale|clearance|markdown|reduced|outlet", text, re.I):
        base, assumed = 30, True  # "extra 50% off sale items": assume items already ~30% off
        it.reasons.append("Extra discount on already-reduced items")
    # explicit prices: a "to $X from $Y" pair beats the first $ in the title
    m = TO_FROM_RE.search(text)
    if m and _money(m.group(2)) > _money(m.group(1)) > 0:
        it.price, it.orig_price = _money(m.group(1)), _money(m.group(2))
    if it.price is None:
        m = PRICE_RE.search(title)
        if m:
            it.price = _money(m.group(1))
    if not it.orig_price:
        m = REG_RE.search(text)
        if m:
            it.orig_price = _money(m.group(1))
    m = re.search(r"down \d{1,2}(?:\.\d+)?% \(\$([\d,.]+)\)", title)
    if m:
        it.saved = _money(m.group(1))
    price_pct = 0.0
    if it.price and it.orig_price and it.orig_price > it.price > 0:
        price_pct = 100 * (1 - it.price / it.orig_price)
        it.saved = it.saved or round(it.orig_price - it.price, 2)
    elif it.orig_price and it.price and it.orig_price <= it.price:
        it.orig_price = None
    if not it.saved:
        m = DOLLARS_OFF_RE.search(text)
        if m:
            it.saved = float(m.group(1) or m.group(2))
    rem = 1 - base / 100
    for e in extras[:2]:
        rem *= 1 - e / 100
    promo_pct = 100 * (1 - rem)
    # An explicit final price already includes any codes; never stack extras on it.
    eff = price_pct if price_pct else promo_pct
    it.pct_off = min(int(round(eff)), 90) if eff >= 0.5 else None
    if extras and base and not assumed and not price_pct and it.pct_off:
        it.reasons.append(f"Stacked discount ≈ {it.pct_off}% off")
    if not it.store:
        m = STORE_FROM_TITLE.search(it.title)
        if m:
            it.store = m.group(1).strip(" .-")
        else:
            m = re.search(r"\b([A-Z][\w&'\-]+(?:\s[A-Z][\w&'\-]+)?)\s*\[\w[\w.\-]+\.\w+\]", it.summary)
            if m:
                it.store = m.group(1)


# --- deal score -------------------------------------------------------------
def score_deal(it: Item) -> None:
    text = f"{it.title} {it.summary[:400]}"
    R, W = it.reasons, it.warnings
    s = 8.0 + it.boost

    # discount
    generic = not it.brands and (bool(GENERIC_HINT.search(it.title)) or bool(AMAZONISH.search(it.store or "")))
    baseline = BR.baseline_for(it.brands, it.store, generic)
    eff = it.pct_off or 0
    excess = max(0, eff - baseline)
    s += 0.45 * eff + 0.35 * excess
    if eff >= 20:
        R.insert(0, f"{eff}% off")
    if excess >= 15 and (it.brands or it.store):
        who = (it.brands[0] if it.brands else it.store)
        R.append(f"{excess} pts deeper than {who}'s usual ~{baseline}% sale")
    if not it.brands and not it.source.startswith("Brand store") and it.kind == "deal":
        s -= 18
        W.append("Lesser-known brand")
    if it.store_median is not None and eff > it.store_median + 5:
        s += 0.2 * (eff - it.store_median)
        R.append(f"Deeper than this store's typical {it.store_median:.0f}% markdown")

    # savings
    if it.saved and it.saved > 0:
        s += min(14, 4 * math.log2(1 + it.saved / 15))
        if it.saved >= 50:
            R.append(f"Save ${it.saved:,.0f}")

    # price-history evidence
    best_h = 0
    for rx, pts, label in HISTORY_PATTERNS:
        m = rx.search(text)
        if m and pts > best_h:
            best_h = pts
            grp = next((g for g in m.groups() if g), "") if m.groups() else ""
            hist_label = label.format(grp) if "{}" in label else label
    if "camelcamelcamel" in it.source.lower():
        best_h = max(best_h, 10)
        hist_label = "Dropped vs Amazon price history"
    if best_h:
        s += best_h
        R.append(hist_label)
        it.flags.append("price_history")
    if "tracked_low" in it.flags:
        s += 10
    elif "price_drop" in it.flags:
        s += 6

    # community
    if it.votes is not None:
        v = it.votes
        if v > 0:
            s += min(55, 9 * math.log2(1 + v))
            hours = max(1.5, it.age_days * 24)
            vel = v / hours
            s += min(12, 4 * math.log2(1 + vel))
            if v >= 10:
                R.append(f"+{v} Slickdeals votes")
            if vel >= 3 and v >= 15:
                R.append(f"Rising fast ({vel:.0f} votes/hr)")
        else:
            s += max(-15, v * 2)
            if v < 0:
                W.append("Negative community votes")
    if "frontpage" in it.flags:
        s += 14
        R.append("Slickdeals Frontpage")
    elif "popular" in it.flags:
        s += 7
        R.append("Slickdeals Popular")
    if it.comments:
        s += min(8, 2 * math.log2(1 + it.comments))

    # editorial
    if it.staff_pick:
        s += 10
        R.append("DealNews staff pick")

    # quality
    if BR.is_premium(it.brands, it.store):
        s += 8
        R.append("Premium brand that rarely discounts")
    if "retailer_verified" in it.flags:
        s += 4
        R.append("Price verified on the retailer's own site")
        if it.in_stock_ratio is not None:
            if it.in_stock_ratio < 0.3:
                s -= 6
                W.append("Limited sizes left")
            elif it.in_stock_ratio >= 0.7:
                s += 2
    if it.is_bf:
        s += 5
    if re.search(r"free (?:s&h|shipping)", it.title, re.I):
        s += 2

    # catches
    for rx, pts, label in CATCHES:
        if rx.search(it.title) or (pts > -10 and rx.search(it.summary[:200])):
            s += pts
            W.append(label)
    if any(t.lower().startswith("sponsored") for t in it.feed_tags):
        s -= 12
        W.append("Sponsored post")
    if it.expires:
        d = parse_date(it.expires)
        if d:
            hrs = (d - NOW).total_seconds() / 3600
            if 0 < hrs <= 36:
                s += 3
                it.flags.append("ending")
                R.append("Ends soon")
    if it.kind == "article":
        s -= 6

    if "Lesser-known brand" in W:
        s *= 0.88  # part of a great deal is a product worth owning
    if it.is_clothing:
        s = s * C.CLOTHING_MULTIPLIER + C.CLOTHING_FLAT_BONUS
    it.score = round(s * decay(it.age_days, C.DEAL_HALF_LIFE_DAYS), 1)


# --- pipeline ---------------------------------------------------------------
def _title_key(t: str) -> str:
    t = re.sub(r"[^a-z0-9 ]", "", t.lower())
    return " ".join(t.split()[:10])


def cross_feed_flags(items: list[Item]) -> None:
    fp = {i.thread_id for i in items if i.thread_id and i.source == "Slickdeals Frontpage"}
    pop = {i.thread_id for i in items if i.thread_id and i.source == "Slickdeals Popular"}
    for i in items:
        if i.thread_id in fp:
            i.flags.append("frontpage")
        elif i.thread_id in pop:
            i.flags.append("popular")


def dedupe(items: list[Item]) -> list[Item]:
    groups: dict[str, Item] = {}
    order: list[Item] = []
    for it in items:
        keys = [k for k in (f"sd:{it.thread_id}" if it.thread_id else "", normalize_link(it.link),
                            _title_key(it.title)) if k]
        hit = next((groups[k] for k in keys if k in groups), None)
        if hit:
            if it.source not in hit.sources:
                hit.sources.append(it.source)
            hit.votes = hit.votes if hit.votes is not None else it.votes
            hit.image = hit.image or it.image
            hit.staff_pick = hit.staff_pick or it.staff_pick
            hit.boost = max(hit.boost, it.boost)
            hit.flags = sorted(set(hit.flags) | set(it.flags))
            if len(it.summary) > len(hit.summary):
                hit.summary = it.summary
            for k in keys:
                groups.setdefault(k, hit)
            continue
        it.sources = [it.source]
        for k in keys:
            groups[k] = it
        order.append(it)
    return order


def process(raw: list[Item]) -> list[Item]:
    cross_feed_flags(raw)
    items = dedupe(raw)
    kept = []
    for it in items:
        if it.published and it.age_days > C.MAX_AGE_DAYS:
            continue
        if NOT_A_DEAL.search(it.title):
            continue
        if it.expires:
            d = parse_date(it.expires)
            if d and d < NOW:
                continue
        classify(it)
        if it.kind == "article" and not SALE_RE.search(it.title):
            continue
        extract_pricing(it)
        if "camelcamelcamel" in it.source.lower() and (it.pct_off or 0) < 20:
            continue
        kept.append(it)
    return kept


def score_all(items: list[Item]) -> None:
    for it in items:
        score_deal(it)
        if len(it.sources) > 1:
            bump = min(15, 5 * (len(it.sources) - 1))
            it.score = round(it.score + bump, 1)
            it.reasons.append(f"Found on {len(it.sources)} sources")
        # tidy: unique reasons, keep order
        seen, rr = set(), []
        for r in it.reasons:
            if r not in seen:
                seen.add(r)
                rr.append(r)
        it.reasons = rr
        it.warnings = sorted(set(it.warnings))
    items.sort(key=lambda x: -x.score)
    deals = [i for i in items if i.kind == "deal"]
    n = len(deals)
    for rank, it in enumerate(deals):
        p = rank / max(1, n)
        it.tier = "Exceptional" if p < 0.03 else "Great" if p < 0.12 else "Good" if p < 0.35 else ""


def diversify(items: list[Item], n: int, per_store: int = 2, per_brand: int = 2) -> list[Item]:
    out, sc, bc, tk = [], {}, {}, set()
    for it in items:
        st = (it.store or "").lower()
        br = it.brands[0].lower() if it.brands else ""
        key = _title_key(re.split(r"\s[-–|]\s|\s\(", it.title)[0])[:40]  # colour variants = same product
        if (st and sc.get(st, 0) >= per_store) or (br and bc.get(br, 0) >= per_brand) or key in tk:
            continue
        out.append(it)
        tk.add(key)
        if st:
            sc[st] = sc.get(st, 0) + 1
        if br:
            bc[br] = bc.get(br, 0) + 1
        if len(out) >= n:
            break
    return out
