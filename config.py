"""
Deal Scout configuration: sources, keyword lists, and scoring knobs.
Edit this file to add/remove feeds, brands, or tune the clothing bias.
"""

# ---------------------------------------------------------------------------
# Watching (owner's pick, 2026-11-26): every deal whose title matches gets the "👀 Watching" tab and a badge, and
# is always kept on the page (exempt from the page-slot and minimum-score cuts). Ranking is unchanged. To watch
# something else, add (label, regex) here and a matching Slickdeals search below. Not alerts: the owner declined
# watch-list alerts on 2026-11-18.
# ---------------------------------------------------------------------------
WATCH = [
    ("Air Force 1", r"\bair\s?force\s?1s?\b|\baf-?1s?\b"),  # not "Air Force One" (the movie, in deal posts)
    # not light/network switches or "Switch 2-Pack"
    ("Nintendo Switch 2", r"(?<!light )(?<!wall )(?<!network )(?<!ethernet )(?<!smart )(?<!toggle )(?<!dimmer )"
                          r"\bswitch\s?2\b(?![-\s]?(?:pack|pk|gang|port|way|count|ct|piece|pcs?)\b)"),
    # Detroit teams (added 2026-11-26): "Detroit Lions", or the team plus its league. Not "Lions"/"Tigers" alone:
    # LSU / Auburn / Clemson Tigers, Penn State Nittany Lions; not "Detroit" alone: Detroit Axle, Detroit Diesel.
    ("Detroit gear", r"\bdetroit\s+(?:lions|tigers|pistons|red\s?wings|city fc)\b|\bdetroit vs\.? everybody\b|"
                       r"\b(?:lions|tigers|pistons|red\s?wings)\b(?=.*\b(?:nfl|mlb|nba|nhl)\b)|"
                       r"\b(?:nfl|mlb|nba|nhl)\b(?=.*\b(?:lions|tigers|pistons|red\s?wings)\b)"),
    # store-wide sales at the team-gear stores (they cover the Detroit teams; deal sites rarely post team-specific gear)
    ("Team gear sales", r"\bfanatics\b(?!.*gift ?card)|\bmitchell\s*(?:&|and)\s*ness\b|\bnfl shop\b|\bmlb shop\b|"
                        r"\bnhl shop\b|\bnba store\b|\b'?47 brand\b"),
    # Gyms (added 2026-11-26, owner: "gym deals, especially ones in NYC", "ones with basketball facilities too"):
    # membership offers from the gyms' own sites (gyms.py, config.GYMS), plus membership and home-gym posts on the deal
    # sites. Not bare "gym": Nike's "Gym Red" colourway, gym bags and gym shoes.
    ("Gym deals", r"(?:GYM_MEMBERSHIP)|(?:GYM_GEAR)"),
]
# Gym memberships and classes, by phrase or chain name. Not "Gold's Gym" (an equipment brand at Walmart), not
# "24 Hour Fitness Tracking" / "Lifetime Fitness Tracker" (watches).
GYM_MEMBERSHIP = (r"\bgym (?:memberships?|pass(?:es)?|day pass(?:es)?)\b|\bfitness (?:memberships?|clubs?|studios?)\b|"
                  r"\b(?:planet fitness|crunch fitness|24[ -]?hour fitness|la fitness|life ?time fitness|anytime fitness|"
                  r"snap fitness|blink fitness|puregym|orangetheory|classpass|ymca|club pilates|corepower yoga|pure barre|"
                  r"solidcore|soulcycle|barry'?s bootcamp|new york sports clubs?|equinox (?:gym|fitness|club|membership))\b"
                  r"(?! track)")
GYM_GEAR = (r"\bhome gym\b|\bpower (?:rack|tower|cage)s?\b|\bsquat (?:rack|stand)s?\b|\bsmith machine\b|\bdumbbells?\b|"
            r"\bkettlebells?\b|\bweight (?:bench|set|plate|vest)(?:e?s)?\b|\b(?:workout|exercise|weight|flat|incline) bench"
            r"(?:es)?\b|\btreadmills?\b|\bwalking pads?\b|\browing machines?\b|\b(?:exercise|spin|stationary|indoor cycling|"
            r"recumbent) bikes?\b|\belliptical(?: machine)?s?\b|"
            r"\bpeloton\b(?!.*\b(?:water bottle|strap|socks?|shoes?|apparel|leggings|tee|shirt|hoodie|bra)\b)|\bbowflex\b|\bnordictrack\b|\bspeediance\b|"
            r"\bcable machines?\b|\bpull[- ]?up (?:bars?|stations?)\b|\bdip stations?\b|\bbarbells?\b(?! apparel)|"
            r"\bbumper plates?\b|\b(?:gym|exercise|workout) (?:floor(?:ing)?|mats?)\b|\bpilates reformers?\b|\bconcept ?2\b|"
            r"\b(?:rogue|rep|titan) fitness\b")
