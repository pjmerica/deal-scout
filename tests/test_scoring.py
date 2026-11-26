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


def test_banner_code_belongs_to_its_promo():
    untuckit = ('<div class="bar"><div class="slide"><p>Black Friday Early Access | 35% Off Everything</p>'
                '<span>Code: <b>EARLY</b> Copied!</span></div></div>')
    assert shopify.promo_from_html(untuckit)[3] == "EARLY"
    madden = ('<div class="bar"><div class="slide"><p>50% off Black Friday Specials: New drops every day.</p></div>'
              '<div class="slide"><p>Black Friday Preview: 40% off select styles with code EARLY.</p></div></div>')
    snippet, pct, _, code = shopify.promo_from_html(madden)
    assert pct == 50 and code == ""  # the code belongs to the 40% slide, not the 50% one


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


def test_ambiguous_store_names_not_matched_in_headlines():
    # "price cuts" is not the brand Cuts, a bed frame isn't FRAME denim, Mother's Day isn't MOTHER
    for t in ['Price cuts on 65" TVs $299', "Wooden bed frame queen $150", "Mother's Day jewelry gift $20",
              "Soul at Scale: Noah on automation"]:
        it = mk(t)
        assert not it.is_clothing and not it.brands, t
    assert mk("TOMS Alpargata Shoes $25").is_clothing  # case-sensitive TOMS still counts


def test_home_goods_from_apparel_brands_are_not_clothing():
    def store_item(title, store):
        it = Item(title=f"{store}: {title}", link="x/" + title, source=f"Brand store: {store}", kind="deal")
        it.brands = [store]
        scoring.classify(it)
        return it
    assert store_item("The Ellie Nap Dress", "Hill House Home").is_clothing
    assert not store_item("Linen Duvet Cover", "Hill House Home").is_clothing
    assert not store_item("CozyChic Throw", "Barefoot Dreams").is_clothing


def test_kids_brand_audience():
    import gender as G
    assert G.detect("Baby Zip Footie", brands=["Primary"]) == ["Kids"]
    assert G.detect("The Emma Flat", brands=["Sarah Flint"]) == ["Women's"]
    # a kids' brand's dress or romper is a child's, not a woman's (Tea Collection, Little Sleepies, 2026-11-23)
    assert G.detect("Ruffle Shoulder Ballet Dress", brands=["Tea Collection"], tags="Girls Dresses") == ["Kids"]
    assert G.detect("Pointelle Leggings", brands=["Tea Collection"], tags="Baby") == ["Kids"]
    assert G.detect("Disney Simba's Safari Bubble Romper", brands=["Little Sleepies"]) == ["Kids"]
    # ...but their adult pieces are not
    assert G.detect("Pink Twinkling Trees Women's Pajama Pants", brands=["Little Sleepies"]) == ["Women's"]
    assert G.detect("Wildwood Floral Sleep Shirt", brands=["Little Sleepies"],
                    tags="Women's Sleep Shirt age adult ss gender Women") == ["Women's"]
    assert G.detect("Adult Pajama Top", brands=["Tea Collection"], tags="Adult Sleep") == ["Everyone"]
    # a roundup naming a kids' brand and a women's brand is not forced to Kids
    assert G.detect("Carter's and Summersalt dresses 40% off", brands=["Carter's", "Summersalt"]) == ["Women's"]
    it = Item(title="Tea Collection: Print Mix Twirl Dress", link="x/twirl", source="Brand store: Tea Collection",
              kind="deal", store="Tea Collection")
    it.brands = ["Tea Collection"]
    scoring.classify(it)
    assert it.gender == ["Kids"] and it.is_clothing


def store_item(title, store):
    it = Item(title=f"{store}: {title}", link="x/" + title, source=f"Brand store: {store}", kind="deal", store=store)
    it.brands = [store]
    scoring.classify(it)
    return it


