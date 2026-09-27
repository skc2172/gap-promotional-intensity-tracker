# Women's Jeans: three-period historical proof of concept

The proof of concept recovered **one usable, explicitly dated alternative**:
11 April 2025, near the March 2025 target. No product-price observations were
recoverable from the checked September 2025 or March 2026 category captures.
Do not plot April's results as March, or represent missing periods as zero.

## Headline metrics and preserved schema

The headline measures are **Discount Breadth** (`share_discounted`) and
**Median Discount Depth** (`median_discount_pct_among_discounted`). Deep-Discount
Share (≥30%), mean discount, bands, promotional messaging, and sample/coverage
statistics remain supporting diagnostics. No existing calculation or field was
removed or renamed, and no mathematical metric definition changed.

Five nullable fields were appended to the existing normalized schema:

| Field | Evidence preserved |
| --- | --- |
| `source_percentage_off` | Source percentage string; missing/blank is null. Never used instead of price-pair calculations. |
| `source_price_type` | Raw `priceType` code. No interpretation of P/M/R. |
| `promo_evidence` | Structured color flags, badges, style flags and raw exclusion value. Historical `ccMarketingFlagsDetails` and `styleMarketingFlagsDetails` are retained under their original names. Page-level offers remain in the historical validation file, not copied onto products. |
| `price_basis` | `displayed_current_vs_retailer_reference` only when supported; otherwise null. |
| `provenance` | Observed/archive time, retrieval time, exact evidence URL/hash, price-field mapping, requested target period and actual archive timestamp. Historical original API URL is also retained. |

JSON keeps these as structured objects; CSV encodes objects as valid JSON cells.
The original 188 current rows were regenerated from saved raw data with all old
field values unchanged. Original v1 observations, validation, and metrics remain
in `data/processed/20260925T150058215580Z/schema-v1/`. Current raw hashes and all
existing current metric values still match their earlier versions. The live
collection method was not changed.

## Selection and collection

For an otherwise unspecified month, the target anchor is the **15th at 12:00 UTC**.
The bounded search covers ±45 days. Initial monthly-collapsed CDX discovery was
retained; uncollapsed CDX responses then established the nearest captures among
accepted whole-category URLs. URLs with style/color filters or malformed category
IDs were rejected. Category identifiers are verified again in archived HTML.

For each period, three nearest distinct HTML bodies were inspected. An additional
initial page from the interrupted run remains available where the refined
nearest capture differed. Exact completed downloads were reused, not recollected.
The page-referenced historical product endpoint was searched in the same date
window. For March 2025, three API candidates were returned: two filtered captures
were excluded; the unfiltered April 11 response was retrieved.

All HTTP responses, CDX results, response hashes, request metadata, candidate
selection records, and actual Memento timestamps are saved under `data/raw/`.
The archive timestamp is verified against `Memento-Datetime`, not guessed from
the replay URL. HTML is inspected offline. No archived JavaScript is executed,
no live product endpoint supplies historical values, and no missing values are
interpolated. JavaScript assets used for semantic validation are themselves
archived captures, preserved as source text.

This is a bounded proof of concept, not a claim that no other usable capture
exists anywhere in Wayback. Search coverage was the known category URL forms
and the API endpoint referenced by the saved pages; other historical endpoints
or distant dates have not been exhaustively searched.

## Results by target period

| Requested period | Nearest inspected category capture (UTC) | Product-price result | Alternative used |
| --- | --- | --- | --- |
| March 2025 | 2025-03-15 18:37:17 | Category HTML shell: 0 extracted product observations; no price records | **2025-04-11 13:25:36**, archived unfiltered category API; 280 product-color observations / 93 parent styles |
| September 2025 | 2025-09-15 18:23:05 | All three checked HTML bodies lack product records; matching API index returned no captures | None found within the bounded search |
| March 2026 | 2026-03-14 20:28:53 | All three checked HTML bodies lack product records; matching API index returned no captures | None found within the bounded search |

