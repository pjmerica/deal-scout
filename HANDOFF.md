# Deal Scout: handoff

**Written:** 2026-11-18 · **Owner:** pjmerica · **Local path:** `C:\Users\pjmer\Documents\deal-scout`
**Repo:** https://github.com/pjmerica/deal-scout · **Live:** https://pjmerica.github.io/deal-scout/
**Sibling:** Card Scout (`Documents\card-scout`, https://pjmerica.github.io/card-scout/), which has its own `HANDOFF.md`

Read this first, then `README.md` (features and scoring) and the code. This file holds what the code doesn't tell you:
the owner's decisions, how things break, and how to check your work.

---

## 1. Read first: the owner's decisions

| Date | Decision |
|---|---|
| 2026-11-18 | **Clothing first.** Clothing deals get ×1.6 + 12 (`config.CLOTHING_MULTIPLIER`). Non-clothing still appears and is never hidden by the gender filter. |
| 2026-11-18 | **Black Friday deals only on this site.** Credit cards, Rakuten cash back, card news and the playbook moved to Card Scout. Don't re-merge. The only bridge is the small stack-hint badges (§7). |
| 2026-11-18 | **Men's / Women's / Kids switch.** Unisex items and storewide sales count as "Everyone" and **appear in both Men's and Women's views** (owner confirmed). |
| 2026-11-18 | **Runs until January 17, 2027, no keepalive.** Enforced by the `guard` job in `scout.yml` (`END_DATE`): scheduled runs do nothing after that date, while manual runs and pushes still work. Separately, GitHub disables scheduled workflows in public repos 60 days after the last commit. To extend, change `END_DATE` (ask the owner first). |
| 2026-11-18 | From the improvement list, the owner **declined for now**: size filter, watch-list alerts, hourly runs over Thanksgiving weekend, enabling Reddit. They're in the backlog (§12); ask before doing them. |

---

## 2. Run, test, deploy

| Task | How |
|---|---|
| Run locally | `py -X utf8 deal_scout.py --open` (about 30–120 s). `--quick` skips brand stores and most searches |
| Logic tests | `py -X utf8 tests/test_scoring.py` (44 regression tests, one per fixed bug or feature) |
| Page smoke test | `node tests/smoke.js site/index.html`: runs the page JS in a DOM stub, renders every tab × filter/gender variant, then **clicks every tab, chip, switch and button**. Fails on a throw, empty output, `undefined` or `NaN` |
| Real-browser check | `tools/shots.js` (headless Chrome over CDP, both sites, desktop + phone screenshots). See its header for usage |
| Health | `py -X utf8 tools/health.py` locally (prints only). In CI, `--issue` manages the health issue (§9) |
| Deploy | `.github/workflows/scout.yml`: push to `main`, every 3 h (`17 */3 * * *`), or manual (`gh workflow run scout.yml`). Order: tests → scrape → smoke → summary → health (always) → Pages. **A failing test blocks the deploy**, so the live site keeps its last good build |
| Test the alert | `gh workflow run scout.yml -f health_test=true` opens the health issue; the next normal run closes it |

Nothing generated is committed (`site/` is gitignored). Pages source is "GitHub Actions".

---

## 3. Data flow

```
feeds.py (RSS: Slickdeals ×~90 searches, DealNews, Hip2Save, editors…) ─┐
shopify.py (205 brand stores: sale collections, homepage promo)       ─┼─> scoring.process (dedupe, classify, gender,
                                                                        │     pricing, codes)
history.load (previous history.json from the live site)               ─┘          │
                                                    history.apply (NEW, price drop, fake-sale) 
                                                    stacks.apply (Card Scout badges)          
                                                    scoring.score_all (quality score, tiers)  
                                                    write_outputs -> site/index.html (data embedded),
                                                                     deals.json, deals.csv, history.json
```

---

## 4. Sources and how they break

- **Slickdeals RSS** (`newsearch.php?...&rss=1`): frontpage, popular, hot deals, plus keyword searches in `config.py`.
  The "Thumb Score" is parsed from `content:encoded`. Pagination doesn't work (page 2 = page 1). **Multi-word queries
  are sent quoted** (`sd_url`): unquoted, "free people" matched any post containing both words. Frontpage/Popular
  membership is applied to every copy of the thread (`cross_feed_flags`).
  **Store name** (`feeds.sd_store`, since 2026-11-18): the first outclick link carries `data-store-slug="macys"`
  (about 88% of items), and most descriptions open "Macy's [macys.com] has…" ("X via Amazon" → Amazon). The slug wins, named
  through `feeds.SLUG_NAMES`, or with the description's spelling when the two agree. Before this, 48% of feed deals had no
  store (only "at Amazon" in a title was read); after, about 13% (user posts that name no store).
- **DealNews RSS**: has `<retailer>`, `<price>`, `<staffPick>`, `<expires>`. Its category IDs are odd: **c205 is Kids' Clothes,
  not men's**, and c206, c207 and c208 return **travel** deals (until 2026-11-25 the "Women's" and "Shoes" feeds were c207/c208,
  so they never had a clothing item). Men's and Women's are filters on c202 (`/c202/Clothing-Accessories/f1/Mens/`,
  `f2/Womens/`); shoes are c280, coats c489, jeans c515, hoodies c866, activewear c487, kids' shoes c559. The category
  page's links list the rest. **Check a new DealNews feed's titles before adding it.** Summaries contain price-history
  phrases ("best price we could find by $X").
