"""Promo-code extraction: 'use promo code "EARLYBF"', 'w/ code BFCM26', banner 'Code: EARLY'."""
from __future__ import annotations

import re

CODE_RE = re.compile(
    r"(?:promo(?:tional)? code|coupon code|discount code|offer code|use code|with code|w/ ?code|enter code|"
    r"apply code|\bcode)\s*[:\-]?\s*([\"“”'‘’]?)([A-Za-z0-9][A-Za-z0-9_-]{2,19})([\"“”'‘’]?)", re.I)

# Words that follow "code" in prose but aren't codes ("no code needed", "code at checkout", "zip code")
STOP = {
    "needed", "required", "req", "applied", "automatically", "auto", "below", "above", "checkout", "cart", "none",
    "free", "only", "the", "and", "for", "with", "this", "that", "here", "link", "page", "offer", "offers", "valid",
    "expires", "ends", "works", "applies", "apply", "enter", "code", "codes", "promo", "coupon", "online", "store",
    "instore", "app", "members", "member", "extra", "stack", "stacks", "sale", "deal", "deals", "when", "will",
    "must", "used", "use", "sent", "email", "texted", "via", "may", "not", "also", "plus", "then", "from", "into",
    "pickup", "shipping", "ship", "orders", "order", "item", "items", "select", "clip", "coupons", "copied", "copy",
}


def extract(text: str, limit: int = 2) -> list[str]:
    out: list[str] = []
    for m in CODE_RE.finditer(text or ""):
        q1, code, q2 = m.group(1), m.group(2), m.group(3)
        quoted = bool(q1 and q2)
        if len(code) < 4 or code.lower() in STOP or code.isdigit():
            continue
        # Unquoted codes must look like codes (ALL CAPS, usually with digits); quoted ones can be mixed case.
        if not quoted and not (code == code.upper() and re.search(r"[A-Z]", code)):
            continue
        if code not in out:
            out.append(code)
        if len(out) >= limit:
            break
    return out
