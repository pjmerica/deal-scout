"""
Credit card intelligence:
  * Frequent Miler "Best Credit Card Offers": every current sign-up offer with FM's
    first-year value estimate (bonus value + credits - fee).
  * Doctor of Credit "Best Current Credit Card Sign Up Bonuses": a curated pick list,
    with spend requirement, timeframe and annual fee.
  * Rakuten cash-back rates for clothing / department stores.
These are merged and ranked by a transparent first-year value model.
"""
from __future__ import annotations

import concurrent.futures as cf
import html
import re

from bs4 import BeautifulSoup

import brands as BR
from feeds import fetch, fetch_head

FM_URL = "https://frequentmiler.com/best-credit-card-offers/"
DOC_URL = "https://www.doctorofcredit.com/best-current-credit-card-sign-bonuses/"

# Rough cents-per-point values used when FM doesn't provide an estimate.
POINT_VALUES = [
    (r"membership rewards|amex|american express(?!.*(?:delta|hilton|marriott))", 1.3),
    (r"ultimate rewards|sapphire|chase ink|freedom", 1.3), (r"thankyou|citi strata|citi premier", 1.2),
    (r"capital one|venture", 1.2), (r"bilt", 1.4), (r"hyatt", 1.6), (r"hilton", 0.45), (r"marriott|bonvoy", 0.7),
    (r"ihg", 0.5), (r"wyndham", 0.8), (r"united", 1.1), (r"delta", 1.1), (r"american airlines|aadvantage", 1.3),
    (r"southwest", 1.3), (r"alaska|atmos", 1.3), (r"jetblue", 1.2), (r"avios|british airways|aer lingus|iberia", 1.3),
]

CLOTHING_PERK = re.compile(r"lululemon|saks|nordstrom|shopping|purchase protection|return protection|"
                           r"walmart\+?|amazon|target|apparel|clothing|department store|ralph lauren|cashback", re.I)
ELEVATED = re.compile(r"highest|all[- ]time high|best (?:ever|offer)|increased|elevated|record|limited[- ]time", re.I)
STOP = {"card", "credit", "the", "from", "visa", "infinite", "signature", "world", "elite", "mastercard", "®",
        "™", "℠", "american", "express", "rewards", "of", "bank", "business", "&", "-", "–", "personal"}


def _tokens(name: str) -> set[str]:
    name = re.sub(r"[®™℠’'()]", " ", name.lower())
    name = re.split(r"\s[–-]\s|:", name)[0]
    return {t for t in re.split(r"[^a-z0-9+]+", name)
            if t and t not in STOP and not t.isdigit() and not re.fullmatch(r"\d+k|\d+,\d+", t)
            and t not in {"up", "to", "points", "point", "miles", "bonus", "signup", "offer", "k", "increased", "offers"}}


def _cpp(name: str) -> float:
    for pat, v in POINT_VALUES:
        if re.search(pat, name, re.I):
            return v
    return 1.0


def _num(s: str) -> int:
    s = s.lower().replace(",", "").strip()
    return int(float(s[:-1]) * 1000) if s.endswith("k") else int(float(s))


def parse_fm() -> list[dict]:
    raw = fetch(FM_URL)
    if not raw:
        return []
    soup = BeautifulSoup(raw, "lxml")
    tables = soup.find_all("table")
    out, seen = [], set()
    for ti, tbl in enumerate(tables[:2]):
        for row in tbl.find_all("tr"):
            box = row.select_one(".BOtmo")
            if not box:
                continue
            a = box.find("a")
            name = a.get_text(" ", strip=True) if a else ""
            if not name or name in seen:
                continue
            seen.add(name)
            full = box.get_text(" ", strip=True)
            val_m = re.search(r"\$([\d,]+)\s*1st Yr Value", full)
            tip = box.select_one(".FMtipL")
            tip_txt = tip.get_text(" ", strip=True).replace("Click to learn about first year value estimates", "").strip() if tip else ""
            offer = full.replace(name, "", 1)
            offer = re.split(r"ⓘ|\$[\d,]+\s*1st Yr", offer)[0].strip()
            href = a.get("href", "") if a else ""
            out.append({
                "name": name, "offer": offer, "fm_value": _num(val_m.group(1)) if val_m else None,
                "business": ti == 1 or "business" in name.lower(), "targeted": "targeted" in full.lower(),
                "variable": "as high as" in offer.lower() or "up to" in offer.lower(),
                "details": tip_txt[:400], "link": ("https://frequentmiler.com" + href) if href.startswith("/") else (href or FM_URL),
            })
    return out