- **Dappered** (menswear deal blog) and **TechBargains** (general deals) were added 2026-11-25, plus Gear Patrol, The
  Strategist (its feedburner address; `nymag.com/strategist/rss/` is dead), Marie Claire, Elle and Vogue as roundup feeds.
  Checked and left out: Kicks Deals, Fat Kid Deals, DealsOfAmerica, DealSea, Mashable deals, InStyle, Real Simple, Today
  (no feed or blocked); Put This On, BuzzFeed Shopping, Sneaker News, Primer (not sale posts).
- **Hypebeast** answers from a home connection but not from GitHub's runners, so it shows "unavailable" in CI. Not broken.
- **camelcamelcamel top drops**: kept only at 20%+ drop. Titles read "down X% ($saving) to $price from $orig".
- **Blocked or useless, don't retry:** Reddit (403/429 without OAuth keys), Dealmoon, Wirecutter, Uniqlo, J.Crew,
  TopCashback, cashbackmonitor, camelcamelcamel popular (Cloudflare), Brad's Deals and blackfriday.com (no feeds).
- **Symptom of breakage:** a source shows "unavailable" or 0 in the How it works → Sources table, and the health issue opens.

---

## 5. Brand stores (`shopify.py`): the fragile part

- **Shopify rate-limits by IP across all its stores** (429, `Retry-After: 60`). After a few dozen requests from your PC,
  *every* Shopify store returns 429 for a while, including stores you never touched. **So local runs scan only ~20 of 205
  stores. Judge brand-store health from the cloud run, never from a local run.** A 429 when probing a new store means
  "Shopify store, throttled" (probably fine from CI); a 404 means it doesn't expose `/products.json`.
- Per store, about 3–4 requests: `/collections.json` → pick up to 2 sale handles by score (`_handle_score`: exact
  `sale`/`black-friday` > `bfcm-*` > `*-sale` > outlet/archive; old years and department slices penalized) → 1–2 product
  pages → fallback `/products.json` if few sale items. `fetch(max_wait=6)` gives up rather than sleeping 60 s.
  A slow second pass retries stores that returned nothing.
- **Images:** always append `width=400` (`&` if the URL already has `?v=`). Without it Allbirds served 3.9 MB PNGs and
  thumbnails showed blank.
- **Variants:** stores list each colour or inseam as its own product. `collapse_variants` keeps the deepest discount per
  base title (text before ` | `, ` - `, `(`) and the page shows "+N more colors/sizes".
