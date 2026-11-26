"""
Brand knowledge used by the scoring logic.

BASELINE: the discount a brand offers on a normal day, roughly. A deal's
"excess discount" (deal % minus baseline) is what makes it special: 40% off
Patagonia is rarer than 60% off Old Navy, which runs that most weeks.

PREMIUM: brands that rarely discount and hold resale value. They get a quality bonus.

SHOPIFY_STORES: clothing brands whose Shopify storefront exposes
/products.json, so we can read real price vs compare-at price, plus stock.
"""

DEFAULT_BASELINE = 25          # unknown brands
GENERIC_BASELINE = 35          # no-name Amazon-style listings are perpetually "on sale"

BASELINE = {
    # always-on-sale mall & factory brands
    "old navy": 50, "gap factory": 50, "gap": 40, "banana republic factory": 55, "banana republic": 35,
    "j.crew factory": 55, "j.crew": 35, "jcpenney": 55, "kohl's": 45, "macy's": 45, "express": 45,
    "american eagle": 35, "aerie": 35, "aeropostale": 55, "the children's place": 55, "carter's": 50,
    "nautica": 45, "izod": 45, "perry ellis": 45, "jos. a. bank": 60, "men's wearhouse": 45, "loft": 45,
    "ann taylor": 40, "h&m": 30, "shein": 55, "fashion nova": 45, "princess polly": 30, "petal & pup": 40,
    "showpo": 40, "nordstrom rack": 50, "saks off 5th": 55, "calvin klein": 45, "tommy hilfiger": 45,
    "eddie bauer": 45, "lands' end": 45, "lands end": 45, "robert graham": 35, "bonobos": 30,
    "steve madden": 30, "skechers": 30, "crocs": 30, "under armour": 35, "adidas": 35, "puma": 35,
    "reebok": 40, "columbia": 30, "sorel": 30, "merrell": 25, "timberland": 25, "levi's": 30, "wrangler": 30,
    "ralph lauren": 30, "polo ralph lauren": 30, "abercrombie": 25, "hollister": 30, "zara": 20,
    "macys": 45, "kohls": 45, "nordstrom": 30, "dsw": 30, "famous footwear": 35, "cupshe": 40,
    # moderate
    "nike": 25, "new balance": 25, "the north face": 20, "north face": 20, "rei": 20, "uniqlo": 15,
    "everlane": 20, "allbirds": 25, "todd snyder": 25, "taylor stitch": 15, "faherty": 20, "rhone": 15,
    "mack weldon": 25, "untuckit": 25, "naadam": 25, "kotn": 25, "vessi": 25, "nisolo": 20, "kizik": 15,
    "set active": 20, "saxx": 20, "unbound merino": 15, "wool&prince": 15, "cotopaxi": 20, "ugg": 15,
    "dr. martens": 20, "dr martens": 20, "hoka": 10, "asics": 25, "brooks": 20, "saucony": 25,
    "ll bean": 15, "l.l.bean": 15, "smartwool": 20, "darn tough": 10, "marine layer": 20, "outerknown": 20,
    "chubbies": 25, "true classic": 25, "cuts": 15, "johnnie-o": 20, "southern tide": 20, "billy reid": 25,
    "frank and oak": 30, "ministry of supply": 25, "girlfriend collective": 15, "beyond yoga": 20,
    "summersalt": 25, "birdies": 20, "beckett simonon": 20, "koio": 20, "oliver cabell": 20, "xero shoes": 20,
    "olukai": 15, "tecovas": 5, "thursday boots": 10, "rothy's": 10, "knix": 20, "tommy john": 20,
    "negative underwear": 15, "universal standard": 25, "naked & famous": 15, "iron & resin": 20,
    "roark": 20, "howler brothers": 20, "ronhill": 30, "janji": 20, "satisfy": 10, "district vision": 15,
    "topo designs": 20, "toad&co": 25, "sunday afternoons": 20, "jachs": 40, "duer": 20, "comfrt": 30,
    "rails": 25, "mott & bow": 25, "taft": 20, "representclo": 10, "represent": 10, "gymshark": 25,
    # rarely discounted
    "patagonia": 10, "arc'teryx": 5, "arcteryx": 5, "canada goose": 0, "moncler": 0, "lululemon": 10,
    "vuori": 10, "on running": 0, "on": 0, "birkenstock": 5, "aime leon dore": 0, "aimé leon dore": 0,
    "kith": 10, "fear of god": 0, "stussy": 0, "noah": 5, "filson": 10, "barbour": 10, "alo yoga": 10,
    "alo": 10, "reigning champ": 15, "quince": 0, "skims": 5, "fjallraven": 15, "outdoor voices": 20,
    "apple": 10, "dyson": 15, "yeti": 10, "stanley": 15, "sony": 20, "bose": 20, "samsung": 25, "lego": 15,
    # added 2026-11-18 with the new brand stores
    "hill house home": 15, "christy dawn": 20, "faithfull the brand": 25, "meshki": 30, "oh polly": 30, "wildfang": 30,
    "kirrin finch": 20, "andie": 25, "montce": 25, "lake pajamas": 10, "cozy earth": 15, "barefoot dreams": 20,
    "splits59": 20, "year of ours": 20, "naked cashmere": 20, "white + warren": 25, "jenni kayne": 10,
    "motel rocks": 35, "loveshackfancy": 20, "agolde": 10, "mother": 15, "staud": 20, "solid & striped": 30,
    "edikted": 40, "frame": 15, "dl1961": 30, "citizens of humanity": 10, "re/done": 15, "cuyana": 5,
    "m.m.lafleur": 20, "rebecca minkoff": 30, "freda salvador": 20, "loeffler randall": 20, "thousand fell": 25,
    "sarah flint": 20, "margaux": 10, "greats": 30, "feetures": 15, "stance": 20, "taos footwear": 25, "toms": 35,
    "native shoes": 30, "primary": 30, "kyte baby": 10, "little sleepies": 15, "tea collection": 40, "pangaia": 25,
    "tentree": 30, "peter manning": 20, "stio": 15, "duckworth": 15, "bearbottom": 30, "linksoul": 20, "ibex": 15,
    "outdoor research": 20,
    # added 2026-11-25 with the new brand stores (rough; unlisted ones use DEFAULT_BASELINE, and the page also
    # compares each item with that store's own typical markdown)
    "ulla johnson": 15, "anine bing": 15, "nili lotan": 10, "doen": 15, "rogue territory": 5, "freenote cloth": 10,
    "grant stone": 10, "velasca": 15, "schott nyc": 15, "nobis": 15, "voormi": 15, "mara hoffman": 20,
    "joe's jeans": 40, "hudson jeans": 35, "sanctuary": 35, "burt's bees baby": 40, "tiger mist": 35,
    "show me your mumu": 30, "psycho bunny": 30, "travismathew": 25, "good american": 25, "alice + olivia": 25,
}