def test_false_positive_words_are_whole_words():
    # "cruise", "paint", "quilt", "flight" hid real clothing from brand stores (2026-11-23)
    for title, store in [("Women's Canvas Cruiser Slip On - Blizzard", "Allbirds"),
                         ("Mackinaw Wool Caped Cruiser Jacket - Brick Plaid", "Filson"),
                         ("The Men's Cruiser Loafer - Husk", "Rothy's"),
                         ("The All Dressed Up Mock Neck Dress - Painted Floral in Slate", "Summersalt"),
                         ("Terrace Skirt Set in Magenta Painterly Gingham", "Lake Pajamas"),
                         ("Corbet Quilted Hoodie", "Marine Layer"),
                         ("Voltage Quilted Vest - Vetiver", "Howler Brothers"),
                         ("Chrome Flight Hoodie - Stained Black", "Represent")]:
        it = store_item(title, store)
        assert it.is_clothing and it.category == "Clothing & Shoes", title
    for t in ["Cat & Jack Kids' Fleece Pajama Sets $8", "Old Navy 40% Off Your Entire Purchase: Sweaters & Jeans",
              "Women's Holiday Party Attire: Dresses from $15"]:
        assert mk(t).is_clothing, t
    # the words still catch what they were for
    for title, store in [("Linen Quilt - Natural", "Hill House Home"), ("Flightweight Packing Cube Set", "Ministry of Supply"),
                         ("Desk Chic Phone Stand - Silver", "Fashion Nova")]:
        assert not store_item(title, store).is_clothing, title
    for t in ["AOKOWN Waterproof Dog Hoodie Raincoat w/ Leash Hole $5.59", "Carnival Cruise Deals: Hoodie Included"]:
        assert not mk(t).is_clothing, t


def test_garment_tag_fallback():
    # items with no garment tag vanished when the page filtered by garment type (417 on 2026-11-23)
    cases = [("The Way-High Skinny Jean | Ash", "Everlane", "Bottoms"),
             ("The ’90s Cheeky® Jean | Vintage Blue", "Everlane", "Bottoms"),
             ("Didion Drape Top - Printed Washable Silk", "M.M.LaFleur", "Tops"),
             ("CloudKnit Short Sleeve", "Outdoor Voices", "Tops"),
             ("ASTER SHORT", "Robert Graham", "Bottoms"),
             ("Lime Icing Summer Bikini Top", "Montce", "Swimwear"),
             ("Malika One Piece Floral Doodle Noir", "Solid & Striped", "Swimwear"),
             ("Stretch Swim Trunk (Clearance)", "Bearbottom", "Swimwear"),
             ("Apollo Trunk 4\"", "Tommy John", "Basics & Underwear"),
             ("Women's Slip On | Black", "Thousand Fell", "Footwear"),
             ("The Belle Bow - Lime Gingham", "Hill House Home", "Accessories"),
             ("The Draper Pleated Pant in Buttersmooth", "Everlane", "Bottoms"),
             ("Heavyweight Crew Sock 6-Pack", "Duckworth", "Basics & Underwear"),
             ("Global Tek Crew - Short Sleeve", "Topo Designs", "Tops"),  # "Topo" is the store, not a top
             ("The Essential Long Sleeve Coverall", "Wildfang", "Dresses & Sets"),
             ("Men's London - Naval Academy/Harbor Mist", "Kizik", "Footwear"),  # one-garment store, model name
             ("SHELTER WOMENS CREW", "Stance", "Basics & Underwear")]
    for title, store, tag in cases:
        assert store_item(title, store).clothing_tags == [tag], (title, store_item(title, store).clothing_tags)
    # ambiguous words never make something clothing, and storewide sales stay untagged
    for t in ["Top 10 Black Friday TV Deals", "Samsung Short Throw Projector $499", "Fish Tank Starter Kit $40"]:
        it = mk(t)
        assert not it.is_clothing and not it.clothing_tags, t
    for store, promo in [("Hill House Home", "Up to 75% Off Everything"),
                         ("Sarah Flint", "Happening Now: The Black Friday Sale, up to 80% off sitewide"),
                         ("Montce", "BLACK FRIDAY: Up to 80% off swim, tops and bottoms")]:
        it = Item(title=f"{store} sitewide: {promo}", link="x/" + store, source=f"Brand store: {store}", kind="deal",
                  store=store)  # the shape shopify.py gives storewide promos
        it.brands = [store]
        scoring.classify(it)
        assert it.is_clothing and it.clothing_tags == [], (store, it.clothing_tags)
    # a headline roundup is not a garment (local build, 2026-11-25)
    assert mk("Walmart Black Friday Top 100 Fashion Deals: Up to 80% off + free shipping w/ $35").clothing_tags == []
    assert mk("Top-Rated Women's Fashion Finds Under $20").clothing_tags == []
    assert mk("Nike Men's Lunar Force 1 Winterized Duckboots (2 Colors) $127.50").clothing_tags == ["Footwear"]
    # "bikini" alone is not clothing in a headline (a bikini trimmer is a razor)
    assert not mk("Panasonic Bikini Trimmer $15").is_clothing
    assert not mk("100-Piece RoseArt Kodak Premium Puppy Socks Jigsaw Puzzle $2.99").is_clothing
    assert store_item("PUZZLE CREAM", "Steve Madden").is_clothing  # a shoe named Puzzle
    assert mk("Cole Haan Men's Go-to Plain Toe Oxford (British Tan) $60").clothing_tags == ["Footwear"]
    assert store_item("The Jack in Burgundy Oxford", "Taylor Stitch").clothing_tags != ["Footwear"]  # a shirt


