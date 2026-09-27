# Four-category current snapshot validation

Collected September 25, 2026, 22:17:24–22:17:29 UTC. Each category has its own
timestamped raw HTML, product JSON, hashed manifest, normalized JSON/CSV,
validation.json, and metrics.json. Previous current and historical evidence and
outputs are retained. No historical collection or dashboard work was performed.

| Category | Product-colors | Styles | Both prices available | Discount Breadth | Median Discount Depth | Deep-Discount Share ≥30% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Women's Jeans | 190 | 65 | 100% | 98.95% | 51.08% | 85.26% |
| Women's T-Shirts & Tanks | 198 | 58 | 100% | 83.33% | 51.90% | 60.61% |
| Men's Jeans | 99 | 26 | 100% | 100.00% | 51.22% | 71.72% |
| Men's T-Shirts | 195 | 84 | 100% | 75.38% | 51.36% | 46.67% |

Breadth and deep-discount share use all listed observations; median depth uses
only discounted observations. The two headline measures remain Breadth and
Median Depth. Mean, band distribution, deep-discount share, counts, and coverage
remain available as supporting diagnostics. Calculations and schema are unchanged.
One evidence-preservation correction retains numeric source percentageOff=0
rather than converting it to null; source percentages never drive calculations.

## Scope and comparability

All four responses use the same public endpoint, US market/currency, anonymous
non-cardholder settings, pageSize=200, pageNumber=0, and product-color unit.
The category ID and department vary explicitly. Stable canonical category URLs
omit navigation tracking and fragments; the Women's department is 136 and Men's
is 75, sent explicitly to the product endpoint. No new collection mechanism,
retries, pagination, or access-control workaround was introduced.

The first-response scope preserves the existing sampling method, and **does not
establish full-category coverage**:

| Category | Listed colors / API total | API pages | Missing product promo text |
| --- | ---: | ---: | ---: |
| Women's Jeans | 190 / 455 | 3 | 0 / 190 |
| Women's T-Shirts & Tanks | 198 / 505 | 3 | 0 / 198 |
| Men's Jeans | 99 / 103 | 1 | 1 / 99 (1.01%) |
| Men's T-Shirts | 195 / 260 | 2 | 48 / 195 (24.62%) |

API totals are metadata, not independently verified complete populations. The
Men's Jeans discrepancy remains unexplained even though pagination reports one
page. The parser retains exactly the unique categories[].ccList identities and
excludes additional nested swatches. None of the samples is represented as a
complete census. All four responses report responsePersonalized=true; featured
ranking, assortment, and availability can change sample composition. The earlier
Women's Jeans snapshot had 188 observations / 64 styles, versus 190 / 65 now;
both snapshots remain available and this is not a matched-product panel.

The common source structure supports the same displayed-current versus retailer-
reference price calculation across these category samples. It does not establish
checkout savings or separate permanent markdowns from temporary events. Promo
flags and priceType codes remain uninterpreted source evidence; missing messaging
is unknown, not proof of no promotion. Category mix and color counts per style
also affect comparisons. Do not pool category shares or interpret movements as a
causal promotion change without assessing membership and coverage.

## Validation and reproducibility

All 682 normalized observations were reconciled against raw JSON pointers:
identities, names, both prices, price types, and color-level promotional flags
match. Listed source membership exactly equals normalized membership; raw file
hashes pass. No missing names or prices were found. This increment validates
against saved API evidence; it does not claim a new rendered-browser or checkout
reconciliation. Earlier browser validation of field semantics is documented in
pricing-semantics.md.

The full offline suite passes **39 tests**, covering every category's routing and
collection/parse/metric round trip, wrong-category and manifest conflicts, raw
hash tampering, preserved blocked responses without retries, batch resumption,
missing/full prices, exact discount boundaries, and historical regressions.

```sh
.venv/bin/python -m gap_tracker.current
# Only one category:
.venv/bin/python -m gap_tracker.current --category women-tshirts-tanks
# Resume saved successful collections and regenerate derived outputs offline:
.venv/bin/python -m gap_tracker.current --batch data/processed/runs/four-categories-20260925.json
.venv/bin/python -m unittest discover -s tests -v
```

Batch paths: data/processed/runs/four-categories-20260925.json.
Consolidated validation: data/processed/runs/four-categories-20260925-validation.json.
These contain the exact raw/processed snapshot paths. Each default invocation
creates a new UTC-dated batch; no existing snapshot is overwritten. An explicitly
resumed batch reuses saved successful collections; a failed collection has no
successful raw path and a subsequent explicit resume attempts it again. Error
bodies remain preserved in their separate incomplete raw directories.

Generated evidence is Git-ignored and must be copied separately when sharing the
research dataset. Source code and methodological documentation remain small and
independent of the retained historical parser.
