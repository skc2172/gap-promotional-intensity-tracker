# Gap promotional-intensity prototype

This prototype collects **four current Gap categories** (Women’s Jeans, Women’s
T-Shirts & Tanks, Men’s Jeans, and Men’s T-Shirts), normalizes their listed
product-color records, and calculates deterministic snapshot metrics.
See [paginated validation](docs/paginated-current-categories.md) for the latest results;
[earlier first-page validation](docs/current-categories.md) is retained for comparison.
A bounded Wayback proof of concept covers three requested historical periods;
A local Streamlit dashboard is now available (launch instructions below). See [historical results and comparability](docs/wayback-proof-of-concept.md).

## Run

The existing `.venv` and `requirements.txt` were retained. This increment uses
only `requests` plus Python's standard library; the existing larger dependency
list includes packages intended for later work. A fresh minimal environment can
install `requests` with `python -m pip install requests`.

```sh
python -m gap_tracker.current  # All four categories, new dated snapshots
# Or collect one category independently:
python -m gap_tracker.collect --category men-jeans
# Use the raw directory printed by the collector:
python -m gap_tracker.parse data/raw/20260925T150058215580Z
python -m gap_tracker.metrics data/processed/20260925T150058215580Z/observations.json
python -m unittest discover -s tests -v
```

Use `.venv/bin/python` in place of `python` if the environment is not activated.
Collection needs network access; parsing and tests work offline. Each collection
creates a new timestamped directory. Rerunning the parser replaces only derived
files for that snapshot. `data/` is ignored by Git but retained locally; preserve
or transfer that directory separately when reproducing this analysis elsewhere.

## Minimal separation

- `gap_tracker/categories.py`: fixed category IDs, US departments, and canonical URLs.
- `gap_tracker/current.py`: sequential collection → parsing → metrics with a resumable batch manifest.
- `gap_tracker/collect.py`: retrieve the HTML shell and all API-reported product JSON
  pages. Save unmodified response bodies plus UTC timestamps, URLs, HTTP
  status, headers (excluding response cookies), and SHA-256 hashes in a manifest.
  Save error responses too, then stop. No retry, authentication, anti-bot workaround,
  or product-detail crawl.
- `gap_tracker/parse.py`: verify raw hashes, read files offline, join category
  references to product-color records, and write CSV/JSON observations and a
  validation report. Each row has a JSON pointer back to its original record.
- `gap_tracker/metrics.py`: source-independent, offline calculations from normalized
  observations. Writes a separate `metrics.json` with snapshot context, input file
  hash, counts, denominators, and definitions. Leaves all underlying observations
  and their product-color/style identifiers intact.
- `gap_tracker/wayback.py`: resumable, bounded archive discovery and raw collection.
- `gap_tracker/parse_wayback.py`: historical HTML inspection and a separate adapter
  for the inspected archived API; historical metrics require a price-basis review.
  Presentation is implemented in app.py with read-only adapters in dashboard_data.py.

## Source discovery and semantics

Page: <https://www.gap.com/browse/women/jeans?cid=5664> (US market, Women department 136).
Jeans is a recognizable, reasonably consistent category with regular, promotional,
and markdown pricing. It is not representative of all Gap merchandise.

The ordinary HTTP response is a Next.js HTML shell with loading placeholders,
navigation, banners, and application configuration—not product price records.
Navigation links to products are not category observations. Running JavaScript
in the browser loads product cards; those expose `Original price:` and `Current
price:` accessibility labels and a separate product marketing flag.

Inspection of the page's public JS established its category-product endpoint:
`https://api.gap.com/v2/catalog_search_products/v2/category_products`.
The enabled `plp-category-products-endpoint` flag selects it. The collector uses
the ordinary page parameters, anonymous `client_id=0` / `session_id=0` defaults,
and non-cardholder segment. No private credentials or browser cookies are copied.
The site specifies `en_US`, not `en-US` (the latter returned a 400 during discovery).
A preliminary request without the complete anonymous/dynamic-facet parameters
returned a different assortment. Only the implemented, fully specified request
is used for the saved research snapshot.

The parser follows `categories[].ccList` and joins `(styleId, ccId)` to
`products[].styleColors[]`. The response contains additional swatches; counting
every nested color would broaden the sample beyond the category listing. Product
names prefer the explicit color-level `styleName`, then the parent `styleName`.
Category is collection context; USD is the fixed US-market context.

| Normalized field | Evidence/rule |
| --- | --- |
| `snapshot_date` | UTC date of product-response collection |
| `product_id`, `style_id` | `ccId`, parent `styleId` |
| `original_price` | `regularPrice`, the site's reference/list price |
| `current_price` | `effectivePrice`, the advertised product-card price |
| `discount_pct` | `100 × (original − current) / original`, four decimal places |
| `is_discounted` | Current below original; null if either price is missing |
| `promo_text` | Explicit color-level marketing flag content; null if absent |
| `source`, `source_url` | `gap_current`, category URL; exact API URL in manifest |

`discount_pct` uses percentage points (30 means 30%). Decimal arithmetic avoids
binary rounding drift. The site's rounded `percentageOff` is preserved in raw
JSON but not used to calculate discounts. A missing price is not copied from the
other price. Invalid, zero reference, and inverted prices fail for inspection.
JSON nulls and CSV blank cells mean unknown. Offer absence does not mean no offer.

Original price is a retailer reference price, not proof of an earlier transaction
price. No checkout, coupon, membership, app, shipping, or tax adjustments are
applied. A sitewide event banner remains raw page evidence and is not attached to
every product. Style-level flags also remain raw rather than being projected onto
individual colors. `promo_text` can include exclusions or final-sale conditions.