WATCH = [(label, rx.replace("GYM_MEMBERSHIP", GYM_MEMBERSHIP).replace("GYM_GEAR", GYM_GEAR)) for label, rx in WATCH]
# Second-level filters on the Watching tab: (name, regex on the full title), first match wins; "." catches the rest
WATCH_SUB = {
    "Detroit gear": [("Lions", r"\blions\b"), ("Tigers", r"\btigers\b"), ("Pistons", r"\bpistons\b"),
                     ("Red Wings", r"\bred\s?wings\b"), ("Detroit City FC", r"\bdetroit city fc\b|\bdcfc\b"),
                     ("Other Detroit", r".")],
    # not "21-in-1 Accessories Bundle Kit" (an accessory kit); "Nintendo Switch 2 - Black ($391.99)" is the console
    "Nintendo Switch 2": [("Consoles & bundles", r"^(?!.*\baccessor(?:y|ies)\b)(?:.*\b(?:consoles?|bundles?|system)\b|"
                                                 r".*\bswitch 2\s*[-–(]\s*(?:black|white|\d{3}\s?gb)\b)"),
                          ("Accessories", r"accessor|controller|joy-?cons?|micro\s?sd|memory card|\bcases?\b|charger|\bdock\b|"
                                          r"\bgrips?\b|screen protector|headset|\bcables?\b|\bbags?\b|carrying|storage|"
                                          r"\bstand\b|power bank|amiibo|\bhdmi\b"),
                          ("Games & other", r".")],
    "Team gear sales": [("NFL", r"\bnfl\b"), ("MLB", r"\bmlb\b"), ("NBA", r"\bnba\b"), ("NHL", r"\bnhl\b"),
                        ("College", r"\bcollege\b|\bncaa\b"), ("Store-wide", r".")],
    # Overlapping filters (see WATCH_SUB_MULTI): an NYC gym with courts is under NYC, Basketball courts and Memberships.
    # Gym-site offers get their NYC / courts tags from config.GYMS (gyms.py); these regexes cover deal-site posts.
    # Basketball: chains where most clubs have a court (LA Fitness, 24 Hour Fitness Sport clubs, Life Time, the Y, JCCs).
    "Gym deals": [("NYC", r"\bnyc\b|\bnew york\b|\bmanhattan\b|\bbrooklyn\b|\bqueens\b|\bbronx\b|\bstaten island\b|"
                          r"\bharlem\b"),
                  ("Basketball courts", r"basketball|\b(?:24[ -]?hour fitness|la fitness|life ?time fitness|ymca|jcc)\b"),
                  ("Memberships & classes", GYM_MEMBERSHIP), ("Home gym gear", GYM_GEAR)],
}
# Watched things whose second-level filters overlap: every matching filter applies, not just the first
WATCH_SUB_MULTI = {"Gym deals"}
# Sources whose every item is on the Watching list (source name prefix -> label)
WATCH_SOURCES = {"Gym site:": "Gym deals"}
# Cap on watched deals kept regardless of rank; past it they compete for ordinary page slots
MAX_WATCHED = 400
# Names that open a sale headline, for deals with no store (scoring.LEAD_STORE_RE), besides the Slickdeals store slugs
# (feeds.SLUG_NAMES) and brands with a known sale level (brands.BASELINE). Retailers count before a dash too
# ("Sportsmans Warehouse - Darn Tough socks"); brands only before sale words ("Hoka Black Friday Sale"), since
# "Apple - AirPods Pro 3" is usually sold somewhere else. Not "On" (shoe brand): "On Black Friday, ..." is a sentence.
EXTRA_STORES = ["Sportsman's Warehouse", "Sportsmans Warehouse", "Academy Sports", "Bass Pro Shops", "Cabela's",
                "Backcountry", "Moosejaw", "Ulta", "Sephora", "Wayfair", "Newegg", "GameStop", "Staples",
                "Nordstrom", "Neiman Marcus", "Saks Fifth Avenue", "Belk", "Burlington", "TJ Maxx", "Marshalls",
                "Huckberry", "Barnes & Noble"]
EXTRA_BRANDS = ["Lululemon", "Athleta", "Anthropologie", "Urban Outfitters", "Free People", "Madewell", "Everlane",
                "Quince", "Uniqlo", "Patagonia", "The North Face", "Dell", "Lenovo", "Samsung", "Apple", "Hoka",
                "New Balance", "Brooks", "Saucony", "Vans", "Converse", "UGG", "Allbirds", "Vuori", "Alo Yoga",
                "Fabletics", "Gymshark", "Old Navy", "Gap", "Banana Republic", "Spanx", "Comfrt"]

# ---------------------------------------------------------------------------
# Gym sites (gyms.py): each run reads these pages and keeps the Black Friday / holiday / New Year membership offer it
# finds, as a "Gym deals" item. nyc = where in NYC (blank = no confirmed NYC location), courts = where the basketball
# courts are. Facts checked 2026-11-26 on the gyms' own sites (locations, amenities) and in news coverage; check again
# before adding a claim. First reachable url wins (seasonal offer pages 404 out of season).
# planetfitness.com refuses scripts from a home PC (403); kept in case the CI runner gets through.
# ---------------------------------------------------------------------------
GYMS = [
    # basketball courts
    {"name": "Equinox", "urls": ["https://www.equinox.com/"], "nyc": "clubs across Manhattan and Brooklyn",
     "courts": "Sports Club New York (160 Columbus Ave) and East 61st St"},
    {"name": "Life Time", "urls": ["https://www.lifetime.life/nyc.html"], "nyc": "Manhattan and Brooklyn clubs",
     "courts": "Sky (W 42nd St, Hell's Kitchen): regulation court"},
    {"name": "YMCA of Greater New York", "urls": ["https://ymcanyc.org/"], "nyc": "branches in all five boroughs",
     "courts": "branch gyms, e.g. McBurney (W 14th St)"},
    {"name": "JCC Manhattan", "urls": ["https://mmjccm.org/fall", "https://mmjccm.org/membership"],
     "nyc": "Upper West Side (334 Amsterdam Ave)", "courts": "two courts; a basketball-only membership too"},
    {"name": "Manny Cantor Center", "urls": ["https://mannycantor.org/fitness/"],
     "nyc": "Lower East Side (197 East Broadway)", "courts": "regulation court, member open gym Saturdays"},
    {"name": "Asphalt Green", "urls": ["https://www.asphaltgreen.org/bpc"], "nyc": "Battery Park City and Upper East Side",
     "courts": "Battery Park City gym, member open-gym hours"},
    {"name": "Chelsea Piers Field House", "urls": ["https://www.chelseapiers.com/fieldhouse-chelsea"],
     "nyc": "Pier 62, Chelsea", "courts": "two full-size courts: drop-ins, leagues, rentals"},
    {"name": "LA Fitness", "urls": ["https://www.lafitness.com/"], "nyc": "", "courts": "most clubs"},
    {"name": "24 Hour Fitness", "urls": ["https://www.24hourfitness.com/"], "nyc": "",
     "courts": "Sport and Super-Sport clubs (none in New York)"},
    # NYC gyms and studios
    {"name": "PureGym", "urls": ["https://www.puregym.com/us/"], "nyc": "the former Blink Fitness gyms"},
    {"name": "New York Sports Clubs", "urls": ["https://www.newyorksportsclubs.com/"], "nyc": "clubs across NYC"},
    {"name": "Lucille Roberts", "urls": ["https://www.lucilleroberts.com/"], "nyc": "women's gyms across NYC"},
    {"name": "Planet Fitness", "urls": ["https://www.planetfitness.com/"], "nyc": "gyms across NYC"},
    {"name": "Crunch", "urls": ["https://www.crunch.com/"], "nyc": "gyms across NYC"},
    {"name": "Chelsea Piers Fitness", "urls": ["https://www.chelseapiers.com/fitness"],
     "nyc": "Chelsea, Flatiron, Downtown Brooklyn, Prospect Heights"},
    {"name": "Harbor Fitness", "urls": ["https://www.harborfitness.com/"],
     "nyc": "Brooklyn (Park Slope, Bay Ridge, Mill Basin, Midwood, Marine Park)"},
    {"name": "Movement", "urls": ["https://movementgyms.com/"], "nyc": "climbing gyms in Gowanus, Harlem and LIC"},
    {"name": "Bouldering Project", "urls": ["https://boulderingproject.com/"], "nyc": "climbing in Gowanus, Brooklyn"},
    {"name": "[solidcore]", "urls": ["https://www.solidcore.co/black-friday", "https://solidcore.co/"],
     "nyc": "studios across NYC"},
    {"name": "Pure Barre", "urls": ["https://www.purebarre.com/"], "nyc": "NYC studios"},
    {"name": "CorePower Yoga", "urls": ["https://www.corepoweryoga.com/"], "nyc": "NYC studios"},
    {"name": "Club Pilates", "urls": ["https://www.clubpilates.com/"], "nyc": ""},
    {"name": "Tone House", "urls": ["https://tonehouse.com/"], "nyc": "Manhattan studios"},
    {"name": "Barry's", "urls": ["https://www.barrys.com/"], "nyc": "NYC studios"},
    {"name": "SoulCycle", "urls": ["https://www.soul-cycle.com/"], "nyc": "NYC studios"},
    {"name": "Rumble", "urls": ["https://www.rumbleboxinggym.com/"], "nyc": "NYC studios"},
    {"name": "Orangetheory", "urls": ["https://www.orangetheory.com/en-us"], "nyc": "NYC studios"},
    {"name": "ClassPass", "urls": ["https://classpass.com/"], "nyc": "books NYC gyms and studios"},
]
# Brand stores whose every item is "Detroit gear", and team-gear stores whose sitewide promo is a "Team gear sale"
# (their Detroit items are caught by the regex above; shopify.scan_store keeps up to 30 watched items per store)
WATCH_STORES = {"Detroit City FC": "Detroit gear", "Ink Detroit": "Detroit gear"}
WATCH_PROMO_STORES = {"47 Brand", "New Era", "Homage", "Charlie Hustle", "Ebbets Field Flannels", "Sportiqe", "Junk Food"}