def parse_doc() -> list[dict]:
    raw = fetch(DOC_URL)
    if not raw:
        return []
    soup = BeautifulSoup(raw, "lxml")
    art = soup.select_one("article") or soup
    out, section = [], ""
    for el in art.find_all(["h2", "h3"]):
        if el.name == "h2":
            section = el.get_text(" ", strip=True)
            if section.lower().startswith(("not on", "recent", "final")):
                section = "STOP"
            continue
        if section in ("", "STOP") or el.find_parent(["nav", "aside"]) or el.find_parent(class_=re.compile("toc", re.I)):
            continue
        title = el.get_text(" ", strip=True)
        body, sib = [], el.find_next_sibling()
        while sib is not None and sib.name not in ("h2", "h3"):
            body.append(sib.get_text(" ", strip=True))
            sib = sib.find_next_sibling()
        text = " ".join(body)
        spend = (re.search(r"spend(?:ing)?\s+(?:of\s+)?\$([\d,]+k?)", text, re.I)
                 or re.search(r"\$([\d,]+k?)\s+(?:in\s+)?(?:purchases|spend)", text, re.I))
        months = re.search(r"(?:within|in|first)\s+(?:the\s+first\s+)?(\d+)\s+months", text, re.I)
        days = re.search(r"(?:within|in|first)\s+(?:the\s+first\s+)?(\d+)\s+days", text, re.I)
        fee = re.search(r"\$([\d,]+)\s+annual fee|annual fee (?:of |is )?\$([\d,]+)", text, re.I)
        pts = re.search(r"([\d,]{5,9}|\d{2,3}k)\s+(?:bonus\s+)?(?:points|miles)", f"{title} {text}", re.I)
        cash = (re.search(r"\$([\d,]{3,5})\s+(?:cash|bonus|statement credit|signup)", f"{title} {text}", re.I)
                or re.search(r"[–-]\s*\$([\d,]{3,5})\b|\bget \$([\d,]{3,5})", f"{title} {text}", re.I))
        out.append({
            "name": title, "section": section, "text": text[:500],
            "spend": _num(spend.group(1)) if spend else None, "months": int(months.group(1)) if months else (round(int(days.group(1)) / 30) if days else None),
            "annual_fee": (0 if re.search(r"no annual fee|\$0 annual fee", text, re.I)
                           else (_num(fee.group(1) or fee.group(2)) if fee else None)),
            "fee_waived": bool(re.search(r"waived (?:the )?first year|first year (?:annual fee )?waived", text, re.I)),
            "points": _num(pts.group(1)) if pts else None,
            "cash": _num(next(g for g in cash.groups() if g)) if cash else None,
            "elevated": bool(ELEVATED.search(text)), "targeted": "ymmv" in section.lower() or "targeted" in section.lower(),
            "business": "business" in section.lower() or "business" in title.lower(),
            "link": DOC_URL + "#" + (el.find("span").get("id", "") if el.find("span") else ""),
        })
    return out


def _match(name: str, cands: list[dict], business: bool, taken: set) -> dict | None:
    a = _tokens(name)
    best, best_s = None, 0.0
    for c in cands:
        if id(c) in taken or bool(c.get("business")) != bool(business):
            continue
        b = _tokens(c["name"])
        if not a or not b:
            continue
        s = len(a & b) / len(a | b)
        if s > best_s:
            best, best_s = c, s
    return best if best_s >= 0.5 else None