PREMIUM = {
    "patagonia", "arc'teryx", "arcteryx", "canada goose", "moncler", "lululemon", "vuori", "on running",
    "hoka", "birkenstock", "aime leon dore", "aimé leon dore", "kith", "fear of god", "stussy", "noah",
    "filson", "barbour", "todd snyder", "taylor stitch", "faherty", "buck mason", "rhone", "alo yoga",
    "alo", "everlane", "allbirds", "the north face", "north face", "cotopaxi", "thursday boots", "tecovas",
    "rothy's", "naadam", "ugg", "dr. martens", "dr martens", "ralph lauren", "polo ralph lauren", "levi's",
    "reigning champ", "fjallraven", "outerknown", "marine layer", "darn tough", "smartwool", "skims",
    "new balance", "nike", "adidas", "apple", "dyson", "yeti", "sony", "bose", "lego", "quince", "uniqlo",
    "agolde", "mother", "frame", "citizens of humanity", "staud", "loveshackfancy", "jenni kayne", "cuyana",
    "christy dawn", "hill house home", "sarah flint", "margaux", "stio", "ibex", "naked cashmere", "barefoot dreams",
    "cozy earth", "outdoor research",
    "ulla johnson", "anine bing", "nili lotan", "doen", "rogue territory", "freenote cloth", "grant stone", "schott nyc",
    "madewell", "j.crew", "carhartt", "columbia", "ll bean", "l.l.bean", "rei",
}

