# Deal Scout

Finds the **best Black Friday deals**, with a **clothing bias**, and the best **credit card offers**. Each deal gets a
quality score that lists its reasons. GitHub Actions re-scrapes every 3 hours and redeploys the site to GitHub Pages:
**https://pjmerica.github.io/deal-scout/**

## What it reads

| Layer | Sources |
|---|---|
| Deal aggregators | Slickdeals (frontpage, popular, hot deals, plus about 90 keyword searches: clothing items, ~50 apparel brands, "price mistake", "all time low", and top tech and home categories), DealNews (main, clothing, shoes, women's, kids, electronics, computers, home), Hip2Save, Krazy Coupon Lady, Ben's Bargains, 9to5Toys, DealCatcher, camelcamelcamel top price drops |
| Brand stores (direct) | **81 clothing brands' Shopify storefronts** (Todd Snyder, Taylor Stitch, Faherty, Everlane, Allbirds, Kith, Aimé Leon Dore, Alo, Cotopaxi, Rothy's, Thursday Boots and more). Real sale price vs original price, in-stock sizes, and the live sitewide promo from the homepage banner |
| Editors | GQ, Esquire, Men's Health, Glamour, Harper's Bazaar, Who What Wear, Refinery29, PopSugar, Fashionista, Hypebeast, Highsnobiety, Good Housekeeping, CNET, ZDNet, The Verge, Tom's Guide, TechRadar, Lifehacker, RetailMeNot, Offers.com |
| Cards and points | Frequent Miler's best-offers table (237 cards with first-year value estimates), Doctor of Credit's best sign-up bonus list (spend, fee, elevated flags), plus news from Doctor of Credit, The Points Guy, One Mile at a Time, Frequent Miler, Upgraded Points, Million Mile Secrets, View from the Wing, CreditCards.com and NerdWallet |
| Cash back | Rakuten rates for about 100 clothing and department stores, tracked over time to flag elevated rates |
| Optional | Reddit (r/frugalmalefashion, r/frugalfemalefashion, ...). Needs free API keys, see below |

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
   left in stock. Unknown brands score a little lower.
7. **Catches**: in-store only or YMMV, membership required, refurbished, rebates, sponsored posts, sold out or expired.
8. **Freshness**: scores halve every 5 days. There's a small bump for "ends soon", and expired deals are removed.
9. **Clothing bias**: × `CLOTHING_MULTIPLIER` (1.6) plus a flat bonus.

Tiers are percentiles (Exceptional is the top 3%, Great 12%, Good 35%). The **Best** tab is diversified, with at most 2
items per store and per brand and colour variants collapsed, plus a best-of list for each category.

Card offers are ranked by first-year value (Frequent Miler's estimate, or points × conservative cents-per-point + cash −
fee), with bonuses for being on Doctor of Credit's list, an elevated offer, shopping perks (Lululemon or Saks credits,
purchase protection) and a minimum spend you can reach with holiday shopping.

## Memory between runs

`history.py` downloads the previous `history.json` from the live site at the start of each run, so nothing extra is
committed. That gives **NEW** badges, price-drop and lowest-price signals, Rakuten rate history ("elevated vs usual"),
and new-promo flags.

## Code map

| File | Role |
|---|---|
| `deal_scout.py` | Orchestrates gathering (in parallel), processing, history, scoring and output |
| `feeds.py` | HTTP fetching (honors `Retry-After`) and RSS/Atom parsing |
| `shopify.py` | Brand-store scanner: sale collection discovery, products, homepage promo detection |
| `cards.py` | Frequent Miler and Doctor of Credit card offers, Rakuten rates |
| `scoring.py` | Classification, pricing math, Deal Quality Score, de-duplication, diversification |
| `brands.py` | Brand baselines, premium list, Shopify store list, Rakuten store list |
| `history.py` | Run-to-run memory |
| `config.py` | Feeds, keyword searches, clothing terms, categories, card playbook, knobs |
| `template.html` | The site (data is embedded at build time) |
| `tests/` | Logic regression tests, and a smoke test that renders every tab against fresh data (both run in CI before deploy) |

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