def test_not_on_sale_collection_rejected():
    assert shopify._handle_score("not-on-sale", 2026) < 0
    assert shopify._handle_score("black-friday-2026", 2026) > shopify._handle_score("bfcm-decor", 2026)


def test_off_season_collections_lose_to_black_friday():
    # Oliver Cabell's scan picked "july-sale" in November over "30-off-mens-bfcm" (2026-11-25)
    nov = {h: shopify._handle_score(h, 2026, 11) for h in
           ["30-off-mens-bfcm", "july-sale", "labor-day-sale-2026", "mens-memorial-sale-10-off", "summer-sale"]}
    assert nov["30-off-mens-bfcm"] > 20
    assert all(nov[h] < 20 for h in ["july-sale", "labor-day-sale-2026", "mens-memorial-sale-10-off", "summer-sale"]), nov
    assert shopify._handle_score("summer-sale", 2026, 7) > 20  # in season it's the sale
    # collections whose names say "not on sale" (Free Fly, Ridge Merino probe, 2026-11-25)
    for h in ["non-markdown-products-with-compare-at-price", "all-products-minus-sale-items"]:
        assert shopify._handle_score(h, 2026, 11) < 0, h


def test_store_name_is_not_the_product():
    # "Kickee Pants: Knot Headband" was tagged Bottoms, "Monday Swimwear: Cayman Necklace" Swimwear (2026-11-25)
    assert store_item("Knot Headband in Tamarin", "Kickee Pants").clothing_tags == ["Accessories"]
    assert store_item("Cayman Necklace - Silver", "Monday Swimwear").clothing_tags == ["Accessories"]
    assert store_item("Print Twist Nightgown in Navy Dragonfly", "Kickee Pants").clothing_tags != ["Bottoms"]
    it = Item(title="Kickee Pants sitewide: 30% off everything", link="x/kp", source="Brand store: Kickee Pants",
              kind="deal", store="Kickee Pants")
    scoring.classify(it)
    assert it.clothing_tags == []
    # a dress sock is a sock
    assert store_item("MENS ALL OVER BUNNY DRESS SOCK - MO2200022", "Psycho Bunny").clothing_tags == ["Basics & Underwear"]
    assert "Footwear" in mk("Cole Haan Men's Dress Shoes $60").clothing_tags
    assert mk("Cole Haan Men's Dress Shoes $60").clothing_tags == ["Footwear"]
    # ski bibs are pants, baby bibs aren't clothing; a blanket-stripe shirt is a shirt
    assert store_item("M Steibis Bib", "Obermeyer").clothing_tags == ["Bottoms"]
    assert not store_item("Magnetic Bib 3-Pack - re-loved", "Magnetic Me").is_clothing
    assert not store_item("Bamboo Swaddle - Moonlight", "Posh Peanut").is_clothing
    assert store_item("Leather Crib Shoes", "Posh Peanut").is_clothing
    assert store_item("Altered Threads Overshirt - Multi Blanket Stripe", "Brixton").is_clothing
    assert not store_item("Sherpa Throw Blanket", "Barefoot Dreams").is_clothing
    # model names at one-garment stores, hats, bags (2026-11-25)
    assert store_item("THE LUNA", "Joe's Jeans").clothing_tags == ["Bottoms"]
    assert store_item("MORRISON", "Clae").clothing_tags == ["Footwear"]
    assert store_item("Seager x WSL Trestles Pro Snapback Blue", "Seager").clothing_tags == ["Accessories"]
    assert store_item("Goldmine Boardshort Duck Camo", "Seager").clothing_tags == ["Swimwear"]
    assert store_item("Ion Weekender", "Mack Weldon").clothing_tags == ["Accessories"]
    assert not store_item("Large Leather Belted Duffle", "Fear of God").is_clothing
    assert store_item("Wool Duffle Coat - Camel", "Todd Snyder").is_clothing


