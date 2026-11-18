"""Regression tests for the deal logic. Run: python -m pytest tests -q  (or python tests/test_scoring.py)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import brands as BR  # noqa: E402
import scoring  # noqa: E402
import shopify  # noqa: E402
from models import Item  # noqa: E402


def mk(title, summary="", **kw):
    it = Item(title=title, link="https://example.com/" + title[:10], source=kw.pop("source", "Test"), kind="deal",
              summary=summary, **kw)
    it.sources = [it.source]
    scoring.classify(it)
    scoring.extract_pricing(it)
    scoring.score_deal(it)
    return it


def test_stacked_discount_compounds():
    it = mk("Old Navy 50% Off Early Black Friday + Extra 30% Off From $1.47")
    assert it.pct_off == 65


def test_up_to_is_discounted():
    it = mk("Nordstrom Rack Up to 70% Off")
    assert it.pct_off == 56


def test_reg_price_math_and_savings():
    it = mk("Men's Wool Overcoat $120 (reg. $400)")
    assert it.pct_off == 70 and it.saved == 280 and it.is_clothing


def test_dealnews_down_from():
    it = mk("Banana Republic Sale", "The men's Signature Suit Jacket is $150, down from $450.")
    assert it.orig_price == 450 and it.pct_off >= 66


def test_price_history_evidence():
    it = mk("Nike Jordan Session Shoes $45", "It's the best price we could find by $15.")
    assert "price_history" in it.flags
    assert any("Best price" in r for r in it.reasons)


def test_brand_baseline_rewards_rare_discounts():
    pata = mk("Patagonia Nano Puff Jacket 40% off")
    navy = mk("Old Navy Puffer Jacket 40% off")
    assert pata.score > navy.score


def test_catches_penalize():
    clean = mk("Levi's 501 Jeans $30 (reg $70)")
    instore = mk("Levi's 501 Jeans $30 (reg $70) in-store only YMMV")
    assert instore.score < clean.score and "In-store only / YMMV" in instore.warnings


def test_not_clothing_false_positives():
    for t in ["Givenchy Eau De Parfum 3.3oz $60", "Insulated Stainless Steel Water Bottle $8",
              "Eddie Bauer Soft King Size Blanket $36", "Bath & Body Works Candles 40% off"]:
        assert not mk(t).is_clothing, t


def test_summary_extras_do_not_overstack():
    it = mk("Old Navy 50% Off Early Black Friday + Extra 30% Off",
            "Old Navy takes 50% off, plus an extra 30% off, and cardmembers get an extra 20% off.")
    assert it.pct_off == 65


def test_final_price_not_stacked_with_codes():
    it = mk("Banana Republic Sale: Up to 40% off + extra 20% off",
            "The men's Signature Suit Jacket is $150, down from $450.")
    assert it.pct_off == 67


def test_camel_drop_parsing():
    it = mk("BOSS VE-500 Vocal Performer - down 9.93% ($41.73) to $378.49 from $420.22",
            source="camelcamelcamel Top Drops")
    assert it.price == 378.49 and it.pct_off == 10 and it.saved == 41.73 and not it.is_clothing


def test_unknown_brand_penalty():
    known = mk("Levi's Trucker Jacket $40 (reg $98)")
    generic = mk("Zorvexa Trucker Jacket $40 (reg $98)")
    assert generic.score < known.score and "Lesser-known brand" in generic.warnings


def test_giveaway_dropped():
    raw = [Item(title="Target Black Friday Giveaway: win a gift card", link="https://x", source="T", kind="deal")]
    assert scoring.process(raw) == []


def test_handle_ranking():
    assert shopify._handle_score("black-friday-sale", 2026) > shopify._handle_score("bfcm-accessories", 2026)
    assert shopify._handle_score("2024-holiday-sale", 2026) < 20
    assert shopify._handle_score("wholesale", 2026) < 0


def test_promo_filters():
    assert shopify.PROMO_BAD.search("Get 20% off your first order when you sign up")
    assert shopify.PROMO_BAD.search("Shop by Markdown 30% off 40% off 50% off")
    assert not shopify.PROMO_BAD.search("BLACK FRIDAY: 40% Off Everything")


def test_history_new_and_price_drop():
    import datetime
    import history
    from models import NOW
    h = {"items": {}, "rakuten": {}, "promos": {}, "runs": []}
    a = Item(title="A", link="https://a", source="s", kind="deal", price=10)
    history.apply(h, [a])
    assert not a.is_new  # the baseline run never marks NEW
    old = (NOW - datetime.timedelta(hours=3)).isoformat()
    h["runs"] = [old]
    h["items"]["https://a"]["first"] = old
    a2 = Item(title="A", link="https://a", source="s", kind="deal", price=8)
    b = Item(title="B", link="https://b", source="s", kind="deal", price=5)
    history.apply(h, [a2, b])
    assert not a2.is_new and "price_drop" in a2.flags and b.is_new


def test_gender_detection():
    import gender as G
    assert G.detect("Women’s Birkenstock Sandals $42") == ["Women's"]          # curly apostrophe
    assert G.detect("Alo Yoga: Unisex Throwback Sock") == ["Everyone"]
    assert G.detect("Men's & Women's Fleece Jackets 40% off") == ["Everyone"]
    assert G.detect("The Silky Flutter Sleeve Dress", brands=["Summersalt"]) == ["Women's"]
    assert G.detect("Cashmere Turtleneck", brands=["Todd Snyder"]) == ["Men's"]
    assert G.detect("Girls' Puffer Jacket $20") == ["Kids"]
    assert G.detect("Eddie Bauer Black Friday Deals: 50% off", has_garment=False) == ["Everyone"]
    assert G.detect("Oxford Shirt", tags="Mens Tops") == ["Men's"]
    assert G.detect("Oxford Shirt") == []
    # structured retailer tags win; "color-family:BLUE" is not "family" = unisex (Faherty, 2026-11-18)
    assert G.detect("Coastline Knit Shirt", brands=["Faherty"],
                    tags="Men's Button Ups color family BLUE division Mens gender Men") == ["Men's"]
    assert G.detect("Tee", tags="color family BLUE") == []
    assert G.detect("Tee", tags="gender Men gender Women") == ["Everyone"]
    assert G.detect("Tee", tags="department Unisex") == ["Everyone"]


def test_promo_tidy():
    assert shopify._tidy("Shop All Black Friday Sale NEW Shop Represent Black Friday Sale Now Live - Up to 70% Off") \
        .startswith("Black Friday Sale")
    assert shopify._tidy("BLACK FRIDAY: 40% Off Everything* BLACK FRIDAY: 40% Off Everything* Shop Women") == \
        "BLACK FRIDAY: 40% Off Everything"


def test_gender_on_scored_items():
    assert mk("Women’s Snow Boots Only $31.84 (Regularly $90)").gender == ["Women's"]
    assert "Men's" in mk("Adidas men's hyperboost shoes - $59.50 (reg $170)").gender


def test_promo_codes():
    import codes
    assert codes.extract('At Nike, use promo code "EARLYBF" to get these') == ["EARLYBF"]
    assert codes.extract('Apply coupon code "Fluxbigsale" at checkout') == ["Fluxbigsale"]
    assert codes.extract("35% Off Everything Code: EARLY Copied!") == ["EARLY"]
    assert codes.extract("w/ code BFCM26 + free shipping") == ["BFCM26"]
    for prose in ["no code needed", "zip code 90210", "Promo code required at checkout", "CODE NEEDED"]:
        assert codes.extract(prose) == [], prose
    assert mk('Nike Jordan Session Shoes $45', 'use promo code "EARLYBF" to get them').codes == ["EARLYBF"]


def test_fake_sale_detector():
    import datetime
    import history
    from models import NOW
    old = (NOW - datetime.timedelta(days=3)).isoformat()
    h = {"items": {"shop.com:jacket": {"first": old, "last": old, "price": 60.0, "min": 60.0, "pct": 40,
                                       "orig": 100.0, "series": [[old, 60.0]]}},
         "promos": {}, "runs": [old]}
    it = Item(title="Brand: Jacket", link="https://shop.com/products/jacket", source="Brand store: X", kind="deal",
              price=72.0, orig_price=180.0, pct_off=60, history_key="shop.com:jacket")
    it.flags.append("retailer_verified")
    history.apply(h, [it])
    assert "orig_raised" in it.flags and "was_cheaper" in it.flags
    assert any("Original price raised $100 → $180" in w for w in it.warnings)
    assert it.price_note.startswith("Tracked since")
    # the same price movement on a deal-site headline (not retailer data) is not judged
    h2 = {"items": {"sd:1": dict(h["items"]["shop.com:jacket"])}, "promos": {}, "runs": [old]}
    feed = Item(title="Jacket $72", link="https://slickdeals.net/f/1-x", source="Slickdeals", kind="deal",
                price=72.0, orig_price=180.0, thread_id="1")
    history.apply(h2, [feed])
    assert "orig_raised" not in feed.flags and "was_cheaper" not in feed.flags


def test_fake_sale_lowers_score():
    a = mk("Brand: Wool Coat $72 (reg $180)")
    b = mk("Brand: Wool Coat $72 (reg $180)")
    b.flags += ["orig_raised", "was_cheaper"]
    b.reasons, b.warnings = [], []
    scoring.score_deal(b)
    assert b.score < a.score


def test_stack_matching():
    import stacks
    st = {"macys": {"name": "Macy's", "rakuten": "10%", "rpct": 10.0}, "saksfifthavenue": {"name": "Saks"},
          "saksoff5th": {"name": "Saks OFF 5TH"}, "nordstrom": {"name": "Nordstrom", "offers": [{"label": "Amex Offer"}]}}
    assert stacks.match(st, ["Macy's"]) == "macys"
    assert stacks.match(st, ["Nordstrom"]) == "nordstrom"
    assert stacks.match(st, ["Saks"]) == ""          # ambiguous between two Saks stores: no badge
    assert stacks.match(st, ["Amazon"]) == ""
    it = Item(title="Macy's: Coat 50% off", link="x", source="T", kind="deal", store="Macy's")
    stacks.apply(st, [it], [])
    assert it.stack == "macys" and it.stack_pts > 0


def test_strip_tracking():
    import deal_scout
    assert deal_scout.strip_tracking("https://slickdeals.net/f/1-x?utm_source=rss&utm_medium=RSS2") == "https://slickdeals.net/f/1-x"
    assert deal_scout.strip_tracking("https://www.dealnews.com/x.html?iref=rss-c206") == "https://www.dealnews.com/x.html"
    assert deal_scout.strip_tracking("https://shop.com/p?color=red&utm_x=1") == "https://shop.com/p?color=red"


def test_baseline_lookup():
    assert BR.baseline_for(["Patagonia"]) == 10
    assert BR.baseline_for([], "Old Navy") == 50
    assert BR.baseline_for([]) == BR.DEFAULT_BASELINE


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    sys.exit(1 if fails else 0)