# Clothing brands running Shopify storefronts with an open /products.json.
# Verified working Nov 2026. Display name -> domain.
SHOPIFY_STORES = {
    "Todd Snyder": "toddsnyder.com", "Bonobos": "bonobos.com", "Taylor Stitch": "taylorstitch.com",
    "Faherty": "fahertybrand.com", "Everlane": "everlane.com", "Allbirds": "allbirds.com",
    "Cotopaxi": "cotopaxi.com", "Kith": "kith.com", "Aimé Leon Dore": "aimeleondore.com",
    "Alo Yoga": "aloyoga.com", "Steve Madden": "stevemadden.com", "Thursday Boots": "thursdayboots.com",
    "Rothy's": "rothys.com", "Filson": "filson.com", "Mack Weldon": "mackweldon.com", "Untuckit": "untuckit.com",
    "Naadam": "naadam.co", "Kotn": "kotn.com", "Vessi": "vessi.com", "Nisolo": "nisolo.com", "Kizik": "kizik.com",
    "Set Active": "setactive.co", "SAXX": "saxxunderwear.com", "Unbound Merino": "unboundmerino.com",
    "Wool&Prince": "woolandprince.com", "Marine Layer": "marinelayer.com", "Outerknown": "outerknown.com",
    "Chubbies": "chubbiesshorts.com", "True Classic": "trueclassictees.com", "Cuts": "cutsclothing.com",
    "Johnnie-O": "johnnie-o.com", "Southern Tide": "southerntide.com", "Billy Reid": "billyreid.com",
    "Frank And Oak": "frankandoak.com", "Ministry of Supply": "ministryofsupply.com",
    "Girlfriend Collective": "girlfriend.com", "Beyond Yoga": "beyondyoga.com", "Summersalt": "summersalt.com",
    "Birdies": "birdies.com", "Beckett Simonon": "beckettsimonon.com", "Koio": "koio.co",
    "Oliver Cabell": "olivercabell.com", "Xero Shoes": "xeroshoes.com", "Olukai": "olukai.com",
    "Tecovas": "tecovas.com", "Knix": "knix.com", "Tommy John": "tommyjohn.com",
    "Negative Underwear": "negativeunderwear.com", "Universal Standard": "universalstandard.com",
    "Naked & Famous": "nakedandfamousdenim.com", "Iron & Resin": "ironandresin.com", "Roark": "roark.com",
    "Howler Brothers": "howlerbros.com", "Ronhill": "ronhill.com", "Janji": "janji.com",
    "Satisfy": "satisfyrunning.com", "District Vision": "districtvision.com", "Topo Designs": "topodesigns.com",
    "Toad&Co": "toadandco.com", "Sunday Afternoons": "sundayafternoons.com", "Jachs": "jachsny.com",
    "Duer": "shopduer.com", "Comfrt": "comfrt.com", "Rails": "railsclothing.com", "Mott & Bow": "mottandbow.com",
    "Taft": "taftclothing.com", "Represent": "representclo.com", "Reigning Champ": "reigningchamp.com",
    "Outdoor Voices": "outdoorvoices.com", "Stussy": "stussy.com", "Noah": "noahny.com",
    "Fear of God": "fearofgod.com", "Fashion Nova": "fashionnova.com", "Princess Polly": "us.princesspolly.com",
    "Petal & Pup": "petalandpup.com", "Showpo": "showpo.com", "Cupshe": "cupshe.com", "Robert Graham": "robertgraham.us",
    "Darn Tough": "darntough.com", "Gymshark": "gymshark.com", "Ten Thousand": "tenthousand.cc",
    # added 2026-11-18 after a CI probe (tools/probe_stores.py): women's, shoes, kids, outdoor
    "Hill House Home": "hillhousehome.com", "Christy Dawn": "christydawn.com", "Faithfull the Brand": "faithfullthebrand.com",
    "Meshki": "meshki.us", "Oh Polly": "us.ohpolly.com", "Wildfang": "wildfang.com", "Kirrin Finch": "kirrinfinch.com",
    "Andie": "andieswim.com", "Montce": "montce.com", "Lake Pajamas": "lakepajamas.com", "Cozy Earth": "cozyearth.com",
    "Barefoot Dreams": "barefootdreams.com", "Splits59": "splits59.com", "Year of Ours": "yearofours.com",
    "Naked Cashmere": "nakedcashmere.com", "White + Warren": "whiteandwarren.com", "Jenni Kayne": "jennikayne.com",
    "Motel Rocks": "motelrocks.com", "LoveShackFancy": "loveshackfancy.com", "AGOLDE": "agolde.com",
    "MOTHER": "motherdenim.com", "STAUD": "staud.clothing", "Solid & Striped": "solidandstriped.com",
    "Edikted": "edikted.com", "FRAME": "frame-store.com", "DL1961": "dl1961.com",
    "Citizens of Humanity": "citizensofhumanity.com", "RE/DONE": "shopredone.com", "Cuyana": "cuyana.com",
    "M.M.LaFleur": "mmlafleur.com", "Rebecca Minkoff": "rebeccaminkoff.com", "Freda Salvador": "fredasalvador.com",
    "Loeffler Randall": "loefflerrandall.com", "Thousand Fell": "thousandfell.com", "Sarah Flint": "sarahflint.com",
    "Margaux": "margauxny.com", "Greats": "greats.com", "Feetures": "feetures.com", "Stance": "stance.com",
    "Taos Footwear": "taosfootwear.com", "TOMS": "toms.com", "Native Shoes": "nativeshoes.com",
    "Primary": "primary.com", "Kyte Baby": "kytebaby.com", "Little Sleepies": "littlesleepies.com",
    "Tea Collection": "teacollection.com", "Pangaia": "pangaia.com", "tentree": "tentree.com",
    "Peter Manning": "petermanningnyc.com", "Stio": "stio.com", "Duckworth": "duckworthco.com",
    "Bearbottom": "bearbottomclothing.com", "Linksoul": "linksoul.com", "Ibex": "ibex.com",
    "Outdoor Research": "outdoorresearch.com",
    # added 2026-11-25 after a CI probe (91 of 140 candidates open; these have items on sale; bag-first brands left out)
    "Velasca": "velasca.com", "Kickee Pants": "kickeepants.com", "Ulla Johnson": "ullajohnson.com",
    "Cleobella": "cleobella.com", "Alphalete": "alphaleteathletics.com", "Tiger Mist": "tigermist.com",
    "Bellabu Bear": "bellabubear.com", "Burt's Bees Baby": "burtsbeesbaby.com", "Sanctuary": "sanctuaryclothing.com",
    "Free Fly": "freeflyapparel.com", "Posh Peanut": "poshpeanut.com", "Spiritual Gangster": "spiritualgangster.com",
    "Swiftwick": "swiftwick.com", "Frankies Bikinis": "frankiesbikinis.com", "Magnetic Me": "magneticme.com",
    "Obermeyer": "obermeyer.com", "Anine Bing": "aninebing.com", "TravisMathew": "travismathew.com",
    "Halfdays": "halfdays.com", "Joe's Jeans": "joesjeans.com", "Dolce Vita": "dolcevita.com",
    "Corridor": "corridornyc.com", "Fresh Clean Threads": "freshcleanthreads.com", "Larroude": "larroude.com",
    "Hudson Jeans": "hudsonjeans.com", "Selkie": "selkiecollection.com", "Lisa Says Gah": "lisasaysgah.com",
    "Rabbit": "runinrabbit.com", "Nobis": "nobis.com", "Fair Harbor": "fairharborclothing.com",
    "Daze Denim": "dazedenim.com", "Pistola": "pistoladenim.com", "Pepper": "wearpepper.com", "Ace Marks": "acemarks.com",
    "Flylow": "flylowgear.com", "Mara Hoffman": "marahoffman.com", "Ciele": "cieleathletics.com",
    "Wolf & Shepherd": "wolfandshepherd.com", "Seager": "seagerco.com", "Clae": "clae.com", "Schutz": "schutz-shoes.com",
    "Path Projects": "pathprojects.com", "Beach Riot": "beachriot.com", "Schott NYC": "schottnyc.com",
    "HUF": "hufworldwide.com", "Parade": "yourparade.com", "Ridge Merino": "ridgemerino.com",
    "Nobull": "nobullproject.com", "Grant Stone": "grantstoneshoes.com", "Show Me Your Mumu": "showmeyourmumu.com",
    "Rogue Territory": "rogueterritory.com", "Voormi": "voormi.com", "Nili Lotan": "nililotan.com",
    "Ash & Erie": "ashanderie.com", "Petite Studio": "petitestudionyc.com", "State and Liberty": "stateandliberty.com",
    "Matisse": "matissefootwear.com", "Doen": "shopdoen.com", "Freenote Cloth": "freenotecloth.com",
    "Psycho Bunny": "psychobunny.com", "Monday Swimwear": "mondayswimwear.com", "Kortni Jeane": "kortnijeane.com",
    "Gymreapers": "gymreapers.com", "Varley": "varley.com", "ASTR the Label": "astrthelabel.com",
    "Favorite Daughter": "favoritedaughter.com", "Alice + Olivia": "aliceandolivia.com",
    "Good American": "goodamerican.com", "Brixton": "brixton.com",
}

