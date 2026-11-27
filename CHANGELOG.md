# Changelog

Every change to Deal Scout, newest first. **Rule for every future change (people and agents):** add an entry here
in the same commit: the date, what changed on the site or in the logic, and why (the bug seen, or the owner's
request). Commit hashes are filled in once a change is committed. Owner decisions live in HANDOFF.md §1, and this
file links to them where one applies.

Live site: https://pjmerica.github.io/deal-scout/ · Repo: pjmerica/deal-scout

---

## 2026-11-27

### 6 more stores from a Black Friday re-probe
The 22 stores that were open on Nov 25 with nothing on sale were probed again on Black Friday, this time also
counting their sale collections. Added, with markdowns in their sale collection: YoungLA (57), M.Gemi (57), Greyson
(158), 3sixteen (39), Bodega (114). Alex Mill was added with 67 markdowns on its first product page. That makes 229
stores. Still nothing on sale: Pure Detroit, Original Retro Brand, Starter, Clare V. and others. They're listed in
`tools/store_candidates.txt` for a late-December re-probe.

### `2cb04eb` Store probe counts the sale collection too (tooling)
`tools/probe_stores.py` counted markdowns only on page 1 of a store's whole product list, which is mostly new
arrivals. Stores with a full "bfcm" collection showed 0 on sale. It now also reports markdowns in the sale collection
the scanner would pick (`in_sale_collection`).

### `b8a01ef` Sneaker models count as footwear
13 of 53 items from the new sneaker shops had no garment type, so the Footwear chip missed them: DTLR names the model
("Nike Air Force 1 Low LV8 Edge", "Javi Elevate Toddler", "Steve Madden Pryce Grade-School"). The footwear fallback
now knows sneaker models (Air Force 1, Air Max, Dunk, Jordan N, Kobe, Samba, Gazelle, 1906R, 990vN, clogs, slides) and
kids' shoe sizes (Grade-School, Pre-School, "... Toddler"). It applies only to clothing items with no garment word, so
"Jordan Retro 4 Tee" is still a top.

### `710fc1c` Ready for Cyber Monday, the holidays and January
The site runs until 2027-01-17, and several things assumed November:
- **Header label.** In January it would have said "Black Friday in 310 days" (it counted to next November), and on
  Cyber Monday itself it already said "Holiday sales season". The labels now run:
  - Black Friday in N days / tomorrow;
  - Black Friday weekend is on;
  - Cyber Monday is on;
  - Holiday sales season;
  - After-Christmas sales (from Dec 26);
  - New Year and winter clearance sales (January).
- **Brand-store collections.** Black Friday, Cyber and holiday collections count as current in November and
  December only. In January, a store's leftover "black-friday" collection loses to its "winter-sale",
  "boxing-day-sale" or "new-year-sale" (`shopify.SEASON_HANDLES`).
- **Slickdeals searches** added for the rest of the season: cyber week, green monday, holiday sale, after christmas,
  winter clearance, end of season sale.

### `706365d` Gym offers: Equinox's new offer, tidier headings
- Equinox changed its offer overnight to "Black Friday: Rest of the year on us ... Offer ends Black Friday", and the
  scanner dropped it: "on us", "rest of the year" and "free until" weren't counted as terms. They are now. The card
  shows it ending tonight (11:59 pm ET).
- Headings that ran into the offer get a colon:
  - "Black Friday Early Access Unlock $0 ..." → "Black Friday Early Access: Unlock $0 ...";
  - "Black Friday Special Buy 10 Classes" → "Black Friday Special: Buy 10 Classes";
  - "BLACK FRIDAY SALE For a limited time" → "Black Friday sale: For a limited time".