# ---------------------------------------------------------------------------
# Scoring knobs
# ---------------------------------------------------------------------------
CLOTHING_MULTIPLIER = 1.6      # clothing deals get their score multiplied by this
CLOTHING_FLAT_BONUS = 12       # ...plus this flat bonus
DEAL_HALF_LIFE_DAYS = 5        # deal score halves every N days of age
MAX_AGE_DAYS = 30              # ignore anything older than this
MIN_NONCLOTHING_SCORE = 8      # non-clothing deals below this are left off the page (they never surface)
# Page slots (scoring.pick_for_page). Brand stores supply 2,000+ verified markdowns that outscore nearly every feed
# deal; unchecked, the 205 stores filled all 2,400 slots and pushed out community deals and almost every non-clothing
# deal (478 -> 91 on 2026-11-25). Each store keeps its best few, feed deals get first claim on FEED_SLOTS, and room
# either side leaves unused goes to the other. The Brands tab has its own per-store list (brand_sales[].top).
MAX_DEALS = 2400
FEED_SLOTS = 1300
MAX_ITEMS_PER_STORE = 8
MAX_ARTICLES = 120             # Sale roundups tab
MAX_ARTICLES_PER_SOURCE = 20   # one site can't fill it (Lifehacker had 38 of 120 on 2026-11-26)
CARD_SCOUT_URL = "https://pjmerica.github.io/card-scout/"   # companion site (cards, cash back), linked in the footer

# ---------------------------------------------------------------------------
# Slickdeals keyword searches (each becomes one RSS query). Heavily clothing.
# ---------------------------------------------------------------------------
SLICKDEALS_CLOTHING_QUERIES = [
    # garments
    "jacket", "coat", "puffer", "parka", "down jacket", "fleece", "vest", "hoodie",
    "sweater", "cashmere", "merino", "flannel", "jeans", "chinos", "joggers",
    "leggings", "dress", "boots", "sneakers", "running shoes", "slippers",
    "base layer", "socks", "underwear", "pajamas", "beanie", "gloves",
    # brands / retailers
    "patagonia", "north face", "arc'teryx", "columbia", "carhartt", "levi's",
    "nike", "adidas", "new balance", "hoka", "uniqlo", "j.crew", "banana republic",
    "gap", "old navy", "lululemon", "vuori", "ralph lauren", "polo ralph lauren",
    "tommy hilfiger", "calvin klein", "under armour", "nordstrom", "macy's",
    "ll bean", "eddie bauer", "rei", "abercrombie", "madewell", "everlane",
    "allbirds", "ugg", "dr martens", "timberland", "bonobos", "todd snyder",
    "quince", "huckberry", "smartwool", "darn tough", "spanx", "aritzia",
    # event terms
    "black friday clothing", "black friday shoes", "cyber monday clothing", "doorbuster",  # "...apparel" found nothing
    # big retailers that block direct scraping: only seen when deal sites post them (added 2026-11-18)
    "american eagle", "aerie", "hollister", "zara", "h&m", "express clothing", "kohl's", "jcpenney", "nordstrom rack",
    "saks off 5th", "bloomingdale's", "dsw", "zappos", "foot locker", "dick's sporting goods", "backcountry",
    "birkenstock", "crocs", "vans", "converse", "salomon", "brooks running", "asics", "on running", "free people",
    "anthropologie", "urban outfitters", "athleta", "fabletics", "alo yoga", "gymshark", "rei outlet",
    "steep and cheap", "sierra trading", "canada goose", "skims", "reformation", "sorel", "ugg boots",
    # added 2026-11-25: more retailers and brands, and winter garments people search for
    "lands' end", "duluth trading", "orvis", "talbots", "ann taylor", "j.jill", "torrid", "lane bryant",
    "kate spade", "coach outlet", "michael kors", "tory burch", "sam edelman", "steve madden", "cole haan", "clarks",
    "sperry", "keen", "merrell", "teva", "hey dude", "skechers", "puma", "reebok", "champion", "hanes",
    "carter's", "oshkosh", "children's place", "gap factory", "j.crew factory", "banana republic factory",
    "brooks brothers", "jos a bank", "vineyard vines", "lacoste", "hugo boss", "wrangler", "dockers",
    "amazon essentials", "goodthreads", "marmot", "helly hansen", "mountain hardwear", "outdoor research", "prana",
    "kuhl", "fjallraven", "rain jacket", "snow boots", "winter boots", "hiking boots", "work boots",
    "chelsea boots", "duck boots", "women's boots", "dress shirt", "blazer", "loafers", "robe", "sherpa",
    "kids clothing", "kids shoes", "baby clothes",
]
SLICKDEALS_GENERAL_QUERIES = [
    "black friday", "cyber monday", "early black friday", "price mistake", "all time low", "lowest price",
    # the rest of the season the site runs through (to 2027-01-17); added 2026-11-27
    "cyber week", "green monday", "holiday sale", "after christmas", "winter clearance", "end of season sale",
    "gift card deal",
    # broad "best deal period" coverage outside clothing
    "tv", "laptop", "airpods", "ipad", "headphones", "nintendo switch", "ps5", "xbox", "ssd", "monitor",
    # Switch 2 and the big Nintendo games (added 2026-11-26: "nintendo switch" alone missed the Switch 2 bundles)
    "switch 2", "nintendo switch 2", "mario kart", "zelda", "pokemon", "joy-con",
    # WATCH items (see top of file). Not "lids" (storage-container lids) or "new era" (nothing relevant).
    "air force 1", "af1", "detroit lions", "detroit tigers", "detroit pistons", "detroit red wings", "fanatics",
    "mitchell & ness",
    # Gym deals (memberships are mostly on the gyms' own sites, gyms.py; these catch posts and home-gym gear)
    "gym membership", "planet fitness", "24 hour fitness", "la fitness", "classpass", "home gym", "dumbbells",
    "treadmill", "power rack", "peloton", "bowflex",
    "apple watch", "kindle", "air fryer", "vacuum", "dyson", "kitchenaid", "lego", "yeti", "power tools",
    "mattress", "coffee maker", "espresso", "luggage", "smart home",
]

