# Deal Scout

Finds the **best Black Friday deals**, with a **clothing bias**. Each deal gets a quality score that lists its reasons.
GitHub Actions re-scrapes every 3 hours and redeploys the site to GitHub Pages:
**https://pjmerica.github.io/deal-scout/**

> **Credit cards, cash back and card news moved out on 2026-11-18** to the companion project **Card Scout**
> (`Documents\card-scout`, https://github.com/pjmerica/card-scout, https://pjmerica.github.io/card-scout/). Its
> `HANDOFF.md` documents the split. Deal Scout's footer and header link to it.

## What's on the site

| Tab | What it shows |
|---|---|
| 🏆 Best | Diversified top 60 (one per store and per brand, colour variants collapsed), then the best picks in each category |
| 👕 Clothing | Every clothing and footwear deal, with category chips (Outerwear, Tops, Footwear, …) |
| 🏷 Brand sales | 81 brands' own stores: live sitewide promo, number of items on sale, typical and max discount, top picks |
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
| Deal aggregators | Slickdeals (frontpage, popular, hot deals, plus about 90 keyword searches: clothing items, ~50 apparel brands, "price mistake", "all time low", gift card deals, and top tech and home categories), DealNews (main, clothing, shoes, women's, kids, electronics, computers, home), Hip2Save, Krazy Coupon Lady, Ben's Bargains, 9to5Toys, DealCatcher, camelcamelcamel top price drops |
| Brand stores (direct) | **81 clothing brands' Shopify storefronts** (Todd Snyder, Taylor Stitch, Faherty, Everlane, Allbirds, Kith, Aimé Leon Dore, Alo, Cotopaxi, Rothy's, Thursday Boots and more). Real sale price vs original price, in-stock sizes, product tags (used for gender), and the live sitewide promo from the homepage banner |
| Editors | GQ, Esquire, Men's Health, Glamour, Harper's Bazaar, Who What Wear, Refinery29, PopSugar, Fashionista, Hypebeast, Highsnobiety, Good Housekeeping, CNET, ZDNet, The Verge, Tom's Guide, TechRadar, Lifehacker, RetailMeNot, Offers.com |
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

**Gender** (`gender.py`), in order of evidence: title words (including curly apostrophes and "unisex"), garment hints
(dress, skirt set, bra → Women's; boxer briefs, tuxedo → Men's), retailer product tags, the brand's audience
(`brands.BRAND_AUDIENCE`), the description, then storewide sales → Everyone.

## Memory between runs

`history.py` downloads the previous `history.json` from the live site at the start of each run, so nothing extra is
committed. That gives **NEW** badges (appeared since the previous run; the first run never counts), price-drop and
lowest-price signals, and new-promo flags.

## Code map

| File | Role |
|---|---|
| `deal_scout.py` | Orchestrates gathering (feeds and brand stores in parallel), processing, history, scoring and output |
| `feeds.py` | HTTP fetching (honors `Retry-After`) and RSS/Atom parsing |
| `shopify.py` | Brand-store scanner: sale collection discovery, products, homepage promo detection, men's/women's balance |
| `scoring.py` | Classification, pricing math, Deal Quality Score, de-duplication, diversification |
| `gender.py` | Who a clothing deal is for |
| `brands.py` | Brand baselines, premium list, brand audience, Shopify store list |
| `history.py` | Run-to-run memory |
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

## Enable Reddit (optional)

Create a free "script" app at https://www.reddit.com/prefs/apps and add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
as repository secrets (Settings → Secrets and variables → Actions).