### `cad8d85` Prices: shipping minimums and "$X off" are not prices; "Levi's's" wording
- **The price reader took the first dollar amount in a headline.** For 72 live deals that was a shipping minimum, a
  discount or a coupon threshold, which also inflated their % off and let them through the "Under $50" filter:
  - "Levi's Black Friday Deals at Macy's: 40% to 75% off + free shipping w/ $39" showed a $39 price;
  - "Over $50 Off Meta Adventurer AI Glasses" showed $50 and 80% off;
  - "$20 off $100 coupon" showed $20;
  - "Keurig ... + $15 Kohl's Cash $64.79" showed $15.
- Now `scoring.headline_price` skips amounts after "w/", "on", "orders", "spend", "after", "$X off", "up to" or
  "save", and amounts followed by "off", "+ gift card", "Kohl's Cash", "back" or "bonus".
- "$X+" alone still counts as a starting price ("Slippers $3.12+"). "45% Off $29.99" is still $29.99.
- Store-wide sales now carry no price, so they show only under "Any price".
- **"54 pts deeper than Levi's's usual sale"** now reads "Levi's usual sale". Names ending in s get an apostrophe
  only: "Allbirds' usual sale".

### `056974c` 9 sneaker shops read directly, for Air Force 1 coverage
Result on the first run: Air Force 1 deals on the Watching tab went from 6 to 23, and all 9 shops were read (1,821
items on sale between them).
- Only 6 Air Force 1 deals were on the Watching tab: Nike, Foot Locker and Finish Line aren't readable.
- Sneaker shops that carry AF1s and run on Shopify were probed from CI (12 of 15 open). Added, with items on sale at
  the probe: DTLR (11), Social Status (28), Sneaker Politics (35), Concepts (46), Undefeated (44), Lapstone & Hammer
  (32), A Ma Maniere (7), Shoe Palace (4), Shop Nice Kicks (5). That makes 223 stores.
- Each keeps up to 30 watched items (AF1s, Detroit gear) on top of its best 8.
- Left out: Extra Butter, Feature and BDGA (0-3 items on sale). Closed: Jimmy Jazz, atmos USA, Kicks USA. Details are
  in `tools/store_candidates.txt`.
- "Concepts", "Undefeated" and "Social Status" are ordinary words, so they aren't matched in deal-site headlines.

### `ebe4238` Fake-sale check: a pack-size switch is not a price change
- Swiftwick's Pursuit Crew showed "Original price raised $22 → $110". The store lists one pair and multi-packs as
  variants of one product, and the scan picked a different one between runs.
- An "original" price that more than doubles or halves now counts as a different variant, not inflation. Real
  inflate-then-discount cases run 10-50%, such as Comfrt $108 → $150 and Robert Graham $498 → $598, and are still
  flagged.
- At brand stores, a price more than 2.5× apart also no longer counts as "was cheaper", "price dropped" or "lowest
  recorded". Deal-site headlines keep the drop note, since a price mistake can be 70% off.

### `76cf413` Brands tab: top picks show the fake-sale warning
- Janji's "M's Rover Merino Half-Zip" was $64 on Nov 19 and $76.80 on Nov 26. It was a top pick on Janji's brand card
  with no note, because the picks are built before the price history runs and the warning reached only the deal
  lists. Picks now show "⚠ Was $64 on Nov 19, cheaper than now" (or "Original price raised ...") and sort after the
  clean ones (`history.flag_brand_picks`).
- Every pick now goes through the history check: Kids and "Everyone" picks could fall outside the items checked.
- Context: on 2026-11-27, 12 live brand-store items were priced more than 3% above their tracked low.

### `cf72c56` Refresh every 3 hours for real; "[Resale]" posts get the used-item warning
- **The 3-hour refresh wasn't happening.** GitHub drops most scheduled starts: from Nov 19 to 27, runs came 6 to 14
  hours apart, including 13 hours over Thanksgiving. Changes:
  - The schedule is now tried every hour.
  - The `guard` job skips the run while the live data is under 170 minutes old and was built from the current
    commit. `deals.json` now records the commit it was built from (`"commit"`, its second key, so the guard reads
    only the first 400 bytes).
  - Scrapes still happen at most every ~3 hours, which is the owner's chosen cadence. Hourly scrapes were declined
    (HANDOFF §1), and this doesn't add them.
  - Runs now queue instead of cancelling each other, so an hourly check can't cancel a build in progress.