# Store names that are ordinary words ("price cuts", "bed frame", "Mother's Day", "primary care").
# Their brand-store items know their brand already; these names are NOT matched in deal-site headlines.
AMBIGUOUS_NAMES = {
    "cuts", "represent", "satisfy", "rails", "noah", "taft", "duer", "set active", "comfrt", "knix", "roark", "janji",
    "koio", "birdies", "frame", "mother", "primary", "greats", "stance", "toms", "andie", "montce", "native shoes",
    "ibex", "stio", "duckworth", "margaux", "edikted", "meshki", "wildfang", "on", "alo", "boss", "lee", "keen", "vans",
    "express", "coach", "guess", "champion", "loft", "theory", "vince", "cos", "boss",
    # 2026-11-25 stores: "Dr Pepper", "Rabbit R1", "Macy's Parade", "a good American", "state and liberty"
    "pepper", "rabbit", "parade", "corridor", "sanctuary", "matisse", "brixton", "free fly", "path projects",
    "good american", "state and liberty", "petite studio", "magnetic me", "fair harbor", "selkie", "nobis",
}

# Brand names that are also ordinary words, still matched in headlines but only counted when the title starts with
# the brand ("Express: 50% off everything") or names a garment ("Diesel men's jeans"). Without this, "8L Diesel"
# made a car jump starter clothing, "Lavender + Mango" Lysol wipes, and "Keurig K-Express" a coffee maker (2026-11-18).
# "wrangler" added 2026-11-25 with its Slickdeals search ("Jeep Wrangler" floor mats). Guess, Champion and Keen are
# stricter: AMBIGUOUS_NAMES, never matched in headlines.
CONTEXT_NAMES = {"diesel", "mango", "express", "wrangler"}


