"""
Stack hints from the companion site Card Scout (separate repo).

At build time we read Card Scout's published cards.json and index, per store:
  - the current Rakuten cash-back rate (if above 0%), and whether it's elevated
  - up to 2 recent card-linked offers / portal deals naming that store (Amex/Chase/Capital One...)
Deals and brand sales at a matching store get small badges ("Rakuten 10%", "Amex Offer") and a
small score bonus (cash back is real money). If Card Scout is unreachable, nothing changes.
"""
from __future__ import annotations

import json
import re

from feeds import fetch

ISSUERS = [(r"amex|american express", "Amex Offer"), (r"\bchase\b", "Chase Offer"),
           (r"capital one", "Capital One Offer"), (r"\bciti\b", "Citi Offer"),
           (r"bankamerideals|bank of america", "BofA Deal"), (r"rakuten|topcashback|shopback|portal", "Portal deal")]
MAX_OFFER_AGE_DAYS = 14


def norm(s: str) -> str:
    s = (s or "").lower().replace("&", "and").replace("’", "'").strip()
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\.com$", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def load(base_url: str) -> tuple[dict, dict]:
    url = base_url.rstrip("/") + "/cards.json"
    status = {"name": "Card Scout (stack data)", "url": base_url, "kind": "stack", "ok": False, "count": 0}
    raw = fetch(url, retries=1)
    if not raw:
        return {}, status
    try:
        d = json.loads(raw)
    except ValueError:
        return {}, status
    stacks: dict[str, dict] = {}
    for r in d.get("rakuten", []):
        if (r.get("pct") or 0) <= 0:
            continue
        e = stacks.setdefault(norm(r["store"]), {"name": r["store"]})
        e.update(rakuten=r["rate"], rpct=r["pct"], rurl=r["url"], elev=bool(r.get("elevated")))
    for n in d.get("news", []):
        if n.get("card_category") != "Shopping & Card-Linked Offers" or not n.get("retailers"):
            continue
        if n.get("warnings") or (n.get("age_days") or 0) > MAX_OFFER_AGE_DAYS:
            continue
        label = next((lab for pat, lab in ISSUERS if re.search(pat, n["title"], re.I)), "Card offer")
        for ret in n["retailers"]:
            e = stacks.setdefault(norm(ret), {"name": ret})
            offs = e.setdefault("offers", [])
            if len(offs) < 2 and all(o["link"] != n["link"] for o in offs):
                offs.append({"label": label, "title": n["title"][:140], "link": n["link"]})
    status.update(ok=True, count=len(stacks))
    return stacks, status


def match(stacks: dict, names: list[str]) -> str:
    keys = [norm(n) for n in names if n]
    for k in keys:
        if len(k) >= 3 and k in stacks:
            return k
    for k in keys:  # "Saks" -> "saksfifthavenue" only when unambiguous
        if len(k) < 4:
            continue
        cands = [s for s in stacks if s.startswith(k) or (len(s) >= 5 and k.startswith(s))]
        if len(cands) == 1:
            return cands[0]
    return ""


def apply(stacks: dict, items, brand_sales: list[dict]) -> int:
    n = 0
    for it in items:
        if it.kind != "deal" or not stacks:
            continue
        k = match(stacks, [it.store] + list(it.brands))
        if not k:
            continue
        e = stacks[k]
        it.stack = k
        if e.get("rpct"):
            it.stack_pts += min(4.0, e["rpct"] * 0.4)
            it.reasons.append(f"Stacks with Rakuten {e['rakuten']} cash back")
        if e.get("offers"):
            it.stack_pts += 2.0
            it.reasons.append(f"{e['offers'][0]['label']} at {e['name']}")
        n += 1
    for s in brand_sales:
        s["stack"] = match(stacks, [s["store"]]) if stacks else ""
    return n