- Slickdeals "[Resale]" posts get the "Refurbished / used" warning even when they don't say "used".

### `703e5f7` Fixes from an audit of the live data
Owner: "keep trying to fix and improve everything as much as possible and document all prior and future changes".
The audit checked the 2,520 live items for expired deals (none), duplicates (none), dead sources (Hypebeast and
Reddit, both known), price oddities, clothing misreads, store names and the Watching lists.

- **Resale items are no longer counted as markdowns.** Outerknown's used "Iconoclast High Rise Skinny" (product link
  ending `-resale`) showed as 88% off, priced against the new price. Brand-store products whose link, title, type or
  tags say resale, pre-owned, used, Worn Wear or refurbished are skipped (`shopify.RESALE`).
- **Store names for deals that had none.** 141 deals had no store, mostly Hip2Save, TechBargains and 9to5Toys
  headlines that open with the store ("Kohl's Black Friday Doorbusters", "American Eagle Black Friday Sale").
  - A known store or brand at the start of a sale headline is now the store (`scoring.LEAD_STORE_RE`, lists in
    `config.EXTRA_STORES` / `EXTRA_BRANDS`).
  - Retailers count before a dash too ("Amazon - Nike Men's ..."). Brands count only before sale words: "Apple -
    AirPods" is usually sold somewhere else.
  - "Deals at Macy's: Up to 70% off" now reads the store after "at" when a colon follows (29 live headlines).
  - TechBargains' `<vendorname>` field is read as the store. Feeds that link straight to a retailer
    ("https://www.amazon.com/...") take the store from the link (`feeds.store_from_link`).
  - Curly apostrophes ("Kohl’s"), "Woot! Daily Deals", "Bonobos 30% – 40% off" and "J. Crew" are also handled.
  - Result: storeless deals in a test build fell from 212 to 109. Store names feed the Best list's
    one-per-store rule and the Rakuten / card-offer badges.
- **Switch 2 filters:** accessory kits ("21-in-1 Accessories Bundle Kit") moved from Consoles & bundles to
  Accessories, and the bare console ("Nintendo Switch 2 - Black") from Games to Consoles.
- **Sale roundups tab: at most 20 articles from one site.** Lifehacker had 38 of the 120 slots, mostly tech, on a
  clothing-first site (`config.MAX_ARTICLES_PER_SOURCE`).
- **Cookware isn't clothing.** "Quince Ceramic Nonstick Cookware" was in Clothing (Quince is a clothing brand).
  Cookware, nonstick, skillets, dutch ovens and pans are now excluded.
- **Watches get the Accessories type** instead of no garment type.
- **Peloton bottles, straps and apparel are not home-gym gear** (Gym deals → Home gym gear); treadmills and bikes are.
- **"Buy 10 classes, get 10 free" counts as 50% off** and "buy 2, get 1 free" as 33%. Pure Barre's offer had no
  discount badge.
- **This changelog**, with every change since the first commit, and a rule in HANDOFF.md to keep it current.

---

## 2026-11-26

### `3f9d0ad` Gym deals: offers from 28 gyms' own sites, NYC and basketball-court filters
Owner: "look for gym deals, especially ones in NYC", then "find ones with basketball facilities too" (HANDOFF §1).
- `gyms.py` reads 28 gyms' own pages each run (`config.GYMS`) and keeps the membership offer line each one
  advertises. A line needs an occasion (Black Friday, holiday, New Year, "sale ends") and terms ($0 down, % off,
  free month, buy N get N). Deal sites barely post memberships, and news searches found gyms in other states.