def test_shopify_titles_lose_markup():
    p = {"title": "Hawaiian <span> Red Tiger </span>", "handle": "h", "product_type": "Shirts", "tags": [],
         "variants": [{"price": "50.00", "compare_at_price": "100.00", "available": True}]}
    assert shopify._product_item("Freenote Cloth", "freenotecloth.com", p).title == "Freenote Cloth: Hawaiian Red Tiger"


def test_end_dates_from_deal_text():
    import ends
    from datetime import datetime
    posted = datetime(2026, 11, 26, 17, 0, tzinfo=ends.ET)  # Thanksgiving afternoon

    def day(title, summary=""):
        d = ends.find_end(title, posted, summary)
        return d.astimezone(ends.ET).strftime("%m/%d") if d else None
    assert day("L.L.Bean 15% Off Cyber Deal Sale - Ends 12/1 $33.14") == "12/01"
    assert day("Gap 50% to 60% OFF Sitewide ends November 27 at 11:59 PM Pacific") == "11/27"
    assert day("Sale", "price is valid through December 20, 2026") == "12/20"
    assert day("Target Deals of the Day 11/22-11/27") == "11/27"
    assert day("Stio: Up To 30% Off | Holiday Sale 11/23 - 11/30") == "11/30"
    assert day("Church's Texas Chicken 8 pc for $4.99 11/30 Only") == "11/30"
    assert day("Fanatics Daily Deals", "Today only, Fanatics is taking 50% off") == "11/26"
    assert day("Laura Geller Sale", "Through 4:59 pm ET today, November 26th, head to Laura Geller") == "11/26"
    assert day("tentree: Cyber Monday Ends Dec 1: Up to 60% off Sitewide") == "12/01"
    assert day("Voormi: Black Friday / Ends Cyber Monday 50% Off Puffy Jackets") == "11/30"
    assert day("Nike sale ends Sunday") == "11/29"
    # a title's date beats the summary's (daily-deal threads list earlier deals and their dates)
    assert day("Target Deals of the Day 11/22-11/27", "40% Off Sweatshirts for All Expires Nov 22") == "11/27"
    # a stated date beats relative words ("free shipping ends today" in a Nov 29 sale)
    assert day("Under Armour Hoodies", "Through November 29th, score hoodies. Free shipping ends today") == "11/29"
    # not end dates
    for t in ["You don't need to wait until Black Friday to save 40%", "Up to 60% Off Hoodies + Last Day for FREE Shipping",
              "Order by 12/20 for Christmas delivery", "FS Live 11/26 1AM CT: Bissell vacuum", "Decor 3-5 piece set $20",
              "Nike 1/4 Zip Pullover $25", "Sizes 8-10 boys jeans", "Use by 1/31 for 20% off"]:
        assert day(t) is None, t


def test_ended_deals_are_removed_and_ends_kept():
    from datetime import timedelta
    from models import NOW
    old = Item(title="Today Only Ann Taylor 50% Off Everything", link="x/ann", source="Slickdeals: ann taylor",
               kind="deal", published=(NOW - timedelta(days=3)).isoformat(), age_days=3)
    live = Item(title="Women's Puffer Jacket $40 - ends in 2 days", link="x/puffer", source="Slickdeals: puffer",
                kind="deal", published=NOW.isoformat())
    dn = Item(title="Columbia Fleece Jacket $25", link="x/dn", source="DealNews Coats", kind="deal",
              published=NOW.isoformat(), expires=(NOW + timedelta(hours=20)).strftime("%a, %d %b %Y %H:%M:%S +0000"))
    filler = Item(title="Rubbermaid 44-Piece Food Storage Set $20", link="x/rb", source="DealNews", kind="deal",
                  published=NOW.isoformat(), expires=(NOW + timedelta(days=90)).isoformat())  # DealNews's default
    kept = scoring.process([old, live, dn, filler])
    assert old not in kept and live in kept and dn in kept
    assert filler in kept and filler.expires == ""
    assert live.expires and dn.expires.endswith("+00:00")  # stored as UTC ISO for the page
    scoring.score_all(kept)
    assert "ending" in dn.flags  # ends within 36 hours


