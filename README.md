# Deal Scout

Finds the **best Black Friday deals**, with a **clothing bias**. Each deal gets a quality score that lists its reasons.
GitHub Actions re-scrapes every 3 hours and redeploys the site to GitHub Pages:
**https://pjmerica.github.io/deal-scout/**

**Agents and maintainers: start with [HANDOFF.md](HANDOFF.md)** (owner decisions, how things break, how to verify).
**[CHANGELOG.md](CHANGELOG.md)** lists every change since the first commit; add an entry with each change.

> **Credit cards, cash back and card news moved out on 2026-11-18** to the companion project **Card Scout**
> (`Documents\card-scout`, https://github.com/pjmerica/card-scout, https://pjmerica.github.io/card-scout/). Its
> `HANDOFF.md` documents the split. Deal Scout's footer and header link to it.

## What's on the site

| Tab | What it shows |
|---|---|
| 🏆 Best | Diversified top 60 (one per store and per brand, colour variants collapsed), then the best picks in each category |
| 👕 Clothing | Every clothing and footwear deal, with category chips (Outerwear, Tops, Footwear, …) |
| 👀 Watching | Every deal for the things you watch (`config.WATCH`: Air Force 1s, Nintendo Switch 2, Detroit teams' gear, team-gear store sales, gym deals, home gym gear), wherever it ranks. Filter by item, then by team, console/game/accessory, league, gyms in NYC / with basketball courts (they overlap) / other, or weights / cardio gear; click any 👀 badge to jump here. Each item has its own link: `#watch/air-force-1`, `#watch/nintendo-switch-2`, and so on. Gym offers show 📍 where the NYC locations and basketball courts are |
| 🏷 Brand sales | 229 brands' and shops' own stores: live sitewide promo, number of items on sale, typical and max discount, top picks |
| 🖤 Black Friday | Deals that mention Black Friday, Cyber Monday or doorbusters |
| 🔥 All deals | Everything, with category chips (Tech, Home & Kitchen, Toys, …) |
| 📰 Sale roundups | Editors' sale roundups (fashion and tech) |
| ⚙️ How it works | The scoring method, plus every source with live status |

The **Shopping for: Everyone / Men / Women / Kids** switch (remembered between visits) filters the clothing on every
deal tab and Brand sales. Unisex items and storewide sales count as "Everyone" and show in both Men's and Women's views.
Non-clothing deals are never hidden by it.

## What it reads

| Layer | Sources |
|---|---|
| Deal aggregators | Slickdeals (frontpage, popular, hot deals, plus about 230 keyword searches: clothing items, ~90 apparel brands and big retailers that block scraping, "price mistake", "all time low", gift card deals, top tech and home categories, and the Watching list: Switch 2, Air Force 1, Detroit teams, gym memberships and home-gym gear), DealNews (main, clothing, men's, women's, shoes, coats, jeans, hoodies, activewear, kids' clothes and shoes, electronics, computers, home), Dappered, Hip2Save, Ben's Bargains, 9to5Toys, TechBargains, DealCatcher, camelcamelcamel top price drops |
| Brand stores (direct) | **229 Shopify storefronts** (clothing brands, team-gear stores and sneaker shops: DTLR, Concepts, Undefeated, Social Status, Sneaker Politics…): menswear (Todd Snyder, Taylor Stitch, Faherty, Kith, Aimé Leon Dore…), women's (Sarah Flint, LoveShackFancy, Christy Dawn, STAUD, AGOLDE, MOTHER, Faithfull, Montce…), shoes (Allbirds, Thursday Boots, Rothy's, Thousand Fell, TOMS…), kids (Primary, Tea Collection, Little Sleepies) and outdoor (Cotopaxi, Outdoor Research, Stio, Ibex…). Real sale price vs original price, in-stock sizes, product tags (used for gender), and the live sitewide promo from the homepage banner |
| Gym sites (direct) | **28 gyms' own pages** (`config.GYMS`, `gyms.py`): NYC gyms and studios (Equinox, PureGym/ex-Blink, New York Sports Clubs, Lucille Roberts, Planet Fitness, Crunch, Chelsea Piers, Harbor Fitness, Movement and Bouldering Project climbing, [solidcore], Pure Barre, CorePower, Barry's, SoulCycle, Rumble, Orangetheory, Tone House, ClassPass), gyms with basketball courts (Equinox Sports Club, Life Time Sky, the Y, JCC Manhattan, Manny Cantor Center, Asphalt Green, Chelsea Piers Field House, LA Fitness, 24 Hour Fitness) and Club Pilates. Keeps the Black Friday / holiday / New Year membership offer line a gym advertises, if any |
| Editors | GQ, Esquire, Men's Health, Gear Patrol, The Strategist, Glamour, Marie Claire, Elle, Vogue, Harper's Bazaar, Who What Wear, Refinery29, PopSugar, Fashionista, Hypebeast, Highsnobiety, Good Housekeeping, CNET, ZDNet, The Verge, Tom's Guide, TechRadar, Lifehacker, RetailMeNot, Offers.com |
| Optional | Reddit (r/frugalmalefashion, r/frugalfemalefashion, r/sneakerdeals, …). Needs free API keys, see below |

## The Deal Quality Score

Every component adds a readable reason (shown under each deal) or a warning (shown in amber):

1. **Effective discount**: stacked codes compound (50% + an extra 30% ≈ 65%). "Up to" offers are discounted. A final
   "$X, down from $Y" price is used as-is and never stacked again.
2. **Discount vs. the brand's usual sale** (`brands.py` `BASELINE`): Old Navy at 50% off is a normal week, while Patagonia
   at 40% is rare. The amount a deal beats that level scores extra.
3. **Price-history evidence**: "best price we could find by $X", "all-time low", "price mistake", camelcamelcamel drops,
   and Deal Scout's own history (price drops, lowest price recorded).
4. **Community**: Slickdeals votes (log scale), vote velocity, and Frontpage / Popular placement.
5. **Editors**: DealNews staff picks, and the same deal found by several sources.
6. **Quality and stock**: premium brands that rarely discount, prices verified on the retailer's own site, and sizes
   left in stock. Unknown brands score lower (−18 and ×0.88).
7. **Catches**: in-store only or YMMV, membership required, refurbished, rebates, sponsored posts, sold out or expired.
8. **Freshness**: scores halve every 5 days. There's a small bump for "ends soon", and expired deals are removed.
9. **Clothing bias**: × `CLOTHING_MULTIPLIER` (1.6) plus a flat bonus.

Tiers are percentiles (Exceptional is the top 3%, Great 12%, Good 35%).

**Gender** (`gender.py`), in order of evidence: title words (including curly apostrophes and "unisex"), a kids' brand
(Kids unless the item is marked adult), garment hints
(dress, skirt set, bra → Women's; boxer briefs, tuxedo → Men's), retailer product tags, a single-audience brand
(`brands.BRAND_AUDIENCE`), the description, a brand that sells to everyone, then storewide sales → Everyone. A store's
audience counts only for storewide sales: a sweater at Macy's isn't unisex.

**Stores**: DealNews names the retailer; Slickdeals items use the store slug on the deal's outbound link and the
"Macy's has…" opening of the description; other feeds use "at Amazon" / "on Macys.com" in the title.

## Fake-sale detector, promo codes, stack hints

- **Fake-sale detector** (`history.py`): every brand-store item's price and original (compare-at) price are recorded
  each run. If the original price was raised after we first saw it (inflate-then-discount), or the item was cheaper at
  some point in the last 14 days, the deal gets an amber warning and loses score (−15 / −10). Each tracked item also
  shows its price range ("Tracked since Nov 18: $59–$79"). Only retailer-verified prices are judged, because deal-site
  headlines are too noisy.
- **Promo codes** (`codes.py`): codes are pulled from deal text ("use promo code EARLYBF", "w/ code BFCM26") and from brand
  homepage banners ("Code: EARLY"), and shown as copy buttons. Prose like "no code needed" or "zip code" is ignored.
- **Stack hints** (`stacks.py`): each build reads Card Scout's published `cards.json`. Deals and brand sales at a store with
  Rakuten cash back or a recent card-linked offer get 💸 and 💳 badges and a small score bonus. If Card Scout is down,
  nothing breaks.

## Breakage alerts

`tools/health.py` runs as the last CI step, even when earlier steps fail. It checks the fresh data against floors:
85%+ of sources online (Reddit excluded), 60%+ of brand stores readable, 1,000+ deals, 400+ clothing deals, and the
critical feeds. It keeps one GitHub issue, **"Site health: needs attention"**, which opens when something is wrong
(GitHub emails the owner), updates when the problem list changes, and closes itself when the next build passes. No open
issue means nothing to do.

## Page weight

The page embeds only what it uses: empty or default fields are omitted (the page restores them on load), brand-store
summaries are dropped, tracking parameters are stripped from links, non-clothing deals scoring below
`MIN_NONCLOTHING_SCORE` are left off, and each brand carries at most 12 thumbnails. Off-screen cards use
`content-visibility` so phones render faster. Roughly 3.2 MB → 1.6 MB raw (600 KB → 360 KB compressed).

## Memory between runs

`history.py` downloads the previous `history.json` from the live site at the start of each run, so nothing extra is
committed. That gives **NEW** badges (appeared since the previous run; the first run never counts), price-drop and
lowest-price signals, new-promo flags, and each card's timing line ("On sale since Nov 20 · 6 days" for brand-store
items, "Posted Nov 24 · 2d ago" for the rest).