- Each gym entry records where its NYC locations and basketball courts are, checked on the gyms' own sites. The card
  shows this on a 📍 line.
  - Courts: Equinox Sports Club NY and East 61st, Life Time Sky, the Y, JCC Manhattan, Manny Cantor Center, Asphalt
    Green BPC, Chelsea Piers Field House, LA Fitness, 24 Hour Fitness.
- Watching tab: "Gym deals", with overlapping filters NYC / Basketball courts / Memberships & classes / Home gym gear.
  It also takes membership and home-gym posts from the deal sites, plus 11 new Slickdeals searches.
- Membership terms ("$0 join fee", "save $180") are not shown as prices, and don't get the "Membership required"
  warning. Gym offers count the gym as the brand (no "Lesser-known brand"), with category Outdoor & Fitness.
- "Ends 11.30" (dotted dates after an end word) is read as an end date. "Join ... by November 30" ends a gym offer.
- Watched deals past the 400 cap now compete for ordinary page slots. Before, the overflow vanished.

### `016f621` Watching badge: same size as the other badges

### `2e77321` Watching filters: counts, sub-filters per item, max price, badge jump
Owner: "can you add filters for these items?"
- Item chips with counts. Picking one adds its own filters (`config.WATCH_SUB`):
  - Detroit gear by team;
  - Switch 2 by consoles & bundles / accessories / games;
  - team-gear sales by league.
- Max-price menu (under $25 / $50 / $100 / $200) on every list.
- A 👀 badge on any card opens the Watching tab filtered to that item.

### `a90238c` Team gear sales: store-wide sales only
Detroit City FC's "47 Brand Oversized DETROIT Crew" was listed as a team-gear sale. For brand-store items the label
now comes only from the team-gear stores' sitewide promos.

### `3ff814e` Watching: Detroit gear and team-gear sales; 9 team-gear and Detroit stores
Owner: "look for any Detroit sports gear deals".
- Deal sites post almost no team-specific gear, so the team-gear stores and Detroit stores are now read directly:
  - team gear: '47, New Era, Ebbets, Charlie Hustle, Sportiqe, Homage, Junk Food;
  - Detroit: Detroit City FC, Ink Detroit.
- "Detroit gear" matches the team name, or team plus league. Not "Detroit" alone (Detroit Axle) or "Tigers" alone
  (LSU).

### `e7e55b7` End dates and timing on cards; Watching tab (Air Force 1, Switch 2); drop frozen feed
Owner: "is there a timeframe on how long the deals are?", "Air Force 1s and Nintendo Switch 2 are big for deals for
me".
- `ends.py` reads end dates from the deal's own words ("Ends 12/1", "through November 30", "today only", "ends Cyber
  Monday"), or DealNews's expiry field minus its "posted + 90 days" filler. This adds a ⏰ badge and an "Ending
  soonest" sort. Deals already over are dropped: 9 were still showing.
- Every card says how long it's been up ("On sale since Nov 20 · 6 days" / "Posted Nov 24 · 2d ago").
- Watching list (`config.WATCH`): Air Force 1s and Switch 2, with a badge and their own tab, always kept on the page.
- Krazy Coupon Lady removed: its feed is a frozen archive.

## 2026-11-25

### `1c7182c` Garment types for model names at shoe and denim brands; hats, bags; titles without markup
Shoe brands → Footwear, denim brands → Bottoms when the product name is a model ("Clae: MORRISON"). Snapbacks,
truckers and bandanas are Accessories. Duffle bags aren't clothing, but duffle coats are. HTML is stripped from
Shopify titles.

### `b83a010` Garment types: ignore the store's name in brand-store titles; bibs, blankets, jewelry
"Kickee Pants: Knot Headband" was tagged Bottoms because of the store name. Garment words now read only the product
part. Dress socks aren't dresses. Ski bibs are bottoms, but baby bibs and swaddles aren't clothing.

