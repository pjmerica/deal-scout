"""
Deal Scout configuration: sources, keyword lists, and scoring knobs.
Edit this file to add/remove feeds, brands, or tune the clothing bias.
"""

# ---------------------------------------------------------------------------
# Scoring knobs
# ---------------------------------------------------------------------------
CLOTHING_MULTIPLIER = 1.6      # clothing deals get their score multiplied by this
CLOTHING_FLAT_BONUS = 12       # ...plus this flat bonus
DEAL_HALF_LIFE_DAYS = 5        # deal score halves every N days of age
MAX_AGE_DAYS = 30              # ignore anything older than this
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
    "black friday clothing", "black friday apparel", "doorbuster",
]
SLICKDEALS_GENERAL_QUERIES = [
    "black friday", "cyber monday", "early black friday", "price mistake", "all time low", "lowest price",
    "gift card deal",
    # broad "best deal period" coverage outside clothing
    "tv", "laptop", "airpods", "ipad", "headphones", "nintendo switch", "ps5", "xbox", "ssd", "monitor",
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
     "url": "https://www.dealnews.com/c208/Clothing-Accessories/Shoes/?rss=1"},
    {"name": "DealNews Women's", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c207/Clothing-Accessories/Womens-Clothing/?rss=1"},
    {"name": "Hip2Save", "kind": "deal", "boost": 0, "url": "https://hip2save.com/feed/"},
    {"name": "Krazy Coupon Lady", "kind": "deal", "boost": 0, "url": "https://www.thekrazycouponlady.com/rss"},
    {"name": "Ben's Bargains", "kind": "deal", "boost": 0, "url": "https://www.bensbargains.com/rss/"},
    {"name": "9to5Toys", "kind": "deal", "boost": 0, "url": "https://9to5toys.com/feed/"},
    {"name": "DealNews Kids' Clothes", "kind": "deal", "boost": 0,
     "url": "https://www.dealnews.com/c205/Clothing-Accessories/Mens-Clothing/?rss=1"},
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
             "dress shirt", "shirt", "shirts", "blouse", "tank top", "turtleneck", "fleece"],
    "Bottoms": ["jeans", "pants", "chinos", "trousers", "joggers", "sweatpants", "leggings",
                "shorts", "skirt", "cargo pants", "jogger", "legging", "sweatpant"],
    "Dresses & Sets": ["dress", "dresses", "jumpsuit", "romper", "suit", "suits", "blazer", "sport coat",
                       "pajama", "pajamas", "pjs", "loungewear", "robe", "matching set"],
    "Footwear": ["boots", "boot", "sneakers", "sneaker", "shoes", "shoe", "loafers", "sandals", "slippers",
                 "clogs", "heels", "flats", "footwear", "running shoe", "trail runner", "chelsea boot",
                 "mules", "slides", "slipper", "clog", "sandal", "loafer", "trainers", "cleats"],
    "Activewear": ["activewear", "athleisure", "base layer", "baselayer", "thermal", "sports bra",
                   "compression", "running tights", "workout"],
    "Basics & Underwear": ["socks", "underwear", "boxer", "boxers", "briefs", "bra", "bras", "undershirt",
                           "long johns", "intimates", "lingerie"],
    "Accessories": ["beanie", "scarf", "gloves", "mittens", "hat", "hats", "cap", "belt", "belts",
                    "handbag", "purse", "tote", "sunglasses", "watch strap", "tie", "ties"],
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
]
# Ambiguous brands: matched case-sensitively, with exclusions
CLOTHING_BRANDS_CASE_SENSITIVE = ["Gap", "GAP", "Coach", "Express", "Lands' End", "Gymshark", "Loft", "LOFT"]
CASE_SENSITIVE_EXCLUDE = {"Express": r"American Express|ExpressVPN|Express Scripts|Express Shipping|Prime Express",
                          "Coach": r"Coach (?:seat|class|flight|ticket)"}

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
                        "toothbrush", "vitamin", "supplement", "lotion", "serum", "hair dryer", "beauty", "health"],
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

# Things that look like clothing words but usually aren't
CLOTHING_FALSE_POSITIVE = [
    r"phone case", r"laptop", r"tv\b", r"\bssd\b", r"monitor", r"air fryer", r"car seat", r"tire", r"vacuum",
    r"pet ", r"dog ", r"cat ", r"book jacket", r"life jacket", r"watch band", r"smartwatch", r"golf cart",
    r"shoe rack", r"shoe organizer", r"coat rack", r"coat hanger", r"paint", r"primer coat", r"top coat",
    r"cruise", r"vacation", r"flight", r"hotel", r"candle", r"fragrance", r"parfum", r"cologne", r"perfume",
    r"eau de", r"blanket", r"comforter", r"duffel", r"luggage", r"suitcase", r"water bottle", r"tumbler",
    r"weighted vest", r"skincare", r"lotion", r"makeup", r"bedding", r"towel", r"sheet set", r"\btent\b",
    r"sleeping bag", r"cooler", r"lego", r"\btoys?\b", r"gift card", r"\begc\b", r"giveaway", r"sweepstakes",
]
# Department stores / broad retailers: a mention alone is weak evidence of clothing
WEAK_RETAILERS = ["nordstrom", "nordstrom rack", "macy's", "macys", "kohl's", "kohls", "jcpenney", "dillard's",
                  "saks", "saks off 5th", "neiman marcus", "bloomingdale's", "bloomingdales", "rei",
                  "target clothing", "eddie bauer", "ll bean", "l.l.bean", "l.l. bean", "tommy hilfiger",
                  "calvin klein", "under armour", "columbia", "carhartt", "patagonia", "the north face", "north face"]

# ---------------------------------------------------------------------------
# Event / sale terms
# ---------------------------------------------------------------------------
BLACK_FRIDAY_TERMS = [r"black friday", r"cyber monday", r"cyber week", r"doorbuster", r"door buster",
                      r"\bbfcm\b", r"thanksgiving sale", r"holiday sale", r"early access", r"pre-black friday",
                      r"gray friday", r"grey friday", r"small business saturday"]
SALE_TERMS = [r"\bsale\b", r"\bsales\b", r"\bdeals?\b", r"% off", r"\bdiscount", r"\bmarkdown",
              r"on sale", r"black friday", r"cyber monday", r"promo code", r"coupon", r"clearance",
              r"price drop", r"lowest price", r"\bsave\b", r"\bbogo\b", r"secret sale", r"friends & family"]