def test_first_seen_from_history():
    import history
    hist = {"items": {}, "promos": {}, "runs": ["2026-11-18T17:30:00+00:00"]}
    a = Item(title="Jacket", link="x/a", source="Brand store: Filson", kind="deal", history_key="filson.com:a")
    history.apply(hist, [a])
    assert a.first_seen and hist["items"]["filson.com:a"]["first"] == a.first_seen
    hist["items"]["filson.com:a"]["first"] = "2026-11-20T05:00:00+00:00"
    b = Item(title="Jacket", link="x/a", source="Brand store: Filson", kind="deal", history_key="filson.com:a")
    history.apply(hist, [b])
    assert b.first_seen == "2026-11-20T05:00:00+00:00"


def test_watching_list():
    # owner's picks (config.WATCH, 2026-11-26): Air Force 1s and Nintendo Switch 2
    assert mk("Nike Men's Air Force 1 '07 Shoes (White) $75 + Free Shipping").watch == ["Air Force 1"]
    assert mk("Nike AF1 Low Women's Sneakers $68").watch == ["Air Force 1"]
    assert mk("Mario Kart World (Nintendo Switch 2) $60").watch == ["Nintendo Switch 2"]
    assert mk("Costco Members: 256GB Nintendo Switch 2 Console + Mario Kart World Bundle $400").watch == ["Nintendo Switch 2"]
    for t in ["Leviton Decora Light Switch 2-Pack $9", "TP-Link 8-Port Gigabit Network Switch 2 Pack $30",
              "Super Mario Galaxy (Nintendo Switch) $30", "Air Force One (4K Blu-ray) $10"]:
        assert mk(t).watch == [], t
    # Detroit teams and team-gear store sales (2026-11-26)
    assert mk("Nike Men's Detroit Lions Amon-Ra St. Brown Game Jersey $90").watch == ["Detroit gear"]
    assert mk("New Era Detroit Tigers 59FIFTY Fitted Hat $25").watch == ["Detroit gear"]
    assert mk("Red Wings NHL Reverse Retro Hoodie $45").watch == ["Detroit gear"]
    for t in ["LSU Tigers Football Hoodie $30", "Penn State Nittany Lions Tee $15", "Detroit Axle Front Brake Kit $60",
              "Red Wing Heritage Iron Ranger Boots $250", "Engine Pistons Set for Honda $80"]:
        assert "Detroit gear" not in mk(t).watch, t
    fan = mk("Fanatics Black Friday NFL Jerseys Sale: Up to Extra 60% off + shipping varies")
    assert fan.watch == ["Team gear sales"] and fan.is_clothing
    assert mk("Fanatics - $100 Gift Card [Digital] at BestBuy $85").watch == []
    # brand stores: Detroit items at team-gear stores, every item at Detroit stores, team-gear stores' promos
    assert store_item("Detroit Tigers Clean Up", "47 Brand").watch == ["Detroit gear"]
    assert store_item("Chicago Cubs Clean Up", "47 Brand").watch == []
    assert store_item("DCFC Home Jersey", "Detroit City FC").watch == ["Detroit gear"]
    assert store_item("47 Brand Oversized DETROIT Crew- Maroon", "Detroit City FC").watch == ["Detroit gear"]
    promo = Item(title="47 Brand sitewide: 30% off everything", link="x/47", source="Brand store: 47 Brand",
                 kind="deal", store="47 Brand", flags=["sitewide_promo"])
    promo.brands = ["47 Brand"]
    scoring.classify(promo)
    assert promo.watch == ["Team gear sales"]
    # second-level filters on the Watching tab (config.WATCH_SUB)
    assert store_item("DETROIT TIGERS '47 HITCH", "47 Brand").watch_tags == ["Tigers"]
    assert store_item("DCFC Patch Hat- Black", "Detroit City FC").watch_tags == ["Detroit City FC"]
    assert store_item("Ink Detroit Retro Cloverleaf T-Shirt", "Ink Detroit").watch_tags == ["Other Detroit"]
    assert mk("Costco Members: 256GB Nintendo Switch 2 Console + Mario Kart World Bundle $400").watch_tags == ["Consoles & bundles"]
    assert mk("$92.99: Samsung P9 Express microSDXC 512GB for Nintendo Switch 2 at Amazon").watch_tags == ["Accessories"]
    assert mk("Donkey Kong Bananza (Nintendo Switch 2 Digital) - $30 @ Walmart").watch_tags == ["Games & other"]
    assert mk("Fanatics MLB Black Friday Sale: Up to Extra 60% off").watch_tags == ["MLB"]
    assert promo.watch_tags == ["Store-wide"]
    assert mk("Nike Men's Air Force 1 '07 Shoes $75").watch_tags == []  # no sub-filters (the gender switch covers it)
    # watched deals always make the page, even a low-scoring non-clothing one
    def item(n, source, store, score, watch=()):
        it = Item(title=f"{store} {n}", link=f"x/{store}/{n}", source=source, kind="deal", store=store)
        it.score, it.watch = score, list(watch)
        return it
    deals = [item(n, "Slickdeals: tv", "Amazon", 100 - n * 0.01) for n in range(500)]
    low = item(0, "Slickdeals: switch 2", "Walmart", 3, ["Nintendo Switch 2"])
    page = scoring.pick_for_page(deals + [low], max_deals=100, feed_slots=60, per_store=4)
    assert low in page and len(page) == 100