### `eecba0a` Page slots: brand stores no longer crowd out feed and non-clothing deals
With 205 stores, brand-store markdowns took all 2,400 slots: non-clothing deals fell from 478 to 91. Now:
- each store keeps its best 8;
- feed deals get first claim on 1,300 slots;
- unused room goes to the other side.

### `ad16573` Expand sources: 69 brand stores, DealNews clothing feeds fixed, ~65 searches, new feeds
- DealNews "Women's" and "Shoes" feeds were returning travel deals. They were replaced, and men's, coats, jeans,
  hoodies, activewear and kids' shoes feeds were added.
- 69 Shopify stores added (205 total).
- New feeds: Dappered, TechBargains, Gear Patrol, The Strategist, Marie Claire, Elle, Vogue.

### `e8fdc23` Brand stores: Black Friday collections win over off-season ones
Oliver Cabell's scan picked "july-sale" in November. Black Friday words now count anywhere in a collection name, and
collections named for another season lose 70 points.

### `95116bf` Anchor clothing false-positive words, garment-type fallback, kids' brands to Kids
- False-positive words now match whole words only. "cruise" had hidden Cruiser shoes, "tire" every "entire", and
  "cat" Cat & Jack.
- Garment type for the 417 clothing items whose title named none. New Swimwear chip.
- Kids' brands' dresses are Kids, not Women's.

## 2026-11-18

### `6281671` Store names for Slickdeals deals, clothing false positives, promo-menu and gender fixes
- Slickdeals store from the outbound link and description: deals with no store fell from 48% to 13%.
- Brand names that are ordinary words (Diesel, Mango, Express) need a garment word. Lysol wipes and a Keurig had
  been in Clothing.
- Filter menus ("20% Off Sale ... 70% Off Sale") are no longer read as promos.

### `f27649d` HANDOFF: note phrase-quoted Slickdeals searches

### `1cb512f` Quote multi-word Slickdeals searches
"free people" returned body wash and cameras. Multi-word searches are now phrase matches.

### `3fedb53` 55 more brand stores, ~40 retailer searches, end-date guard
- Stores verified from CI (136 total).
- Store names that are ordinary words (Cuts, FRAME, MOTHER) aren't matched in headlines.
- Searches for retailers that block scraping.
- Scheduled runs stop after 2027-01-17 (owner's planned end).

### `f58f5b7` tools: probe candidate Shopify stores from CI (probe.yml)

### `e4ce82c` HANDOFF.md for agents + tools/shots.js real-browser check

### `a7c1586` Banner codes: only take a nearby code when it can't belong to a different promo
Steve Madden's code EARLY was shown on the wrong promo.

### `60d8444` Health check: manual test-alert switch

### `d6ab479` Fake-sale detector, promo codes, Card Scout stack hints, health alerts, lighter page
- `history.py` flags an inflated "original" price or a recent lower price.
- `codes.py` adds copy buttons for promo codes.
- `stacks.py` shows Rakuten and card offers from Card Scout.
- `tools/health.py` keeps the self-closing "Site health" issue.
- Page weight roughly halved.

### `7aa7249` Cleanup: structured gender tags, tighter promo text

### `fcf5b14` Fixes from a real-browser look at the live site
Brand thumbnails were ~4 MB and showed blank. Colour and size variants are collapsed. Compact header on phones.

### `a89a70c` Split: Deal Scout is Black Friday deals only; cards moved to card-scout
Also: tab clicks threw an error on a removed state field, and the smoke test now clicks every control.

### `69a7dfe` Men's / Women's / Kids filter across deal tabs and brand sales

### `61005a1` NEW badge = appeared since the previous run

### `24b7239` Best list: one pick per store/brand; soften no-name deals

### `7eeed95` Deeper deal logic: brand-store scanning, explainable quality score, run history
81 Shopify stores, the Deal Quality Score with reasons and warnings, run-to-run memory, more feeds, and CI tests
before deploy.

### `a77b2ad` Deal Scout: Black Friday + credit card deal scraper with GitHub Pages deploy
