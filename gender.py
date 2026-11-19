"""
Who a clothing deal is for: "Men's", "Women's", "Kids", or "Everyone" (unisex items,
storewide sales, brands that sell to both). Shared by the feed scorer and the brand-store scanner.

Order of evidence:
  1. explicit words in the title (men's / women’s / kids / unisex)
  2. garment words that imply an audience (dress, skirt set, bra -> Women's; boxer briefs, tuxedo -> Men's)
  3. product tags / type from the retailer (brand stores)
  4. a single-audience brand (Summersalt -> Women's, Todd Snyder -> Men's); the store counts only for storewide sales
  5. the description, if it names exactly one audience (both named -> Everyone)
  6. a brand that sells to everyone (Nike, Comfrt, Macy's for a storewide sale) -> Everyone
  7. storewide sales with no specific garment in the title -> Everyone
"""
from __future__ import annotations

import re

import brands as BR

APOS = "['’]"
MEN = re.compile(rf"\bmen{APOS}?s?\b|\bmens\b|\bmenswear\b|\bfor men\b|\bboys?{APOS}?s?\b(?=.*\bmen)|\bmale\b|\bhis\b", re.I)
WOMEN = re.compile(rf"\bwomen{APOS}?s?\b|\bwomens\b|\bwomenswear\b|\bfor women\b|\bladies\b|\bfemale\b|\bhers\b|"
                   rf"\bmaternity\b", re.I)
KIDS = re.compile(rf"\bkids?{APOS}?s?\b|\bboys?{APOS}?\b|\bgirls?{APOS}?\b|\btoddlers?\b|\bbaby\b|\binfants?\b|"
                  rf"\bchildren{APOS}?s?\b|\byouth\b|\bbig kid\b|\blittle kid\b", re.I)
UNISEX = re.compile(rf"\bunisex\b|\bmen{APOS}?s?\s*(?:&|and|/|\+)\s*women{APOS}?s?\b|"
                    rf"\bwomen{APOS}?s?\s*(?:&|and|/|\+)\s*men{APOS}?s?\b|\bfamily\b|\bfor (?:him|her) (?:and|&|or) (?:him|her)\b", re.I)
WOMEN_HINT = re.compile(r"\bdress(?:es)?\b(?! shirts?\b| shoes?\b| pants?\b| socks?\b)|\bskirts?\b|\bblouses?\b|"
                        r"\bsports? bras?\b|\bbras?\b|\bbralettes?\b|\bmaxi\b|\bmidi\b|\bmini dress|\bgowns?\b|"
                        r"\brompers?\b|\bjumpsuits?\b|\bheels\b|\bbikinis?\b|\bone-piece\b|\bswimsuits?\b|\blingerie\b|"
                        r"\bcamisoles?\b|\bcami\b|\bleggings?\b|\bpant set\b|\bskirt set\b|\btank dress\b|\bkaftan\b|"
                        r"\bbodysuits?\b|\bpanties\b|\bbikini briefs?\b|\bthongs?\b(?! sandal)|\bmules?\b|\bballet flats?\b", re.I)
MEN_HINT = re.compile(r"\bboxer briefs?\b|\bboxers\b|\btrunks? \(\d|\btuxedo\b|\bneckties?\b|\bbow ties?\b|\bbeard\b|"
                      r"\bsport coat\b|\bchinos?\b(?=.*\bmen)|\bdress shirts?\b", re.I)
TAG_KEYED = re.compile(r"\b(?:gender|division|department|dept|sex|audience)\s+(men['’]?s?|women['’]?s?|kids?|boys?|girls?|unisex|all gender)\b", re.I)
UNISEX_TAG = re.compile(r"\bunisex\b|\ball genders?\b|\bgender neutral\b", re.I)
STOREWIDE = re.compile(r"sitewide|site-wide|storewide|everything|\bsale\b|% off|deals\b|clearance|outlet|"
                       r"\bsavings\b|black friday|cyber monday|& more|\bstyles\b", re.I)


def detect(title: str, summary: str = "", brands: list[str] | None = None, store: str = "",
           tags: str = "", has_garment: bool = True) -> list[str]:
    g: list[str] = []
    if KIDS.search(title):
        g.append("Kids")
    if UNISEX.search(title):
        return sorted(set(g) | {"Everyone"})
    if MEN.search(title):
        g.append("Men's")
    if WOMEN.search(title):
        g.append("Women's")
    if "Men's" in g and "Women's" in g:
        return sorted(set(g) | {"Everyone"})
    if g:
        return g
    if WOMEN_HINT.search(title):
        return ["Women's"]
    if MEN_HINT.search(title):
        return ["Men's"]
    if tags:
        # Structured retailer tags first ("gender:Men", "division:Womens", "department:Unisex")
        keyed = {m.group(1).lower().rstrip("s").replace("'", "") for m in TAG_KEYED.finditer(tags)}
        keyed = {{"men": "Men's", "women": "Women's", "kid": "Kids", "boy": "Kids", "girl": "Kids",
                  "unisex": "Everyone", "all gender": "Everyone"}[k] for k in keyed if k in
                 ("men", "women", "kid", "boy", "girl", "unisex", "all gender")}
        if keyed:
            if "Everyone" in keyed or {"Men's", "Women's"} <= keyed:
                return sorted((keyed - {"Men's", "Women's"}) | {"Everyone"})
            return sorted(keyed)
        tm, tw = bool(MEN.search(tags)), bool(WOMEN.search(tags))
        # free-text tags: "family" here is usually "color-family", so only explicit unisex words count
        if UNISEX_TAG.search(tags) or (tm and tw):
            return ["Everyone"]
        if tm:
            return ["Men's"]
        if tw:
            return ["Women's"]
        if KIDS.search(tags):
            return ["Kids"]
    # The store's audience only speaks for storewide sales: Macy's sells to everyone, but a sweater at Macy's
    # isn't unisex. A brand that sells to everyone is weaker evidence than a description naming one audience.
    aud = BR.audience_for(brands or [], "" if has_garment else store)
    if aud and aud != "Everyone":
        return [aud]
    if summary:
        s = summary[:260]
        sm, sw = bool(MEN.search(s)), bool(WOMEN.search(s))
        if UNISEX.search(s) or (sm and sw):
            return ["Everyone"]
        if sm:
            return ["Men's"]
        if sw:
            return ["Women's"]
    if aud:
        return [aud]
    if not has_garment and STOREWIDE.search(title):
        return ["Everyone"]
    return []
