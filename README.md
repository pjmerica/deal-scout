# Deal Scout

Scrapes Black Friday deals from 100+ feeds and search queries, ranks them with a **clothing bias**, and lists the
best **credit card offers** (sign-up bonuses, card-linked shopping offers, bank bonuses, points promos). The output is a
static site that GitHub Actions rebuilds and redeploys to GitHub Pages every 3 hours.

## What it scrapes

| Type | Sources |
|---|---|
| Deals | Slickdeals (frontpage, popular, hot deals, plus about 60 clothing, brand and Black Friday keyword searches), DealNews (main, clothing, shoes, women's), Hip2Save, Krazy Coupon Lady, Ben's Bargains, 9to5Toys |
| Sale roundups | GQ, Esquire, Men's Health, Glamour, Harper's Bazaar, Who What Wear, Refinery29, PopSugar, Fashionista, Hypebeast, Highsnobiety, Good Housekeeping, RetailMeNot, Offers.com |
| Cards and points | Doctor of Credit (all, cards, bank bonuses), The Points Guy, One Mile at a Time, Frequent Miler, Upgraded Points, Million Mile Secrets, View from the Wing, CreditCards.com, NerdWallet, plus Slickdeals searches for credit cards, Amex/Chase/Capital One offers, Rakuten, gift cards |
| Optional | Reddit (r/frugalmalefashion, r/frugalfemalefashion, r/sneakerdeals, r/blackfriday, r/churning, ...). Needs API keys, see below |

## How deals are ranked

- **Discount**: the % off from the title or description, or computed from "reg. $X" prices
- **Community votes**: Slickdeals thumb score and comment counts
- **Editor signals**: DealNews staff picks, frontpage/popular feed boosts, and being found by more than one source
- **Black Friday relevance**: mentions of Black Friday, Cyber Monday or doorbusters
- **Freshness**: the score halves every 5 days (10 days for card offers)
- **Clothing bias**: clothing deals get score × 1.6 + 12. Tune `CLOTHING_MULTIPLIER` in `config.py`

Card offers are ranked by estimated bonus value, "elevated" or "all-time high" wording, shopping relevance (card-linked
offers, portals, rotating 5% categories, clothing retailers), and community engagement.

## Run locally

```
pip install -r requirements.txt
python deal_scout.py --open      # or double-click run_deal_scout.bat
```

Output goes to `site/index.html`, `site/deals.json` and `site/deals.csv`.

## Enable Reddit (optional)

Reddit blocks anonymous scraping. Create a free "script" app at https://www.reddit.com/prefs/apps, then add
`REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` as repository secrets (Settings → Secrets → Actions) or as environment
variables when running locally.

## Customize

Everything lives in `config.py`: feeds, Slickdeals keyword searches, clothing brands and terms, scoring weights, and the
card playbook text.