SLICKDEALS_SEARCH_URL = (
    "https://slickdeals.net/newsearch.php?q={q}&searcharea=deals&searchin=first&rss=1"
)

# ---------------------------------------------------------------------------
# RSS / Atom feeds.  kind: deal | article
#   deal    = individual product/store deals
#   article = editorial "best sales right now" roundups (kept only if sale-ish)
# ---------------------------------------------------------------------------
FEEDS = [
    # ---- Deal aggregators ----
    {"name": "Slickdeals Frontpage", "kind": "deal", "boost": 10,
     "url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"},
    {"name": "Slickdeals Popular", "kind": "deal", "boost": 8,
     "url": "https://slickdeals.net/newsearch.php?mode=popdeals&searcharea=deals&searchin=first&rss=1"},
    {"name": "Slickdeals Hot Deals", "kind": "deal", "boost": 0,
     "url": "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&forumchoice%5B%5D=9&rss=1"},
    {"name": "DealNews", "kind": "deal", "boost": 0, "url": "https://www.dealnews.com/?rss=1"},
    {"name": "DealNews Clothing", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c202/Clothing-Accessories/?rss=1"},
    {"name": "DealNews Shoes", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c280/Clothing-Accessories/Shoes/?rss=1"},
    # c207 and c208 (the old "Women's" and "Shoes" feeds) return TRAVEL deals; Men's and Women's are filters on
    # c202 (f1 / f2). Checked 2026-11-25: each of these is 80-100% clothing.
    {"name": "DealNews Women's", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c202/Clothing-Accessories/f2/Womens/?rss=1"},
    {"name": "DealNews Men's", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c202/Clothing-Accessories/f1/Mens/?rss=1"},
    {"name": "DealNews Coats", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c489/Clothing-Accessories/Coats/?rss=1"},
    {"name": "DealNews Jeans", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c515/Clothing-Accessories/Jeans/?rss=1"},
    {"name": "DealNews Hoodies", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c866/Clothing-Accessories/Sweatshirts-Hoodies/?rss=1"},
    {"name": "DealNews Activewear", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c487/Clothing-Accessories/Activewear/?rss=1"},
    {"name": "DealNews Kids' Shoes", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c559/Clothing-Accessories/Shoes/Kids-Shoes/?rss=1"},
    {"name": "Hip2Save", "kind": "deal", "boost": 0, "url": "https://hip2save.com/feed/"},
    # Krazy Coupon Lady removed 2026-11-26: every feed address serves the same frozen 1,700-post archive (newest
    # post 8 days old, median 50), so nothing from it reached the page. Re-check thekrazycouponlady.com/rss later.
    {"name": "Ben's Bargains", "kind": "deal", "boost": 0, "url": "https://www.bensbargains.com/rss/"},
    {"name": "9to5Toys", "kind": "deal", "boost": 0, "url": "https://9to5toys.com/feed/"},
    {"name": "DealNews Kids' Clothes", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c205/Clothing-Accessories/Kids-Clothes/?rss=1"},
    # menswear deal blog (sitewide sales, curated picks) and a general deal site (added 2026-11-25)
    {"name": "Dappered", "kind": "deal", "boost": 2, "url": "https://dappered.com/feed/"},
    {"name": "TechBargains", "kind": "deal", "boost": 0, "url": "https://www.techbargains.com/rss.xml"},
    {"name": "DealNews Electronics", "kind": "deal", "boost": 0, "url": "https://www.dealnews.com/c142/Electronics/?rss=1"},
    {"name": "DealNews Computers", "kind": "deal", "boost": 0, "url": "https://www.dealnews.com/c39/Computers/?rss=1"},
    {"name": "DealNews Home", "kind": "deal", "boost": 0, "url": "https://www.dealnews.com/c196/Home-Garden/?rss=1"},
    {"name": "DealCatcher", "kind": "deal", "boost": 0, "url": "https://www.dealcatcher.com/rss"},
    {"name": "camelcamelcamel Top Drops", "kind": "deal", "boost": 0, "url": "https://camelcamelcamel.com/top_drops/feed"},
    # editor-curated deal desks (articles; kept only if sale-related)
    {"name": "CNET Deals", "kind": "article", "boost": 2, "url": "https://www.cnet.com/rss/deals/"},
    {"name": "ZDNet Deals", "kind": "article", "boost": 0, "url": "https://www.zdnet.com/topic/deals/rss.xml"},
    {"name": "The Verge", "kind": "article", "boost": 0, "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Tom's Guide", "kind": "article", "boost": 0, "url": "https://www.tomsguide.com/feeds/all"},
    {"name": "TechRadar", "kind": "article", "boost": 0, "url": "https://www.techradar.com/feeds/all"},
    {"name": "Lifehacker", "kind": "article", "boost": 0, "url": "https://lifehacker.com/feed/rss"},
    {"name": "RetailMeNot Blog", "kind": "article", "boost": 0, "url": "https://www.retailmenot.com/blog/feed"},
    {"name": "Offers.com Blog", "kind": "article", "boost": 0, "url": "https://www.offers.com/blog/feed/"},

    # ---- Fashion editorial (sale roundups) ----
    {"name": "Esquire Style", "kind": "article", "boost": 0, "url": "https://www.esquire.com/rss/style.xml/"},
    {"name": "Esquire", "kind": "article", "boost": 0, "url": "https://www.esquire.com/rss/all.xml/"},
    {"name": "GQ", "kind": "article", "boost": 0, "url": "https://www.gq.com/feed/rss"},
    {"name": "Men's Health", "kind": "article", "boost": 0, "url": "https://www.menshealth.com/rss/all.xml/"},
    {"name": "Glamour", "kind": "article", "boost": 0, "url": "https://www.glamour.com/feed/rss"},
    {"name": "Harper's Bazaar", "kind": "article", "boost": 0, "url": "https://www.harpersbazaar.com/rss/all.xml/"},
    {"name": "Who What Wear", "kind": "article", "boost": 0, "url": "https://www.whowhatwear.com/rss"},
    {"name": "Refinery29", "kind": "article", "boost": 0, "url": "https://www.refinery29.com/en-us/rss.xml"},
    {"name": "PopSugar Fashion", "kind": "article", "boost": 0, "url": "https://www.popsugar.com/fashion/feed"},
    {"name": "Fashionista", "kind": "article", "boost": 0, "url": "https://www.fashionista.com/.rss/full/"},
    {"name": "Hypebeast", "kind": "article", "boost": 0, "url": "https://hypebeast.com/feed"},
    {"name": "Highsnobiety", "kind": "article", "boost": 0, "url": "https://www.highsnobiety.com/feed/"},
    {"name": "Good Housekeeping", "kind": "article", "boost": 0, "url": "https://www.goodhousekeeping.com/rss/all.xml/"},
    # added 2026-11-25 (all checked: they post Black Friday fashion sale roundups)
    {"name": "Gear Patrol", "kind": "article", "boost": 0, "url": "https://www.gearpatrol.com/feed/"},
    {"name": "The Strategist", "kind": "article", "boost": 0, "url": "https://feeds.feedburner.com/nymag/strategist"},
    {"name": "Marie Claire", "kind": "article", "boost": 0, "url": "https://www.marieclaire.com/feeds/all"},
    {"name": "Elle", "kind": "article", "boost": 0, "url": "https://www.elle.com/rss/all.xml/"},
    {"name": "Vogue", "kind": "article", "boost": 0, "url": "https://www.vogue.com/feed/rss"},

]

# Optional: Reddit blocks anonymous scraping. Create a free "script" app at
# https://www.reddit.com/prefs/apps and set REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
# environment variables to enable these.
REDDIT_SUBS = [
    ("frugalmalefashion", "deal", 10),
    ("frugalfemalefashion", "deal", 10),
    ("FrugalFemaleFashion", "deal", 0),
    ("sneakerdeals", "deal", 4),
    ("blackfriday", "deal", 4),
    ("deals", "deal", 0),
]

# ---------------------------------------------------------------------------
# Clothing detection
# ---------------------------------------------------------------------------
CLOTHING_TERMS = {
    "Outerwear": ["jacket", "jackets", "coat", "coats", "parka", "puffer", "anorak", "windbreaker",
                  "vest", "gilet", "shacket", "overcoat", "peacoat", "trench", "outerwear", "down jacket",
                  "rain jacket", "shell jacket", "softshell", "insulated jacket", "parkas", "hoody"],
    "Tops": ["hoodie", "hoodies", "sweatshirt", "sweatshirts", "sweater", "sweaters", "cardigan",
             "pullover", "quarter zip", "1/4 zip", "half zip", "crewneck", "t-shirt", "t-shirts", "tee",
             "tees", "polo", "polos", "henley", "flannel", "button down", "button-down", "oxford shirt",
             "dress shirt", "shirt", "shirts", "blouse", "tank top", "turtleneck", "fleece",
             "jerseys",  # plural only: "jersey" is also New Jersey and jersey-knit sheets (the fallback reads it)
             "longsleeve", "overshirt", "overshirts", "tunic", "tunics", "camisole", "camisoles", "bodysuit",
             "bodysuits"],
    "Bottoms": ["jeans", "pants", "chinos", "trousers", "joggers", "sweatpants", "leggings",
                "shorts", "skirt", "cargo pants", "jogger", "legging", "sweatpant",
                "pant", "chino", "trouser", "skort", "skorts", "overalls", "culottes", "tights", "sweatshorts"],
    "Dresses & Sets": ["dress", "dresses", "jumpsuit", "romper", "suit", "suits", "blazer", "sport coat",
                       "pajama", "pajamas", "pjs", "loungewear", "robe", "matching set",
                       "gown", "gowns", "shirtdress", "kaftan", "caftan", "jumpsuits", "rompers", "onesie", "onesies",
                       "coverall", "coveralls", "nightgown", "nightgowns", "nightshirt", "sleep shirt", "sleepwear"],
    "Footwear": ["boots", "boot", "sneakers", "sneaker", "shoes", "shoe", "loafers", "sandals", "slippers",
                 "clogs", "heels", "flats", "footwear", "running shoe", "trail runner", "chelsea boot",
                 "mules", "slides", "slipper", "clog", "sandal", "loafer", "trainers", "cleats",
                 "booties", "bootie", "espadrilles", "mary janes", "duck boots", "duckboots"],
    "Activewear": ["activewear", "athleisure", "base layer", "baselayer", "thermal", "sports bra",
                   "compression", "running tights", "workout"],
    # "bikini" alone is not here: "bikini trimmer" is a razor. The fallback below tags brand-store bikinis.
    "Swimwear": ["swimsuit", "swimsuits", "swimwear", "tankini", "swim trunks", "swim trunk", "swim shorts",
                 "board shorts", "boardshorts", "boardshort", "board short", "rash guard", "rashguard", "bathing suit", "bikini top",
                 "bikini tops", "bikini bottom", "bikini bottoms", "bikini set"],
    "Basics & Underwear": ["socks", "underwear", "boxer", "boxers", "briefs", "bra", "bras", "undershirt",
                           "long johns", "intimates", "lingerie", "sock", "bralette", "bralettes", "boxer briefs",
                           "undershirts"],
    "Accessories": ["beanie", "scarf", "gloves", "mittens", "hat", "hats", "cap", "belt", "belts",
                    "handbag", "purse", "tote", "sunglasses", "watch strap", "tie", "ties",
                    "beanies", "scarves", "suspenders", "bucket hat"],
}
# Garment type for an item ALREADY classified as clothing whose title names no garment above ("Drape Top",
# "Cheeky Jean", "Apollo Trunk 4\""). These words are too ambiguous to decide whether something is clothing
# ("Top 10 TV deals", "short throw projector", "fish tank"), so they only fill in a missing tag. First match
# wins, in this order: "Bikini Top" is swimwear, "High Top" footwear, "Cheeky Jean" bottoms. Without a tag an
# item vanishes when the page filters by garment type (417 of 1,874 clothing deals on 2026-11-23).
CLOTHING_TAG_FALLBACK = [
    ("Swimwear", r"\bswim|\bbikinis?\b|\bone[- ]piece\b|\bpareos?\b|\bcover[- ]ups?\b"),
    ("Footwear", r"\bslip[- ]?ons?\b|\blace[- ]?ups?\b|\bmules?\b|\b(?:high|low|mid)[- ]tops?\b|\bmary janes?\b|"
                 r"\bslingbacks?\b|\bwedges?\b|\bheels?\b|\bpumps?\b|\b(?:plain|cap|wing)[- ]?toe\b|\bwingtips?\b|"
                 r"\bbrogues?\b|\b(?:oxford|derby) (?:dress )?shoes?\b"),  # not "Oxford" alone: an oxford-cloth shirt
    ("Bottoms", r"\bshorts?\b(?![\s-]*sleeve)|\bjeans?\b|\btights?\b|\b5-pocket\b|\bpalazzo\b|\bbootcut\b|"
                r"\bflares?\b|\bwide[- ]leg\b|\bstraight\b|\bbibs?\b"),  # ski bibs; baby bibs are false positives
    ("Basics & Underwear", r"\bbriefs?\b|\btrunks?\b|\bcheek(?:y|ini)\b|\bthongs?\b(?! sandal)|\bno[- ]show\b"),
    ("Dresses & Sets", r"\bfooties?\b|\bzippy\b|\bsleepers?\b"),
    ("Tops", r"\btops?\b(?![\s-]*(?:\d|rated|picks?|deals?|sellers?|brands?|stores?)\b)|\btanks?\b|\bcamis?\b|\bv-neck\b|\b(?:scoop|mock|crew|boat|cowl) neck\b|\bbutton[- ]up\b|"
             r"\brugby\b|\b(?:long|short)[- ]?sleeves?\b|\bjersey\b|\bjumper\b|\bcamp collar\b|\braglan\b|\bringer\b"),
    ("Outerwear", r"\bfull[- ]zip\b|\bzip[- ]up\b|\bbomber\b|\bshells?\b"),
    ("Accessories", r"\bbags?\b|\bbackpacks?\b|\bcrossbody\b|\bwallets?\b|\bpouch\b|\bcard ?holder\b|\bbows?\b|"
                    r"\bscrunchies?\b|\bheadbands?\b|\bcloche\b|\bvisors?\b|\beye mask\b|\bhair clips?\b|"
                    r"\bnecklaces?\b|\bearrings?\b|\bbracelets?\b|\brings?\b|\bpendants?\b|\bsnapbacks?\b|"
                    r"\btruckers?\b|\bbandanas?\b|\bweekenders?\b|\bbriefcases?\b|\bwatch(?:es)?\b"),
]
# Last resort for brand-store items still untagged: stores that sell essentially one garment type and name
# products by model ("Kizik: Men's London", "Sarah Flint: Perfect Marta 85", "Stance: SHELTER WOMENS CREW").
CLOTHING_TAG_BRAND = {
    "kizik": "Footwear", "sarah flint": "Footwear", "birdies": "Footwear", "koio": "Footwear",
    "thousand fell": "Footwear", "rothy's": "Footwear", "nisolo": "Footwear", "freda salvador": "Footwear",
    "feetures": "Basics & Underwear", "darn tough": "Basics & Underwear", "stance": "Basics & Underwear",
    # added 2026-11-25: shoe brands and denim brands whose jeans are named by fit ("Joe's Jeans: THE LUNA",
    # "FRAME: The Loose", "MOTHER: The Ripper"); their other products name the garment and are tagged before this
    "clae": "Footwear", "velasca": "Footwear", "grant stone": "Footwear", "taos footwear": "Footwear",
    "larroude": "Footwear", "dolce vita": "Footwear", "schutz": "Footwear", "matisse": "Footwear",
    "ace marks": "Footwear", "wolf & shepherd": "Footwear", "native shoes": "Footwear", "xero shoes": "Footwear",
    "olukai": "Footwear", "vessi": "Footwear", "allbirds": "Footwear", "thursday boots": "Footwear",
    "tecovas": "Footwear", "joe's jeans": "Bottoms", "hudson jeans": "Bottoms", "frame": "Bottoms",
    "mother": "Bottoms", "agolde": "Bottoms", "dl1961": "Bottoms", "citizens of humanity": "Bottoms",
    "re/done": "Bottoms", "daze denim": "Bottoms", "pistola": "Bottoms", "naked & famous": "Bottoms",
    "rogue territory": "Bottoms", "true classic": "Tops",
}
# generic words that indicate apparel but aren't a garment category
CLOTHING_GENERIC = ["apparel", "clothing", "clothes", "fashion", "menswear", "womenswear", "wardrobe",
                    "outfit", "outfits", "style deals", "sitewide", "site-wide", "cashmere", "merino", "denim"]

# Brands: case-insensitive whole-word match
CLOTHING_BRANDS = [
    "patagonia", "the north face", "north face", "arc'teryx", "arcteryx", "columbia", "carhartt", "levi's",
    "levis", "nike", "adidas", "new balance", "hoka", "asics", "brooks", "saucony", "on running", "uniqlo",
    "j.crew", "j. crew", "jcrew", "banana republic", "old navy", "lululemon", "vuori", "ralph lauren",
    "polo ralph lauren", "tommy hilfiger", "calvin klein", "under armour", "nordstrom", "nordstrom rack",
    "macy's", "macys", "kohl's", "kohls", "ll bean", "l.l.bean", "l.l. bean", "eddie bauer", "rei",
    "abercrombie", "hollister", "american eagle", "aerie", "madewell", "everlane", "allbirds", "ugg",
    "dr. martens", "dr martens", "timberland", "bonobos", "todd snyder", "quince", "huckberry",
    "smartwool", "darn tough", "spanx", "aritzia", "zara", "h&m", "mango", "free people", "anthropologie",
    "urban outfitters", "lucky brand", "wrangler", "lee jeans", "dockers", "hanes", "champion", "fruit of the loom",
    "jockey", "saxx", "tommy john", "bombas", "mack weldon", "outdoor voices", "fabletics", "athleta",
    "zappos", "foot locker", "dick's sporting goods", "backcountry", "steep and cheap", "sierra trading post",
    "reformation", "loveshackfancy", "christy dawn", "sarah flint", "thousand fell", "outdoor research",
    "alo yoga", "gymshark", "reebok", "puma", "converse", "vans", "skechers", "crocs", "birkenstock",
    "clarks", "cole haan", "sperry", "sorel", "merrell", "keen", "salomon", "the frye", "frye", "steve madden",
    "sam edelman", "kate spade", "michael kors", "coach outlet", "tory burch", "marc jacobs", "lands' end",
    "lands end", "duluth trading", "filson", "barbour", "canada goose", "moncler", "mountain hardwear",
    "marmot", "outdoor research", "prana", "kuhl", "rhone", "faherty", "buck mason", "taylor stitch",
    "outerknown", "reigning champ", "carhartt wip", "stussy", "supreme", "ssense", "mr porter", "end clothing",
    "saks", "saks off 5th", "neiman marcus", "bloomingdale's", "bloomingdales", "dillard's", "jcpenney",
    "target clothing", "goodfellow", "express men", "shein", "asos", "revolve", "shopbop", "net-a-porter",
    "farfetch", "comfrt", "nautica", "guess", "vineyard vines", "southern tide", "peter millar", "brooks brothers",
    "jos. a. bank", "jos a bank", "men's wearhouse", "suitsupply", "indochino", "lacoste", "hugo boss",
    "diesel", "g-star", "true religion", "7 for all mankind", "ag jeans", "frame denim", "citizens of humanity",
    "girlfriend collective", "skims", "uniqlo u", "cos", "& other stories", "arket", "theory", "vince",
    "rag & bone", "club monaco", "j.jill", "loft", "ann taylor", "white house black market", "chico's",
    "torrid", "lane bryant", "eloquii", "universal standard", "hoka one one", "on cloud", "ugg australia",
    # added 2026-11-25 with their Slickdeals searches
    "orvis", "talbots", "teva", "hey dude", "oshkosh", "oshkosh b'gosh", "the children's place", "amazon essentials",
    "goodthreads", "helly hansen", "chaco", "fanatics", "mitchell & ness", "mitchell and ness",
]
# Ambiguous brands: matched case-sensitively, with exclusions
CLOTHING_BRANDS_CASE_SENSITIVE = ["Gap", "GAP", "Coach", "Express", "Lands' End", "Gymshark", "Loft", "LOFT",
                                  "TOMS", "AGOLDE", "STAUD", "FRAME Denim", "MOTHER Denim", "Stance socks"]
CASE_SENSITIVE_EXCLUDE = {"Express": r"American Express|ExpressVPN|Express Scripts|Express Shipping|Prime Express",
                          "Coach": r"Coach (?:seat|class|flight|ticket)",
                          "Loft": r"\bLoft (?:Bed|Ladder|Desk|Bunk)", "LOFT": r"\bLOFT (?:BED|LADDER)"}

GENDER_TERMS = {
    "Men's": [r"\bmen['’]?s\b", r"\bmens\b", r"\bmenswear\b", r"\bfor men\b"],
    "Women's": [r"\bwomen['’]?s\b", r"\bwomens\b", r"\bwomenswear\b", r"\bfor women\b", r"\bladies\b"],
    "Kids": [r"\bkids['’]?\b", r"\bboys['’]?\b", r"\bgirls['’]?\b", r"\btoddler\b", r"\bbaby\b", r"\bchildren['’]?s\b"],
}

# Non-clothing categories (first match wins; clothing is detected separately)
CATEGORY_TERMS = {
    "Tech": ["laptop", "macbook", "chromebook", "tv", "oled", "qled", "4k", "monitor", "ssd", "hard drive", "headphones",
             "earbuds", "airpods", "ipad", "iphone", "tablet", "kindle", "camera", "gopro", "drone", "router", "mesh wifi",
             "speaker", "soundbar", "smartwatch", "apple watch", "galaxy", "pixel", "charger", "power bank", "usb-c",
             "gpu", "graphics card", "cpu", "keyboard", "mouse", "gaming", "ps5", "playstation", "xbox", "nintendo",
             "switch 2", "steam deck", "vr", "meta quest", "projector", "roku", "fire tv", "echo", "ring", "smart home",
             "electronics", "computers", "tablets", "cell phones", "video games", "printer", "nas", "microsd"],
    "Home & Kitchen": ["air fryer", "vacuum", "robot vacuum", "roomba", "dyson", "blender", "kitchenaid", "instant pot",
                       "cookware", "pan", "knife set", "coffee maker", "espresso", "keurig", "nespresso", "mattress",
                       "pillow", "sofa", "sectional", "furniture", "lamp", "rug", "bedding", "sheets", "towels",
                       "christmas tree", "string lights", "decor", "candle", "storage", "humidifier", "air purifier",
                       "space heater", "grill", "home & garden", "kitchen", "appliances", "dishwasher", "refrigerator"],
    "Toys & Games": ["lego", "toy", "toys", "board game", "puzzle", "doll", "nerf", "playset", "hot wheels", "barbie",
                     "squishmallow", "stuffed animal", "kids' toys"],
    "Beauty & Health": ["skincare", "makeup", "fragrance", "perfume", "cologne", "shampoo", "razor", "trimmer",
                        "toothbrush", "vitamin", "supplement", "lotion", "serum", "hair dryer", "beauty", "health",
                        "massager", "massage gun", "massage chair", "disinfecting wipes"],
    "Outdoor & Fitness": ["tent", "sleeping bag", "yeti", "stanley", "cooler", "bike", "e-bike", "treadmill",
                          "dumbbell", "kayak", "camping", "hiking", "fishing", "golf", "peloton", "rower", "sporting goods"],
    "Tools & Auto": ["drill", "impact driver", "tool set", "power tools", "ryobi", "dewalt", "milwaukee", "kobalt",
                     "craftsman", "jump starter", "tire", "dash cam", "car", "automotive", "tools"],
    "Travel & Experiences": ["cruise", "vacation", "flight", "hotel", "tickets", "luggage", "suitcase", "travel",
                             "theme park", "airfare"],
    "Food & Grocery": ["snack", "coffee beans", "soda", "grocery", "chocolate", "meal kit", "protein", "food",
                       "pizza", "restaurant"],
}

# Category tags from feeds that mean apparel
CLOTHING_CATEGORY_HINTS = ["clothing", "apparel", "fashion", "shoes", "footwear", "womens", "mens",
                           "accessories", "jewelry & watches", "style"]

# Things that look like clothing words but usually aren't. A brand-store item matching any of these is not
# clothing at all, so anchor each word: unanchored, "cruise" hid Allbirds' and Filson's Cruiser line, "paint" a
# "Painted Floral" dress, "quilt" quilted vests and hoodies, "flight" a "Flight Hoodie", "tire" every "entire" and
# "attire", "cat " Target's Cat & Jack (2026-11-25).
CLOTHING_FALSE_POSITIVE = [
    r"phone case", r"\bphone (?:stand|holder|grip|mount|charger)", r"laptop", r"tv\b", r"\bssd\b", r"monitor",
    r"air fryer", r"car seat", r"\btires?\b", r"vacuum",
    r"\bpets?\b", r"\bdogs?\b", r"\bcats?\b(?! ?(?:&|and) ?jack| footwear)", r"book jacket", r"life jacket",
    r"watch band", r"smartwatch", r"golf cart",
    r"shoe rack", r"shoe organizer", r"coat rack", r"coat hanger", r"\bpaint(?:s|ing|ings|er|ers|brush(?:es)?)?\b",
    r"primer coat", r"top coat", r"\bcruises?\b", r"vacation", r"packing cubes?",
    r"\bflights?\b(?!\s+(?:jacket|hoodie|bomber|suit|jumpsuit|pant|short|tee|crew|sweatshirt|boot|sneaker|shoe|vest)s?\b)",
    r"hotel", r"candle", r"fragrance", r"parfum", r"cologne", r"perfume",
    r"eau de", r"\bblankets?\b(?! (?:stripe|scarf|coat|hoodie|jacket|shirt|plaid|check))", r"comforter", r"\bduff(?:el|le)s?\b(?! coats?)", r"luggage", r"suitcase", r"water bottle", r"tumbler",
    r"weighted vest", r"skincare", r"lotion", r"makeup", r"bedding", r"towel", r"sheet set", r"\btent\b",
    r"sleeping bag", r"cooler", r"lego", r"\btoys?\b", r"gift card", r"\begc\b", r"giveaway", r"sweepstakes",
    # home goods sold by some apparel brands (Hill House, Cozy Earth, Barefoot Dreams, Jenni Kayne)
    r"\bduvet", r"\bpillow", r"\bquilts?\b", r"\bshams?\b", r"\bsheets?\b", r"\bthrow\b", r"\bdecor", r"\bvase",
    r"\bnapkin", r"\btablecloth", r"\bplacemat", r"\bmug\b", r"\bornament", r"bath mat", r"\bdinnerware",
    # "Quince Ceramic Nonstick Cookware" (2026-11-26: Quince is a clothing brand that also sells kitchenware)
    r"\bcookware\b", r"\bnon-?stick\b", r"\bskillets?\b", r"\bdutch ovens?\b", r"\b(?:frying|sauce) ?pans?\b",
    # garment words in other senses, seen on the live site 2026-11-18 (compression leg massager, thermal printer,
    # "Golf+ ... Tee Off in VR", nylon cable tie, laser tag "no vest needed", a Joe Abercrombie ebook)
    r"massag", r"thermal (?:printer|paper|label|camera|imag)", r"label printer", r"\btee off\b", r"\bgolf tees?\b",
    r"\b(?:cable|zip) ties?\b", r"\bno vest\b", r"laser tag", r"\be-?books?\b", r"\bkindle edition\b", r"\bpaperback\b",
    r"\bhardcover\b", r"\baudiobook\b", r"jump starter", r"\bheater\b",
    # "Puppy Socks Jigsaw Puzzle" (2026-11-25). Not "puzzle" alone: Steve Madden has a shoe called PUZZLE.
    r"\bjigsaw\b", r"\bboard games?\b",
    # baby gear from kids' brands (a feeding bib is not a ski bib)
    r"\b(?:baby|bandana|silicone|feeding|drool|magnetic) bibs?\b", r"\bbibs? \d+-pack", r"\bburp cloths?\b",
    r"\bswaddles?\b", r"\bteethers?\b", r"\brattles?\b", r"\bloveys?\b",
    r"\bcrib (?:sheets?|bumpers?|mattress|mobile|skirt)",  # not "crib shoes" (soft baby shoes)
]
# Department stores / broad retailers: a mention alone is weak evidence of clothing
WEAK_RETAILERS = ["zappos", "dick's", "dick's sporting goods", "backcountry", "sierra", "nordstrom", "nordstrom rack", "macy's", "macys", "kohl's", "kohls", "jcpenney", "dillard's",
                  "saks", "saks off 5th", "neiman marcus", "bloomingdale's", "bloomingdales", "rei",
                  "target clothing", "eddie bauer", "ll bean", "l.l.bean", "l.l. bean", "tommy hilfiger",
                  "calvin klein", "under armour", "columbia", "carhartt", "patagonia", "the north face", "north face",
                  "orvis", "duluth trading",  # both also sell fishing gear, tools and home goods
                  "fanatics"]  # also collectibles, signed balls, drinkware

# ---------------------------------------------------------------------------
# Event / sale terms
# ---------------------------------------------------------------------------
BLACK_FRIDAY_TERMS = [r"black friday", r"cyber monday", r"cyber week", r"doorbuster", r"door buster",
                      r"\bbfcm\b", r"thanksgiving sale", r"holiday sale", r"early access", r"pre-black friday",
                      r"gray friday", r"grey friday", r"small business saturday"]
SALE_TERMS = [r"\bsale\b", r"\bsales\b", r"\bdeals?\b", r"% off", r"\bdiscount", r"\bmarkdown",
              r"on sale", r"black friday", r"cyber monday", r"promo code", r"coupon", r"clearance",
              r"price drop", r"lowest price", r"\bsave\b", r"\bbogo\b", r"secret sale", r"friends & family"]