def test_page_slots_keep_feed_deals():
    # 205 brand stores' markdowns outscored everything and pushed feed and non-clothing deals off the page (2026-11-25)
    def item(n, source, store, score):
        it = Item(title=f"{store} item {n}", link=f"x/{store}/{n}", source=source, kind="deal", store=store)
        it.score = score
        return it
    stores = [item(n, f"Brand store: S{s}", f"S{s}", 150 - n) for s in range(50) for n in range(20)]  # 1,000 items
    feed = [item(n, "Slickdeals: tv", "Amazon", 60 - n * 0.01) for n in range(500)]
    page = scoring.pick_for_page(stores + feed, max_deals=600, feed_slots=300, per_store=4)
    per = {}
    for i in page:
        if i.source.startswith("Brand store"):
            per[i.store] = per.get(i.store, 0) + 1
    assert len(page) == 600 and max(per.values()) <= 4
    assert sum(1 for i in page if not i.source.startswith("Brand store")) == 400  # 300 reserved + 100 left by stores
    # with few feed deals, the stores get the room
    page = scoring.pick_for_page(stores + feed[:50], max_deals=600, feed_slots=300, per_store=20)
    assert len(page) == 600 and sum(1 for i in page if not i.source.startswith("Brand store")) == 50


def test_ordinary_words_are_not_brands():
    # brand names that are ordinary words, from the 2026-11-25 searches and stores
    for t in ["Guess Who? Classic Board Game $9", "Champion Spark Plugs 4-Pack $12",
              "Jeep Wrangler All-Weather Floor Mats $80", "Loft Bed with Desk and Storage $199",
              "Dr Pepper 12-Pack $5", "Orvis Clearwater Fly Rod $199"]:
        assert not mk(t).is_clothing, t
    for t in ["Champion Men's Reverse Weave Hoodie $25", "Wrangler Men's Relaxed Fit Jeans $13",
              "GUESS Women's Puffer Jacket $60", "LOFT 50% off everything", "Orvis Men's Flannel Shirt $40"]:
        assert mk(t).is_clothing, t


def test_baseline_lookup():
    assert BR.baseline_for(["Patagonia"]) == 10
    assert BR.baseline_for([], "Old Navy") == 50
    assert BR.baseline_for([]) == BR.DEFAULT_BASELINE