The March 2025 alternative is 27 days after the midpoint anchor and falls outside
March. Its normalized `snapshot_date` is **2025-04-11**; `requested_target_period`
remains **2025-03** and `archive_timestamp` is **20250411132536**.

For pages without product records, price coverage/missingness is **null / not
assessable**, not 100% missing or 0% discounted. Zero extracted rows does not mean
the retailer had zero products. The March 2026 shell even contains a placeholder
“0 of 0 items”; the parser deliberately does not treat it as inventory evidence.

## Structure and promotional evidence

The 2025 category HTML contains a Next.js application shell, category navigation,
page content and a JSON-LD **BreadcrumbList**, not a product list. The March 2026
capture additionally has nine product-card skeletons and placeholder price-label
translations. Translation keys such as `regularPrice` are not numeric observations.
None of the selected HTML bodies contains product links with `pid=`, populated
product cards, or numeric product-price fields detected by the source inspector.
Unrecognized product-bearing structures fail closed for manual inspection.

Page-level promotional text survives in title/alt attributes as well as HTML
paragraphs. It is preserved with its element type, attribute and `page_header`
scope. Some evidence is an image accessibility label, not visible body text.
Examples from the nearest captures:

- March 2025: Friends & Family messaging advertising a broad 40% offer and a
  separate 50% dress offer, plus a cardmember incentive. A dress offer is not
  assigned to jeans.
- September 2025: an up-to-50% adult-style offer and a separate kids/baby offer.
- March 2026: Friends & Family messaging advertising 40%, with collaboration
  exclusions and separate cardmember/first-purchase incentives.

These establish the presence of messaging, not each product's eligibility or
price. They are not inputs to Discount Breadth or Median Discount Depth.

The April API has `categories[].ccList` references and `products[].styleColors`.
This shape was inspected before implementing the historical adapter. It differs
from the current response in its detailed marketing fields, personalization
fields, inventory values and absence of the current `metadata` object. The adapter
preserves historical flags rather than assuming current field names existed.
All 280 listed colors join to unique `(styleId, ccId)` records; there are 280 nested
colors and 93 styles. Its API total is 280 and pagination reports one page with a
requested size of 300. That supports completeness relative to this returned API
listing, not an independent census of all Gap jeans or stock.

## Historical price-basis validation

The alternative has unusually close archive provenance:

- Category HTML: **20250411132530**.
- Product API JSON: **20250411132536**, six seconds later.
- Referenced frontend bundle `96424.836baa.a046e.js`: **20250411132528**.

The archived bundle explicitly maps `effectivePrice` to `currentPrice` and
`regularPrice` to `regularPrice`. Its price-rendering component labels the latter
“Original price” with a line-through, and the former “Current price”; equal prices
are displayed as a single regular price. That is the same advertised/reference
price concept established for September 2026. This is static archived source-code
validation, not a claim that an archived browser successfully rendered every card
or that checkout prices were verified.

The dated, hash-checked review is saved in `docs/historical-price-basis.json`.
Historical metrics require that review; merely finding similarly named fields is
not enough. The historical parser keeps explicit product-color IDs and parent
style IDs. It does not copy the current assortment backward or apply promotional
percentages to effective prices.

April coverage and diagnostics:

| Validation | Result |
| --- | --- |
| Product-color observations / parent styles | 280 / 93 |
| Missing names | 0 / 280 |
| Missing original prices | 0 / 280 (0%) |
| Missing current prices | 0 / 280 (0%) |
| Missing product promotional text | 1 / 280 (0.36%) |
| Product parsing | Successful; all references joined and all price pairs validated |
| Price basis | Supported by archived frontend mapping and labels |

April alternative metrics, using existing definitions:

| Role | Measure | Value |
| --- | --- | --- |
| **Headline** | **Discount Breadth** | **81.07% (227/280)** |
| **Headline** | **Median Discount Depth among discounted observations** | **24.97%** |
| Diagnostic | Deep-Discount Share (≥30%) | 35.71% (100/280) |
| Diagnostic | Mean discount among discounted observations | 32.76% |
| Diagnostic | Band counts: 0%, >0–<20%, 20–<30%, 30–<40%, 40–<50%, ≥50% | 53, 0, 127, 1, 84, 15 |