## End dates

`ends.py` reads when a deal ends from DealNews's expiry field or the deal's own words ("Ends 12/1", "through November 30",
"11/22-11/27", "today only", "ends Cyber Monday"). Cards show ⏰ Ends …, the **Ending soonest** sort puts them first, and
deals already over are dropped. About 1 in 4 deals has one; most deals never say.

## Code map

| File | Role |
|---|---|
| `deal_scout.py` | Orchestrates gathering (feeds and brand stores in parallel), processing, history, scoring and output |
| `feeds.py` | HTTP fetching (honors `Retry-After`) and RSS/Atom parsing |
| `shopify.py` | Brand-store scanner: sale collection discovery, products, homepage promo detection, men's/women's balance |
| `gyms.py` | Gym-site scanner: the membership offer line on each gym's page (`config.GYMS`), with NYC locations and basketball courts |
| `scoring.py` | Classification, pricing math, Deal Quality Score, de-duplication, diversification |
| `gender.py` | Who a clothing deal is for |
| `brands.py` | Brand baselines, premium list, brand audience, Shopify store list |
| `history.py` | Run-to-run memory and the fake-sale detector |
| `ends.py` | When a deal ends, from its own words |
| `codes.py` | Promo-code extraction |
| `stacks.py` | Card Scout stack hints (Rakuten and card-linked offers per store) |
| `tools/health.py` | Breakage alerts (the self-closing health issue) |
| `tools/probe_stores.py` | Check candidate Shopify stores from CI before adding them (`gh workflow run probe.yml`) |
| `tools/shots.js` | Real-browser check of both sites: headless Chrome screenshots, JS errors, overflow (see header) |
| `config.py` | Feeds, keyword searches, clothing terms, categories, knobs, `CARD_SCOUT_URL` |
| `template.html` | The site (data is embedded at build time) |
| `tests/` | `test_scoring.py` (logic regressions) and `smoke.js` (renders every tab and filter, then clicks every control, against fresh data). Both run in CI before deploy |

## Run locally

```
pip install -r requirements.txt
python deal_scout.py --open      # or double-click run_deal_scout.bat
python deal_scout.py --quick     # fewer searches, skips the brand-store scan
python tests/test_scoring.py && node tests/smoke.js site/index.html
```

Shopify rate-limits an IP after many requests (HTTP 429). The scanner keeps requests to about 3–4 per store and retries
throttled stores slowly. Repeated local runs in a short time will see fewer stores than the cloud run does.

## Refresh schedule

The workflow is meant to run about every 3 hours. GitHub's own scheduler fires it only every 6–14 hours, so since
2026-11-27 the Windows scheduled task `DealScout-Refresh` on the owner's PC runs `tools/pc_refresh.py` every 30
minutes and at logon. The script starts the workflow only when the live data is 170+ minutes old and no run is
already going. It stops after 2027-01-17, and works only while the PC is awake. Log:
`%LOCALAPPDATA%\DealScout\pc_refresh.log`. Remove it with `Unregister-ScheduledTask -TaskName DealScout-Refresh -Confirm:$false`.

## Enable Reddit (optional)

Create a free "script" app at https://www.reddit.com/prefs/apps and add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
as repository secrets (Settings → Secrets and variables → Actions).
