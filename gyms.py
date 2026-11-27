"""
Gym membership offers straight from the gyms' own sites (added 2026-11-26; owner: "gym deals, especially ones in NYC",
then "ones with basketball facilities too").

Deal sites rarely post gym memberships, and news searches turn up gyms in other states, so each run reads the pages in
config.GYMS and keeps the offer line a gym is advertising ("Black Friday Sale | 50% off first two full months + $0 join
fee"), if any. An offer needs an occasion (Black Friday, holiday, New Year, "sale ends ...") AND terms ($0 down, % off,
free month, buy N get N...). Each one becomes a "Gym deals" item on the Watching list, tagged NYC and/or Basketball
courts from config.GYMS, with where-to-go on the card (Item.where).
"""
from __future__ import annotations

import concurrent.futures as cf
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

import config as C
import ends as ENDS
from feeds import session
from models import NOW, Item

OCCASION = re.compile(r"black friday|cyber (?:monday|week)|\bbfcm\b|holiday (?:sale|special|offer|deal|savings)|"
                      r"new year|resolution|sale ends|limited[- ]time (?:offer|only)", re.I)
TERMS = re.compile(r"\$\s?0\s*(?:down|join|enroll\w*|initiation|registration|due|to start)|\$\d+(?:\.\d\d)?\s*(?:down|to join)|"
                   r"join for \$|started for \$|\d{1,3}\s?% off|\bfree (?:months?|weeks?|class(?:es)?)\b|"
                   r"\b(?:months?|weeks?|class(?:es)?) free\b|buy \d+(?: classes)?,? get \d+|buy one,? get one|\bbogo\b|"
                   r"save (?:up to )?(?:\$\d+|\d+\s?%)|\$\d+ (?:credit|off)|\$\d+ towards?|waived|half off|"
                   r"no (?:enrollment|initiation|joining|join) fee", re.I)
BAD = re.compile(r"newsletter|subscribe|e-?mail|\bsms\b|text (?:me|us)|gift ?cards?", re.I)
CTA = re.compile(r"\s*(?:join (?:now|today)|join (?:&|and) save|sign up(?: (?:&|and) save| now)?|shop now|learn more|"
                 r"claim (?:now|yours(?: now)?|at your studio)|get started|book (?:now|a tour)|see details|"
                 r"find (?:a|your) (?:club|gym|location|studio)|terms (?:apply|(?:&|and) conditions)|[×›»|*])\s*[.!]?\s*$", re.I)
SKIP_PARENT = {"body", "html", "main", "header", "nav", "footer"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


END_HINT = re.compile(r"\bends?\b|\bexpires?\b|\bthrough\b|\buntil\b|\bby (?:" + "|".join(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]) + r")", re.I)
PROPER = re.compile(r"\b(black friday|cyber monday|cyber week|new year|thanksgiving|monday|tuesday|wednesday|thursday|"
                    r"friday|saturday|sunday|january|february|march|april|june|july|august|september|october|"
                    r"november|december)\b", re.I)
KEEP_CAPS = re.compile(r"\b(?:NYC|BOGO|YMCA|JCC|LA|NY|BF|BFCM|PLUS|PF)\b|\bGO!")
# "Join ... by November 30" is the offer's end (ends.py leaves "by" alone: "order by 12/20 for Christmas delivery")
JOIN_BY = re.compile(r"\b((?:join|sign up|enrol\w*|register)\b[^.!?]{0,80}?)\bby\b", re.I)


