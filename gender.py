"""
Who a clothing deal is for: "Men's", "Women's", "Kids", or "Everyone" (unisex items,
storewide sales, brands that sell to both). Shared by the feed scorer and the brand-store scanner.

Order of evidence:
  1. explicit words in the title (men's / women’s / kids / unisex)
  2. garment words that imply an audience (dress, skirt set, bra -> Women's; boxer briefs, tuxedo -> Men's)
  3. product tags / type from the retailer (brand stores)
  4. the brand's audience (Summersalt -> Women's, Todd Snyder -> Men's, Comfrt -> Everyone)
  5. the description, if it names exactly one audience (both named -> Everyone)
  6. storewide sales with no specific garment in the title -> Everyone
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
        tm, tw = bool(MEN.search(tags)), bool(WOMEN.search(tags))
        if UNISEX.search(tags) or (tm and tw):
            return ["Everyone"]
        if tm:
            return ["Men's"]
        if tw:
            return ["Women's"]
        if KIDS.search(tags):
            return ["Kids"]
    aud = BR.audience_for(brands or [], store)
    if aud:
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
    if not has_garment and STOREWIDE.search(title):
        return ["Everyone"]
    return []