def test_ordinary_word_brands_need_context():
    # all seen on the live Clothing tab 2026-11-18
    for t in ["[SnS, AC] $11.61 | 4-Pk 80-Count Lysol Disinfecting Wipes (Lavender + Mango) at Amazon",
              "GOOLOO 12V 4500A Portable Car Battery Jump Starter (up to 10L Gas or 8L Diesel) w/ Quick Charge $50",
              "BougeRV 5KW All-in-One Portable Diesel Parking Heater w/ APP Control & Timer $139",
              "$49.47 Keurig K-Express Essentials Single-Serve K-Cup Pod Coffee Maker",
              "[Resale] $403.63 | Breville BES870XL Barista Express Espresso Machine",
              "Today only: PNY's Switch 2-compatible 890MB/s Express microSD card starts at just $30"]:
        it = mk(t)
        assert not it.is_clothing and not ({"Diesel", "Mango", "Express"} & set(it.brands)), t
    # the brands still count when the deal is about them
    assert "Express" in mk("Express: Extra 50% Off Clearance + Free Shipping").brands
    assert mk("Mango Black Friday Sale: 30% off everything").is_clothing
    d = mk("Diesel Men's Larkee Straight Jeans $49 (reg $128)")
    assert d.is_clothing and "Diesel" in d.brands


def test_garment_words_in_other_senses():
    for t in ["CINCOM Heat & Compression Leg Massager CM-102A (Red) $64.99 + Free Shipping",
              "[Prime] NDYIN N80 Portable Wireless Bluetooth Thermal Printer $27.92 + Free Shipping",
              "[AC] $297.99 | Meta Quest 3S 128GB | VR Headset — Golf+ Included — Tee Off in VR at Amazon",
              "Calterm UV Black 100 Pack 7 in. Nylon Cable Tie - down 47.36% ($3.14) to $3.49 from $6.63",
              "Rechargeable Laser Tag Set 4 Pack, No Vest Needed, Kids Adults Game $90",
              "$1.99 | The Blade Itself by Joe Abercrombie (Kindle ebook)"]:
        assert not mk(t).is_clothing, t
    for t in ["Under Armour Men's HeatGear Compression T-Shirt $20", "Men's Heated Puffer Vest w/ Battery Pack $35.99",
              "Smartwool Men's Classic Thermal Merino Base Layer Crew $60 (reg $100)"]:
        assert mk(t).is_clothing, t


def test_slickdeals_store_names():
    from feeds import sd_store
    slug = lambda s: f'<a href="https://slickdeals.net/click?trd=x" data-store-slug="{s}">x</a>'
    assert sd_store(slug("amazon"), "ShuYang US via Amazon [amazon.com] has for Prime Members: ...") == "Amazon"
    assert sd_store(slug("dicks-sporting-goods"), "Dick's Sporting Goods [dickssportinggoods.com] has ...") == \
        "Dick's Sporting Goods"
    assert sd_store(slug("macys"), "Macy's has select ...") == "Macy's"
    assert sd_store(slug("nike-store"), "Nike [nike.com] has ...") == "Nike"
    assert sd_store(slug("finish-line"), "Finishline.com has ...") == "Finish Line"
    assert sd_store(slug("nordstrom-rack"), "Nordstrom Rack has ...") == "Nordstrom Rack"
    assert sd_store(slug("jos-a-bank"), "Jos. A. Bank [josbank.com] has ...") == "Jos. A. Bank"  # description's spelling
    assert sd_store(slug("kemimoto"), "") == "Kemimoto"
    assert sd_store("", "Best Buy has the HP OmniBook X Flip 14 inch laptop") == "Best Buy"
    assert sd_store("", "Woot! has ...") == "Woot"
    assert sd_store("", "Black Friday has arrived early") == ""
    assert sd_store("", "Use promocode SNL3LS64 at checkout") == ""


def test_slickdeals_store_from_feed():
    from feeds import parse_feed
    xml = ('<?xml version="1.0"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>'
           '<title>Nike Air Max 95 $109.99</title><link>https://slickdeals.net/f/20330001-nike-air-max-95</link>'
           '<description><![CDATA[Foot Locker [footlocker.com] has Nike Men\'s Air Max 95 for $109.99.]]></description>'
           '<content:encoded><![CDATA[<div>Thumb Score: +12 </div><a href="https://slickdeals.net/click?trd=Foot%20Locker" '
           'data-store-slug="foot-locker">Foot Locker</a>]]></content:encoded>'
           '<pubDate>Thu, 19 Nov 2026 02:47:19 +0000</pubDate></item></channel></rss>').encode()
    it = parse_feed(xml, "Slickdeals Frontpage", "deal", 10)[0]
    assert it.store == "Foot Locker" and it.votes == 12 and it.thread_id == "20330001"