The full normalized records and `metrics.json` are in
`data/processed/wayback/2025-03/`; the directory names the **requested target**,
while every observation and the metrics file identify the actual April date.
The other two periods have empty observation arrays plus explicit unsuccessful
product-extraction reports; no metrics files are emitted.

## Comparability assessment

| Question | Assessment |
| --- | --- |
| Historical original/reference price comparable to current `regularPrice`? | **Yes for the April alternative at the displayed-reference concept level**, based on archived code/labels. Neither proves a previously charged price. Unavailable for the September/March shells. |
| Historical current/sale price comparable to current `effectivePrice`? | **Yes for April as advertised current price**, before separately messaged conditional checkout/app/card offers. Not necessarily a permanent markdown or final paid price. Unavailable for the shells. |
| Same observation unit? | **Yes for April: identifiable product-color IDs plus parent styles**. Do not assume parent-style groupings remain stable over time. No identifiable product unit in the other pages. |
| Promotional messaging preserved? | **April: product-level raw/structured flags plus separate page evidence. Other periods: page evidence only.** Missing text remains unknown. |
| Defensible comparison with September 2026? | **Descriptive comparison of dated samples with explicit caveats is defensible; a like-for-like category trend is not established.** |

April uses a historical Certona/default ordering and requests 300 colors; current
collection uses constructorio/featured ordering and requests 200. Both report
personalized sorting. April returns 280 of a reported 280; the current sample has
188 listed colors out of 453, with the earlier browser/API 200-versus-188 discrepancy.
Assortment, color mix, style grouping, stock availability, ranking and promotion
eligibility can differ. There is no sales or inventory weighting. A change between
81.07% and 98.94% cannot therefore be attributed solely to promotional policy.
Nor can these captures substantiate a three-period time series: two requested
periods have no usable prices and the March alternative is dated April.

## Reproduction and tests

From the repository root, using the existing environment:

```sh
# Offline: preserve schema additions and reproduce the current metrics.
.venv/bin/python -m gap_tracker.parse data/raw/20260925T150058215580Z
.venv/bin/python -m gap_tracker.metrics data/processed/20260925T150058215580Z/observations.json

# Offline historical inspection, normalization, and approved price-basis metrics.
.venv/bin/python -m gap_tracker.parse_wayback 2025-03 --price-basis-review docs/historical-price-basis.json
.venv/bin/python -m gap_tracker.parse_wayback 2025-09
.venv/bin/python -m gap_tracker.parse_wayback 2026-03

# Resumable archive discovery/collection; requires network only for uncached requests.
.venv/bin/python -m gap_tracker.wayback 2025-03
.venv/bin/python -m gap_tracker.wayback 2025-09
.venv/bin/python -m gap_tracker.wayback 2026-03

.venv/bin/python -m unittest discover -s tests -v
```

The supporting frontend downloads and semantic review are retained audit evidence,
not a generic JavaScript crawler. They are used offline by the review gate. If a
future capture differs, a new evidence-backed review is required before metrics.
Raw/generated data remains Git-ignored and must accompany a transferred project
for offline reproduction.

Tests cover nullable evidence and raw code preservation, historical URL/filter
selection, nearest-date selection, archive-time verification, empty shells,
page-level offers, unsupported product structures, embedded template labels,
historical joins, missing/invalid prices, date provenance, price-basis review
hashes, and blocking unverified historical metrics. No Wayback requests are made
by unit tests. Streamlit remains unimplemented.

Validation completed: **34 tests passed**. All 280 historical normalized records
were reconciled to their archived JSON records. The 188 current observations
retain every pre-existing field value and metric value; original raw hashes
remain unchanged. A compact machine-readable result is saved at
`data/processed/wayback/summary.json`.