## Demonstrated snapshot: 2026-09-25 15:00 UTC

Raw directory: `data/raw/20260925T150058215580Z/`.
Outputs: `data/processed/20260925T150058215580Z/`.

| Validation | Result |
| --- | --- |
| Listed, unique product-color observations | 188 |
| Unique parent styles | 64 |
| Missing names | 0 / 188 (0%) |
| Missing current prices | 0 / 188 (0%) |
| Missing original prices | 0 / 188 (0%) |
| Missing product marketing text | 0 / 188 (0%) |
| API category total / requested page size | 453 / 200 |

The first eight API-listed observations were checked against rendered product
cards: names, both prices, and marketing text matched. Examples:

| Product-color ID | Product | Original | Current | Marketing text |
| --- | --- | --- | --- | --- |
| 911424002 | Low Slung Extra Baggy Jeans | 89.95 | 44.00 | 50% off + extra 10% in the app |
| 1185301002 | High Rise Stride Wide-Leg Jeans | 89.95 | 71.00 | Extra 10% off in the app |
| 911401002 | Low Rise Long & Lean Jeans | 99.95 | 49.00 | 50% off + extra 10% in the app |

All normalized rows were additionally checked against their raw JSON records.
Unit tests cover missing and invalid prices, discount arithmetic, exclusions of
unlisted colors, duplicate category references, and unknown offer text.

**Coverage remains limited:** the browser reported 200 loaded cards, but the
separate saved API response explicitly listed 188 IDs (389 nested color records).
The cause of the 12-item difference is not established. We do not fill the gap
with unlisted colors, and do not claim this response reproduces the entire browser
grid. The endpoint reports `responsePersonalized=true` even with anonymous
defaults. Featured ranking, personalization, inventory, and assortment changes
can therefore change the observed sample. Only the saved response is reproducible;
future collections need not have identical membership or ordering.

This demonstrates collection and deterministic parsing for an explicitly bounded
sample. Full browser/API coverage reconciliation, stability across collection
dates, and checkout offer eligibility are not established. Resolve those coverage
questions before treating any future category trend as an investment signal.

## Deterministic snapshot metrics

Run the metrics command above to write `metrics.json` beside `observations.json`.
No collection is performed. The module recalculates markdowns from original and
current prices; it ignores stored discount fields and promotional text. Each
product-color observation has equal weight; styles are counted separately.
Exact rational arithmetic is used before rounding output to six decimal places,
so exactly 30% qualifies and a value just below 30% does not. Shares in JSON are
fractions (0–1); discount percentages are percentage points (30 means 30%).

Both shares use **all observations** as the denominator. Missing prices remain
unknown and contribute to neither full-price nor discounted counts; if present,
reported shares are lower bounds based on confirmed discounts. Missing counts
are explicit and discount bands exclude unknowns. Mean and median include only
observations with a strictly positive calculated discount, and are null when
there are none. An empty dataset, duplicate product-color identities, mixed
snapshot contexts, or invalid prices cause an error instead of a misleading summary.

For the saved 2026-09-25 snapshot:

| Metric | Value |
| --- | --- |
| Product-color observations / unique styles | 188 / 64 |
| Missing-price observations | 0 |
| Discounted share | 186 / 188 = 98.94% |
| Median discount among discounted observations | 51.08% |
| Mean discount among discounted observations | 48.61% |
| Share discounted at least 30% | 161 / 188 = 85.64% |

Band counts: 0%: **2**; >0–<20%: **0**; 20–<30%: **25**;
30–<40%: **0**; 40–<50%: **2**; ≥50%: **159**.
These describe the saved bounded sample; the coverage limitations above still apply.

## Schema v2 and headline measures

The headline metrics are **Discount Breadth** (`share_discounted`) and
**Median Discount Depth** (`median_discount_pct_among_discounted`). All existing
calculations remain; the other metrics, messaging, and coverage statistics are
supporting diagnostics. This changes presentation priority, not definitions.

Schema v2 appends nullable `source_percentage_off`, `source_price_type`,
`promo_evidence`, `price_basis`, and `provenance`. Existing fields are intact; P/M/R
are preserved without interpretation. CSV object fields contain JSON. See the
[three-period report](docs/wayback-proof-of-concept.md) for provenance, capture
selection, actual dates, results, limitations, and commands. Current v1 outputs
were retained under the original processed snapshot's `schema-v1/` directory.

## Interactive research dashboard

Launch `.venv/bin/python -m streamlit run app.py` from this directory.
The dashboard reads saved snapshots; **Refresh Current Data** explicitly runs the
existing four-category pipeline into a new dated batch. See the
[dashboard guide](docs/dashboard.md) for workflow, refresh handling, validation,
and historical-comparability limits. The earlier statements about deferred
presentation describe the prior pipeline increments; this is the first UI version.

## Historical backfill

The archive workflow now searches both known product endpoint families without
date bounds and inspects annual category-page representatives across indexed
years. It has added 25 selected historical snapshots across four categories,
plus the retained POC observation. See [the dated results and qualified
comparability assessment](docs/historical-backfill.md).

```sh
.venv/bin/python -m gap_tracker.backfill --collect --html
# Review newly recovered evidence before publishing new price metrics:
.venv/bin/python -m gap_tracker.backfill_publish
.venv/bin/python -m gap_tracker.backfill_report
```

Backfill is separate from Refresh Current Data. The dashboard displays saved
validated archive samples as discrete dated points, with source/coverage labels.
The optional archive network-error fallback uses the standard `curl` executable;
HTTP access denials are not bypassed.
