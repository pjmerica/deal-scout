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


def test_gender_on_scored_items():
    assert mk("Women’s Snow Boots Only $31.84 (Regularly $90)").gender == ["Women's"]
    assert "Men's" in mk("Adidas men's hyperboost shoes - $59.50 (reg $170)").gender


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
