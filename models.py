from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc)


@dataclass
class Item:
    title: str
    link: str
    source: str
    kind: str                      # deal | article
    published: str = ""            # ISO timestamp
    age_days: float = 0.0
    summary: str = ""
    image: str = ""
    store: str = ""
    price: float | None = None
    orig_price: float | None = None
    pct_off: int | None = None     # effective (stacked) discount
    saved: float | None = None     # dollars saved
    votes: int | None = None
    comments: int | None = None
    staff_pick: bool = False
    expires: str = ""              # when the deal ends (ISO, UTC): DealNews's field or read from the text (ends.py)
    feed_tags: list[str] = field(default_factory=list)
    thread_id: str = ""            # Slickdeals thread id (for cross-feed signals)
    # Brand-store (Shopify) extras
    in_stock_ratio: float | None = None
    variants: int = 1                   # brand-store colour/size variants collapsed into this item
    store_median: float | None = None   # typical discount across that store's sale items
    history_key: str = ""
    # derived
    is_clothing: bool = False
    clothing_tags: list[str] = field(default_factory=list)
    category: str = ""
    gender: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    is_bf: bool = False
    is_new: bool = False
    flags: list[str] = field(default_factory=list)       # frontpage, popular, price_history, ...
    reasons: list[str] = field(default_factory=list)     # human-readable "why it ranks"
    warnings: list[str] = field(default_factory=list)    # catches: membership, in-store, ...
    score: float = 0.0
    tier: str = ""
    boost: float = 0.0
    sources: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)       # promo codes found in the text / banner
    price_note: str = ""                                 # 'Tracked since Nov 18: $59–$79'
    first_seen: str = ""                                 # when Deal Scout first saw it (history.py), ISO UTC
    watch: list[str] = field(default_factory=list)       # config.WATCH labels the title matches
    stack: str = ""                                      # key into data['stacks'] (Card Scout hints)
    stack_pts: float = 0.0