def test_store_name_cleanup():
    assert scoring.tidy_store("Woot! An Amazon Company") == "Woot"
    assert scoring.tidy_store("Best Buy Locations") == "Best Buy"
    assert scoring.tidy_store("Newegg ahead of Black Friday") == "Newegg"
    assert scoring.tidy_store("adidas") == "adidas" and scoring.tidy_store("Bed Bath and Beyond") == "Bed Bath and Beyond"
    assert mk("Men's Macrolux Heavy Puffer Jacket (3 Colors) $24.99 at 32 Degrees").store == "32 Degrees"
    # the words before "[amazon.com]" aren't always the store
    assert mk("Arc'teryx Beta SV Jacket Women's $568.01", "Color: Black, Small [amazon.com] has it").store == "Amazon"
    # Hip2Save "on Amazon" / "on Macys.com"; spelling variants fold together
    assert mk("Cozy Washable Slippers Only $9.34 on Amazon (Reg. $26)").store == "Amazon"
    assert mk("Electric Towel Warmer Just $44.99 Shipped on Macys.com (Reg. $149)").store == "Macy's"
    assert mk("Jacket $40 on Sale for Members").store == ""
    assert scoring.tidy_store("Joes New Balance Outlet") == scoring.tidy_store("Joe's New Balance Outlet")


def test_brand_display_names_and_baseline_reason():
    assert mk("Levi's 501 Jeans $30 (reg $70)").brands == ["Levi's"]  # str.title() gave "Levi'S"
    assert scoring.brand_title("j.crew") == "J.Crew" and scoring.brand_title("h&m") == "H&M"
    assert scoring.brand_title("rei") == "REI" and scoring.brand_title("dick's sporting goods") == "Dick's Sporting Goods"
    # the no-name baseline isn't Amazon's usual sale
    it = mk("ZITY Men's Plaid Flannel Hoodie Shirt Jacket $14.99 (reg $29.99)", store="Amazon")
    assert not any("Amazon's usual" in r for r in it.reasons) and it.pct_off == 50
    assert any("Old Navy's usual" in r for r in mk("Old Navy Puffer Jacket 80% off").reasons)


def test_department_store_does_not_make_items_unisex():
    import gender as G
    assert G.detect("Charter Club Cashmere Sweater $40", store="Macy's") == []
    assert G.detect("Macy's Black Friday Sale: 50% off", store="Macy's", has_garment=False) == ["Everyone"]
    # a brand that sells to everyone is weaker than a description naming one audience
    assert G.detect("Nike Air Max 95 $109.99", "Foot Locker has the Nike Men's Air Max 95", brands=["Nike"]) == ["Men's"]
    assert G.detect("Nike Air Max 95 $109.99", brands=["Nike"]) == ["Everyone"]


def test_promo_menus_ranges_and_nav():
    menu = ('<ul class="filters"><li><a>20% Off Sale 30% Off Sale 40% Off Sale 50% Off Sale 60% Off Sale '
            '70% Off Sale</a></li></ul>')
    assert shopify.promo_from_html(menu)[1] == 0  # a filter menu is not a 70% sale (Faithfull, 2026-11-18)
    tiered = '<div class="bar"><p>Black Friday: 30% off $100, 40% off $200, 50% off $300</p></div>'
    assert shopify.promo_from_html(tiered)[1] == 50
    snippet, pct, up_to, _ = shopify.promo_from_html('<div class="bar"><p>70-80% Off Items Online Warehouse Sale</p></div>')
    assert pct == 80 and up_to
    assert shopify._tidy("UP TO 80% OFF Our biggest Black Friday ever No code needed. SHOP: ALL SWIM SHOP: APPAREL") == \
        "UP TO 80% OFF Our biggest Black Friday ever No code needed"
    assert shopify._tidy("BLACK FRIDAY 30% OFF SITEWIDE Early holiday shopping starts now. SHOP WINTER ARRIVALS") == \
        "BLACK FRIDAY 30% OFF SITEWIDE Early holiday shopping starts now"


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