def best_card_offers() -> tuple[list[dict], dict]:
    fm, doc = parse_fm(), parse_doc()
    offers = []
    taken_fm, doc_for = set(), {}
    for d in doc:
        f = _match(d["name"], fm, d["business"], taken_fm)
        if f:
            taken_fm.add(id(f))
            doc_for[id(f)] = d
    for f in fm:
        offers.append({**f, "doc": doc_for.get(id(f))})
    matched_doc = {id(v) for v in doc_for.values()}
    for d in doc:  # DoC picks FM doesn't list
        if id(d) not in matched_doc:
            offers.append({"name": d["name"], "offer": d["name"], "fm_value": None, "business": d["business"],
                           "targeted": d["targeted"], "variable": False, "details": "", "link": d["link"], "doc": d})
    ranked = []
    for o in offers:
        d = o.get("doc") or {}
        value = o.get("fm_value")
        est = False
        if value is None:
            pts = d.get("points") or 0
            value = int(pts * _cpp(o["name"]) / 100) + (d.get("cash") or 0)
            fee = d.get("annual_fee") or 0
            if not d.get("fee_waived"):
                value -= fee
            est = True
        score = min(70, (value or 0) / 40)
        reasons = []
        if o.get("fm_value"):
            reasons.append(f"${o['fm_value']:,} est. first-year value (Frequent Miler)")
        elif value:
            reasons.append(f"≈${value:,} est. first-year value")
        if d:
            score += 15
            reasons.append("On Doctor of Credit's best-offers list")
        if d.get("elevated"):
            score += 10
            reasons.append("Elevated / highest-ever wording")
        perk_txt = f"{o.get('details', '')} {d.get('text', '')}"
        clothing_perk = bool(CLOTHING_PERK.search(perk_txt))
        if clothing_perk:
            score += 6
            m = CLOTHING_PERK.search(perk_txt)
            reasons.append(f"Shopping perk: {m.group(0)}")
        spend = d.get("spend")
        if spend:
            if spend <= 4000:
                score += 6
                reasons.append(f"Reachable with holiday spend (${spend:,})")
            elif spend >= 15000:
                score -= 10
        if o.get("targeted"):
            score -= 4
        ranked.append({
            "name": o["name"], "offer": o["offer"], "value": value, "value_is_estimate": est,
            "business": o["business"], "targeted": o.get("targeted", False), "variable": o.get("variable", False),
            "details": o.get("details", ""), "link": o["link"], "doc_pick": bool(d), "elevated": bool(d.get("elevated")),
            "spend": spend, "months": d.get("months"), "annual_fee": d.get("annual_fee"),
            "fee_waived": d.get("fee_waived", False), "clothing_perk": clothing_perk,
            "score": round(score, 1), "reasons": reasons,
        })
    ranked.sort(key=lambda x: -x["score"])
    status = {"fm": len(fm), "doc": len(doc)}
    return ranked, status


# ---------------------------------------------------------------------------
# Rakuten cash-back rates for clothing stores
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", html.unescape(s).lower().replace("&", "and"))


def rakuten_rates(workers: int = 6) -> list[dict]:
    def slugs(name: str) -> list[str]:
        base = html.unescape(name).lower().replace("’", "'")
        a = re.sub(r"[^a-z0-9]", "", base.replace("&", ""))
        b = re.sub(r"[^a-z0-9]", "", base.replace("&", "and"))
        c = re.sub(r"[^a-z0-9]+", "-", base.replace("'", "").replace("&", "and")).strip("-")
        d = re.sub(r"[^a-z0-9]", "", base.split(" ")[0])
        out = []
        for x in (a, b, c, d):
            if x and x not in out:
                out.append(x)
        return out

    def run(name):
        first = re.sub(r"[^a-z0-9]", "", html.unescape(name).lower().split(" ")[0].replace("’", "'"))
        for slug in slugs(name):
            head = fetch_head(f"https://www.rakuten.com/shop/{slug}")
            if not head:
                continue
            t = re.search(r"<title>(.*?)</title>", head, re.S)
            title = html.unescape(t.group(1)) if t else ""
            if "Cash Back" in title and first[:4] in re.sub(r"[^a-z0-9]", "", title.lower()):
                break
        else:
            return None
        m = re.search(r"&\s*((?:Up to\s+)?(?:\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?)|No)\s+Cash Back", title, re.I)
        if not m:
            return None
        rate_txt = m.group(1)
        pct = re.search(r"(\d+(?:\.\d+)?)%", rate_txt)
        store_name = re.split(r"\s+Coupons", title)[0].strip() or name
        return {"store": store_name, "slug": slug, "rate": rate_txt if rate_txt.lower() != "no" else "None",
                "pct": float(pct.group(1)) if pct else 0.0, "url": f"https://www.rakuten.com/shop/{slug}"}

    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        seen = set()
        for r in ex.map(run, BR.RAKUTEN_CLOTHING):
            if r and r["slug"] not in seen:
                seen.add(r["slug"])
                out.append(r)
    out.sort(key=lambda r: -r["pct"])
    return out