def _sentence_case(s: str) -> str:
    """'BLACK FRIDAY SAVINGS ARE HERE! GET STARTED FOR $1 DOWN.' -> 'Black Friday savings are here! Get started for $1
    down.' (only for shouted lines; mixed-case text is left alone)"""
    letters = [c for c in s if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.6:
        return s
    caps = {m.start(): m.group(0) for m in KEEP_CAPS.finditer(s)}
    out = re.sub(r"(^|[.!?]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), s.lower())
    out = PROPER.sub(lambda m: m.group(0).title(), out)
    for pos, word in caps.items():
        out = out[:pos] + word + out[pos + len(word):]
    return out


def tidy(s: str, name: str = "") -> str:
    s = _norm(s)
    s = re.sub(r"(.{12,90}?)[\s|:!.-]+\1", r"\1", s)  # "Black Friday Early Access Black Friday Early Access ..."
    if name:
        s = re.sub(r"\s*[|–-]\s*" + re.escape(name) + r"\s*$", "", s, flags=re.I)  # "... Up to 25% Off | [solidcore]"
    # keep the sentences about the offer's terms or its end, plus an occasion line before the terms ("Don't miss this
    # limited time offer."); drop photo descriptions ("... framed by gold Black Friday ribbons.") and slogans
    parts = re.split(r"(?<=[.!?])\s+", s)
    first_terms = next((n for n, p in enumerate(parts) if TERMS.search(p)), len(parts))
    kept = [p for n, p in enumerate(parts) if TERMS.search(p) or END_HINT.search(p)
            or (OCCASION.search(p) and n < first_terms)]
    s = " ".join(kept) if kept else s
    prev = None
    while prev != s:
        prev, s = s, CTA.sub("", s).strip(" ,-|·:")
    return _sentence_case(s)


def offer_from_html(html: str, name: str = "") -> str:
    """The gym's offer line on this page (up to 300 characters), or ''."""
    html = re.sub(r"<(script|style|svg|noscript|template)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    soup = BeautifulSoup(html, "lxml")
    texts = []  # (text, bonus)
    # dedicated offer pages state it in the page's own summary ([solidcore]: "Save up to 25% on memberships ..."),
    # which beats a long FAQ answer further down
    for m in soup.find_all("meta", attrs={"content": True}):
        if (m.get("name") or m.get("property") or "").lower() in ("description", "og:description", "og:title"):
            texts.append((m["content"], 10))
    for img in soup.find_all("img", alt=OCCASION):  # banner images ("Black Friday BOGO Deal")
        texts.append((img["alt"], 0))
    # banners and heroes: the smallest element around an occasion or terms phrase that holds both
    for node in soup.find_all(string=lambda s: bool(s) and (OCCASION.search(s) or TERMS.search(s))):
        if isinstance(node, Comment):  # LA Fitness keeps an old banner in a comment
            continue
        el, t = node.parent, str(node)
        for _ in range(4):
            if (OCCASION.search(t) and TERMS.search(t)) or el is None or el.name in SKIP_PARENT:
                break
            grown = _norm(el.get_text(" ", strip=True))
            if len(grown) > 300:
                break
            t, el = grown, el.parent
        texts.append((t, 0))
    best, best_score = "", 0.0
    for t, bonus in texts:
        t = tidy(t, name)
        if not t or len(t) > 300 or BAD.search(t) or not OCCASION.search(t) or not TERMS.search(t):
            continue
        # distinct terms (a banner repeated twice is not two offers), the occasion named, a stated end, shorter
        score = (10 * len({m.group(0).lower() for m in TERMS.finditer(t)}) + 3 * bool(re.search(r"black friday|cyber", t, re.I))
                 + 4 * bool(END_HINT.search(t)) - len(t) / 40 + bonus)
        if score > best_score:
            best, best_score = t, score
    return best


def short(offer: str, n: int = 170) -> str:
    return offer if len(offer) <= n else offer[:n].rsplit(" ", 1)[0] + "…"


def where_line(g: dict) -> str:
    parts = [f"NYC: {g['nyc']}" if g.get("nyc") else "No NYC location listed"]
    if g.get("courts"):
        parts.append(f"🏀 Basketball: {g['courts']}")
    return " · ".join(parts)


def gym_item(g: dict, url: str, offer: str) -> Item:
    # the title is shortened for the card; the full line stays in the summary, where the end date is read too
    it = Item(title=f"{g['name']}: {short(offer)}", link=url, source=f"Gym site: {g['name']}", kind="deal",
              store=g["name"], published=NOW.isoformat(), age_days=0.0, history_key=f"gym:{urlsplit(url).netloc}",
              summary=offer)
    end = ENDS.find_end(JOIN_BY.sub(r"\1ends", offer), NOW)
    if end:
        it.expires = end.isoformat()
    it.where = where_line(g)
    it.flags.append("gym_offer")
    it.brands = [g["name"]]
    it.watch_tags = ["Memberships & classes"] + (["NYC"] if g.get("nyc") else []) \
        + (["Basketball courts"] if g.get("courts") else [])
    it.reasons.append("Live offer on the gym's own website")
    return it


def scan_gym(g: dict) -> tuple[Item | None, bool]:
    """(item or None, page read?)"""
    for url in g["urls"]:
        try:
            r = session.get(url, timeout=20)
        except Exception:  # noqa: BLE001
            continue
        if r.status_code != 200:
            continue
        offer = offer_from_html(r.text, g["name"])
        return (gym_item(g, r.url or url, offer) if offer else None), True
    return None, False


def scan_all(workers: int = 8) -> tuple[list[Item], list[dict]]:
    items, read, failed = [], 0, []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for g, (it, ok) in zip(C.GYMS, ex.map(scan_gym, C.GYMS)):
            read += ok
            if not ok:
                failed.append(g["name"])
            if it:
                items.append(it)
    print(f"  gym sites: {len(items)} offers from {read}/{len(C.GYMS)} pages read"
          + (f" (not read: {', '.join(failed)})" if failed else ""))
    status = [{"name": f"Gym sites ({read}/{len(C.GYMS)} read)", "url": "https://github.com/pjmerica/deal-scout/blob/main/config.py",
               "kind": "deal", "ok": read >= len(C.GYMS) // 2, "count": len(items)}]
    return items, status