# Who a brand mainly sells to (used when a product title doesn't say).
BRAND_AUDIENCE = {
    "Women's": [
        "knix", "summersalt", "universal standard", "princess polly", "petal & pup", "showpo", "girlfriend collective",
        "beyond yoga", "set active", "birdies", "cupshe", "fashion nova", "spanx", "negative underwear", "aritzia",
        "free people", "anthropologie", "athleta", "lane bryant", "torrid", "loft", "ann taylor", "chico's", "j.jill",
        "aerie", "lulus", "reformation", "white house black market", "eloquii", "kate spade", "tory burch",
        "michael kors", "sam edelman", "victoria's secret", "intimissimi", "cuup", "parade", "andie",
        "hill house home", "christy dawn", "faithfull the brand", "meshki", "oh polly", "wildfang", "kirrin finch",
        "montce", "splits59", "year of ours", "naked cashmere", "white + warren", "jenni kayne", "motel rocks",
        "loveshackfancy", "agolde", "mother", "staud", "solid & striped", "edikted", "re/done", "cuyana",
        "m.m.lafleur", "rebecca minkoff", "freda salvador", "loeffler randall", "sarah flint", "margaux", "taos footwear",
        "ulla johnson", "cleobella", "tiger mist", "sanctuary", "spiritual gangster", "frankies bikinis", "anine bing",
        "halfdays", "dolce vita", "larroude", "selkie", "lisa says gah", "daze denim", "pistola", "pepper",
        "mara hoffman", "schutz", "beach riot", "show me your mumu", "nili lotan", "petite studio", "matisse", "doen",
        "monday swimwear", "kortni jeane", "varley", "astr the label", "favorite daughter", "alice + olivia",
        "good american",
    ],
    "Men's": [
        "todd snyder", "bonobos", "mack weldon", "untuckit", "saxx", "true classic", "cuts", "chubbies", "johnnie-o",
        "robert graham", "jachs", "iron & resin", "howler brothers", "naked & famous", "beckett simonon",
        "oliver cabell", "taft", "ten thousand", "jos. a. bank", "jos a bank", "men's wearhouse", "taylor stitch",
        "buck mason", "peter millar", "rhone", "mizzen+main", "proper cloth", "suitsupply", "indochino",
        "billy reid", "roark", "wool&prince", "aimé leon dore", "aime leon dore", "huckberry", "duluth trading",
        "peter manning", "bearbottom", "linksoul",
        "velasca", "travismathew", "corridor", "fresh clean threads", "ace marks", "seager", "path projects", "huf",
        "grant stone", "rogue territory", "ash & erie", "state and liberty", "freenote cloth", "psycho bunny",
        "gymreapers",
    ],
    "Everyone": [
        "comfrt", "noah", "alo yoga", "alo", "kith", "stussy", "fear of god", "represent", "gymshark", "allbirds",
        "vessi", "kizik", "xero shoes", "koio", "everlane", "faherty", "naadam", "kotn", "outerknown", "marine layer",
        "cotopaxi", "filson", "olukai", "tecovas", "thursday boots", "nisolo", "duer", "ministry of supply",
        "unbound merino", "topo designs", "toad&co", "district vision", "satisfy", "janji", "ronhill",
        "sunday afternoons", "darn tough", "rails", "mott & bow", "tommy john", "frank and oak", "outdoor voices",
        "reigning champ", "rothy's", "skims", "steve madden", "uniqlo", "old navy", "gap", "gap factory",
        "banana republic", "banana republic factory", "j.crew", "j.crew factory", "eddie bauer", "lands' end",
        "ll bean", "l.l.bean", "columbia", "the north face", "patagonia", "arc'teryx", "levi's", "nordstrom",
        "nordstrom rack", "macy's", "kohl's", "rei", "abercrombie", "american eagle", "h&m", "zara", "express",
        "carhartt", "under armour", "nike", "adidas", "new balance", "puma", "hoka", "on running", "lululemon", "vuori",
        "lake pajamas", "cozy earth", "barefoot dreams", "frame", "dl1961", "citizens of humanity", "thousand fell",
        "greats", "feetures", "stance", "toms", "native shoes", "pangaia", "tentree", "stio", "duckworth", "ibex",
        "outdoor research",
        "alphalete", "free fly", "swiftwick", "obermeyer", "joe's jeans", "hudson jeans", "rabbit", "nobis",
        "fair harbor", "flylow", "ciele", "wolf & shepherd", "clae", "schott nyc", "parade", "ridge merino", "nobull",
        "voormi", "brixton", "southern tide",
    ],
}
BRAND_AUDIENCE["Kids"] = ["primary", "kyte baby", "little sleepies", "tea collection", "carter's",
                          "the children's place", "hanna andersson", "janie and jack", "gymboree",
                          "kickee pants", "bellabu bear", "burt's bees baby", "posh peanut", "magnetic me", "oshkosh",
                          "oshkosh b'gosh"]
_AUDIENCE = {b: aud for aud, names in BRAND_AUDIENCE.items() for b in names}


def audience_for(brands: list[str], store: str = "") -> str | None:
    for b in brands + ([store] if store else []):
        a = _AUDIENCE.get(norm_brand(b))
        if a and a != "Everyone":
            return a  # a single-audience brand is the most specific evidence
    for b in brands + ([store] if store else []):
        if _AUDIENCE.get(norm_brand(b)) == "Everyone":
            return "Everyone"
    return None


def norm_brand(b: str) -> str:
    return b.lower().replace("’", "'").strip()


def baseline_for(brands: list[str], store: str = "", generic: bool = False) -> int:
    cands = [norm_brand(x) for x in brands + ([store] if store else [])]
    vals = [BASELINE[c] for c in cands if c in BASELINE]
    if vals:
        return min(vals)  # the rarest-discounting brand mentioned sets the bar
    return GENERIC_BASELINE if generic else DEFAULT_BASELINE


def is_premium(brands: list[str], store: str = "") -> bool:
    return any(norm_brand(x) in PREMIUM for x in brands + ([store] if store else []))