- **Homepage promo** (`promo_from_html`): the smallest element around each "% off" that explains itself (Black
  Friday / sitewide / everything…), excluding sign-up, next-order, filter-menu and product-grid text. A promo code is taken
  from the surrounding block **only if that block holds a single promo** (Steve Madden's bar paired a 50% promo with
  another slide's code). Three or more different "% off" values with no dollar amount is a **filter menu, not a promo**
  (Faithfull's "20% Off Sale 30% Off Sale … 70% Off Sale" ranked as a 70% sitewide sale); tiered offers ("30% off $100,
  40% off $200") name dollar amounts and are kept. "70-80% off" counts as up to 80%. `TRAILING_NAV` strips "SHOP: …" and
  "SHOP WINTER ARRIVALS"-style navigation.
- Stores that stopped exposing data: Buck Mason, Rhone, Vuori, Bombas, SKIMS, Spanx (404). **To add stores:** list them in
  `tools/store_candidates.txt`, run `gh workflow run probe.yml` (it checks from CI, where nothing is throttled; results are
  on the run summary), then add the open ones to `brands.SHOPIFY_STORES` with their `BASELINE`, `PREMIUM` and
  `BRAND_AUDIENCE` entries. 55 stores (women's, shoes, kids, outdoor) were added this way on 2026-11-18, for 136 total,
  and 69 more on 2026-11-25, for 205. `store_candidates.txt` lists every store already probed and why it was left out,
  plus the open ones with nothing on sale yet, to re-probe later. Bag-first brands (Herschel, Dagne Dover,
  Mission Workshop) were left out on purpose: bags count as clothing accessories and would crowd the clothing.
- **Stores with a sitewide promo but 0 items on sale** (Toad&Co, Jenni Kayne, Ten Thousand, Cuyana, Rails): they take the
  discount at checkout, so `compare_at_price` is empty or equal to the price. Their promo still shows as a store-sale card.
  Not a scanner fault.
- **Collection choice** (`_handle_score`): Black Friday words count anywhere in a collection name ("30-off-mens-bfcm"), and
  collections named for another season lose 70 points ("july-sale", "labor-day-sale-2026" in November: Oliver Cabell's
  scan picked those until 2026-11-25). Names that say "not on sale" ("non-markdown-…", "all-products-minus-sale-items")
  are rejected.
- **Store names that are ordinary words** (Cuts, FRAME, MOTHER, Primary, Stance, Represent…) go in
  `brands.AMBIGUOUS_NAMES`. They are never matched in deal-site headlines ("price cuts" once tagged a TV deal as the brand
  Cuts). Their brand-store items still know their brand.
- Apparel brands that also sell home goods (Hill House, Cozy Earth, Barefoot Dreams): `config.CLOTHING_FALSE_POSITIVE`
  keeps duvets, pillows, throws and similar out of clothing.

---

## 6. Classification details worth knowing

- **Clothing:** `scoring.classify`, with terms in `config.CLOTHING_TERMS`. Brand-store items are clothing unless false-positive
  words appear. Materials (cashmere, merino, denim) count as clothing but **not** as a garment category. Department
  stores count only weakly (`WEAK_RETAILERS`), so Macy's fragrance isn't clothing.
- **False-positive words must be anchored** (`\bcruises?\b`, not `cruise`). A brand-store item that matches one is not clothing
  at all. Unanchored, "cruise" hid Allbirds', Rothy's and Filson's Cruiser line, "paint" a "Painted Floral" dress, "quilt"
  quilted vests and hoodies, "flight" a "Flight Hoodie", "tire" every "entire"/"attire", "cat " Target's Cat & Jack (fixed
  2026-11-25). Run any new word against `deals.json` titles before adding it.
- **Brand-store titles start with the store's name** ("Kickee Pants: Knot Headband"). Garment words and false-positive
  words are matched on the product part only (`product` in `scoring.classify`): before 2026-11-25 every Kickee Pants item
  was Bottoms and "Monday Swimwear: Cayman Necklace" Swimwear. "Dress" before sock/shirt/shoe/pants is not a dress.
- **Garment type (the chips on the Clothing tab).** `CLOTHING_TERMS` decides both *whether* an item is clothing and its type,
  so it holds only unambiguous words. Ambiguous ones ("top", "short", "tank", "trunk", "jean", "bikini", "bag") are in
  `config.CLOTHING_TAG_FALLBACK` and only fill in a missing type on an item that is **already** clothing, first match wins
  (`scoring.fallback_tags`). Then `CLOTHING_TAG_BRAND` covers one-garment stores that name products by model (Kizik, Sarah
  Flint, Stance). Storewide sales stay untagged. An item with no type disappears when someone picks a chip: on 2026-11-23,
  417 of 1,874 clothing deals had none; after the fix about 150 do, mostly storewide sales. The chip list is
  `CLOTH_CATS` in `template.html` (Swimwear added 2026-11-25): keep it in step with `CLOTHING_TERMS`.
- **Gender** (`gender.py`), in order: title words (handles curly apostrophes "Women’s", "unisex", "men's & women's") →
  **a kids' brand → Kids** unless the item is marked adult (Little Sleepies' `age:adult` tag, Tea Collection's "Adult
  Pajama Top"; before 2026-11-25 their girls' dresses landed in Women's) →
  garment hints (dress, skirt set, bra → Women's) → **structured retailer tags** (`gender:Men`, `division:Womens`) →
  free-text tags (**"color-family" is not "family" = unisex**: that bug labeled Faherty's men's shirts as unisex) → brand
  audience (`brands.BRAND_AUDIENCE`) → description → storewide sale → Everyone.
- **Pricing:** title first. Extras compound (50% + extra 30% = 65%). A final "$X down from $Y" price is never stacked
  again. "Extra X% off sale items" assumes a 30% base.
- **Brand names that are ordinary words, part 2** (`brands.CONTEXT_NAMES`: Diesel, Mango, Express): still matched in
  headlines, but counted only when the title starts with the brand or names a garment. Without it "8L Diesel" made a car jump
  starter clothing, "Lavender + Mango" Lysol wipes, "Keurig K-Express" a coffee maker. (`AMBIGUOUS_NAMES` is the stricter
  list: never matched in headlines at all.) Garment words in other senses are in `config.CLOTHING_FALSE_POSITIVE`
  (compression *massager*, *thermal printer*, "Tee Off", *cable tie*, "no vest needed", ebooks). Clothing gets ×1.6 + 12, so
  every false positive also jumps up the rankings: when you spot one on the live site, add the word and a test.
- **Store names** (`scoring.tidy_store`): "Woot! An Amazon Company" → Woot, "Best Buy Locations" → Best Buy, "Newegg ahead of
  Black Friday" → Newegg, "Macys.com" → Macy's; spelling variants of stores in `feeds.SLUG_NAMES` fold into one name. A store
  matters for the per-store cap on the Best tab, the Card Scout badges and the brand baseline, so check those when you
  change store extraction.
- **Gender and stores:** a store's audience counts only for a storewide sale. Macy's sells to everyone, but a sweater at
  Macy's isn't unisex, so it stays unlabeled (the page offers "+ N unlabeled"). A brand that sells to everyone (Nike) ranks
  below a description naming one audience ("Foot Locker has the Nike Men's…" → Men's).

---

## 7. Card Scout stack hints (`stacks.py`): a cross-repo contract

Each build reads `https://pjmerica.github.io/card-scout/cards.json` and uses `rakuten[].store/rate/pct/url/elevated` and
`news[].title/link/card_category/retailers/age_days/warnings`. Store names are matched by normalized name, with a
prefix match only when it's unambiguous ("Saks" matches nothing because there are two Saks stores). If you change those fields
in Card Scout, update `stacks.py` in the same change (Card Scout's HANDOFF §4b says the same).

---

## 8. History and the fake-sale detector (`history.py`)

- Loaded from the live site at the start of every CI run (nothing committed). If the site is down, history restarts and
  the health check notes it.
- Per item: first/last seen, price, min, first original price, and a price series (changes only, last 30). Kept 30 days.
- `orig_raised` (−15) and `was_cheaper` (−10, 14-day window) apply to **retailer-verified** prices only. Deal-site
  headline prices are too noisy to judge. Tracking started 2026-11-18, so expect the first flags in late November.

---

## 9. Health issue (`tools/health.py`)

Runs last, `if: always()`, with each step's outcome. Problems: a failed CI step, under 85% of sources online (Reddit
excluded), fewer than max(60, 60%) of brand stores readable, under 1,000 deals or 400 clothing deals, or a critical feed empty.
It keeps **one** issue titled "Site health: needs attention": creates it, edits it and comments when the problem list
changes (signature in an HTML comment), and closes it when clear. Needs `permissions: issues: write`. Verified end to end
on 2026-11-18 (issue #1 opened by the test switch and closed by the next run).

---

## 10. Page weight

The data is embedded in `index.html`. `write_outputs.slim()` omits empty or default fields (the page restores them on
load: see the `for(const i of items)` block in `template.html`), drops brand-store summaries, strips tracking params
(`strip_tracking` keeps the host as given), leaves out non-clothing deals below `MIN_NONCLOTHING_SCORE`, and keeps 12
thumbnails per brand. **Which 2,400 deals go on the page** is `scoring.pick_for_page`: each brand store keeps its best 8
(`MAX_ITEMS_PER_STORE`), feed deals get first claim on 1,300 slots (`FEED_SLOTS`), unused room goes to the other side.
Without it, the 205 stores' markdowns filled every slot on 2026-11-25 (non-clothing deals 478 -> 91, Slickdeals/DealNews
clothing 576 -> 348). Adding stores or feeds changes the balance: check both counts in `deals.json` afterwards. Live size went from 3.2 MB to 2.1 MB raw (~600 KB to ~465 KB compressed) on 2026-11-18. If you add a field the
page uses, make sure it survives `slim()` or gets a default on load.

---

## 11. Lessons learned (save yourself the time)

- **Windows:** use `py`, not `python`. Pass `-X utf8` (the console is cp1252). `py -I` ignores `PYTHONIOENCODING`.
- **Don't put Python patch code in Bash heredocs:** backslashes got mangled (`\b` turned into a backspace character in
  `scoring.py`). Write a patch script to a file and run that. If it happens, check with `grep -P '\x08'`.
- **The smoke test must click things.** Rendering every tab passed while a tab-click handler threw on a removed state
  field. That bug was live for about an hour.
- **Look at the real page** (`tools/shots.js`) after UI work. The DOM-stub smoke test can't see images, layout or
  overflow.
- Slickdeals's "credit card" search returns wallets and microSD cards. Keyword searches need junk filters.
- **Audit the live data, not just the tests.** Download `https://pjmerica.github.io/deal-scout/deals.json` and look at
  clothing items with no garment tag, the `store` values, and the brand-sale promo texts. That's how the 2026-11-18
  evening fixes were found (Lysol wipes and jump starters in Clothing, 48% of feed deals with no store, a filter menu read
  as a 70% sale). All tests passed while those were live.
- GitHub cron can start runs late. A manual `gh workflow run` is fine at any time.

---

## 12. Backlog (ideas, not commitments; ask the owner)

- Declined for now (§1): **size filter** (Shopify variants carry sizes and stock), **watch-list alerts** (could reuse the
  health-issue mechanism), **hourly runs Thanksgiving–Cyber Monday**, **Reddit keys** (r/frugalmalefashion and
  r/frugalfemalefashion are the best clothing sources missing).
- More brand stores: done 2026-11-18 (55 added). Paige returned 429 from CI on two probes (the second on the evening of
  2026-11-18), so it's left out. Don't retry it.
- Slickdeals searches for big retailers that block scraping: done 2026-11-18 (about 40 added to `SLICKDEALS_CLOTHING_QUERIES`).
- ~~Page packaging: load data as a separate file to shrink transfer~~ **checked 2026-11-18, not worth it:** GitHub Pages
  already gzips `index.html` (2.4 MB raw → 497 KB transferred), so a separate data file transfers about the same, and
  `fetch` is blocked on file:// pages, so `--open` would stop working. If phones ever feel slow to parse, embed the data
  as `<script type="application/json">` and `JSON.parse` it (and update `tests/smoke.js`).
- Checked 2026-11-18, left alone: a higher per-store cap on the Best tab for big retailers (Amazon, Walmart, eBay). Most
  of their crowded-out deals are blocked by the per-brand cap anyway (Adidas, Nike, Carhartt); a cap of 3 changed about 3
  of 60 picks, mostly by adding no-name Amazon items.
