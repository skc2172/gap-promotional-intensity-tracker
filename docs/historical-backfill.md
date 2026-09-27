# Historical backfill: recoverable evidence and comparability

API discovery searched both known public product endpoints without date bounds and without time collapsing. The saved CDX responses contain 64 legacy-API records (14 Women’s Jeans, 15 Women’s T-Shirts & Tanks, 19 Men’s Jeans, 16 Men’s T-Shirts); all four current-endpoint queries returned no captures. None of these indices hit the 10,000-record limit. This is coverage of the queried URL families, not proof of exhaustive coverage of every historical Gap system.

**25 new selected historical snapshots**, plus the retained April 11, 2025 proof-of-concept snapshot, feed the dashboard. All 26 selected samples have both prices on every normalized observation. Prices are from the archived response only.

| Category | Selected snapshots | First actual capture | Last actual capture | Product-color sample range |
|---|---:|---|---|---:|
| Men / Jeans | 8 | 2023-08-17 | 2026-02-19 | 84–135 |
| Men / T-Shirts | 5 | 2024-02-10 | 2026-08-03 | 153–232 |
| Women / Jeans | 6 | 2024-02-14 | 2026-08-22 | 176–280 |
| Women / T-Shirts & Tanks | 7 | 2023-07-16 | 2026-08-23 | 200–300 |

## Actual recoverable observations

All rows below use archived category API JSON (`regularPrice` / `effectivePrice`), one archived response per snapshot. Price coverage is the share with both price fields, not assortment coverage. Shares use all normalized product-colors. Median depth uses discounted observations only. API total is metadata rather than an independently verified population.

| Capture date | Category | Product-colors | Styles | API total | Price coverage | Breadth | Median depth | ≥30% share |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2023-07-16 | Women / T-Shirts & Tanks | 289 | 80 | 1331 | 100% | 67.13% | 31.60% | 35.29% |
| 2023-08-15 | Women / T-Shirts & Tanks | 300 | 117 | 456 | 100% | 36.67% | 33.26% | 22.67% |
| 2023-08-17 | Men / Jeans | 135 | 125 | 135 | 100% | 54.81% | 56.68% | 39.26% |
| 2023-10-16 | Men / Jeans | 98 | 93 | 98 | 100% | 95.92% | 41.21% | 65.31% |
| 2023-11-20 | Men / Jeans | 84 | 35 | 85 | 100% | 94.05% | 49.98% | 50.00% |
| 2024-01-15 | Women / T-Shirts & Tanks | 300 | 107 | 374 | 100% | 94.00% | 41.94% | 54.33% |
| 2024-02-10 | Men / T-Shirts | 188 | 99 | 188 | 100% | 59.57% | 32.42% | 33.51% |
| 2024-02-14 | Women / Jeans | 176 | 116 | 177 | 100% | 85.23% | 31.21% | 44.32% |
| 2024-03-23 | Women / T-Shirts & Tanks | 300 | 106 | 335 | 100% | 91.67% | 33.22% | 62.33% |
| 2024-04-05 | Men / Jeans | 96 | 40 | 96 | 100% | 85.42% | 41.39% | 62.50% |
| 2024-04-21 | Women / T-Shirts & Tanks | 221 | 62 | 224 | 100% | 86.43% | 33.22% | 60.18% |
| 2024-05-14 | Men / Jeans | 91 | 40 | 91 | 100% | 26.37% | 24.97% | 10.99% |
| 2024-09-16 | Men / Jeans | 99 | 40 | 109 | 100% | 83.84% | 41.21% | 48.48% |
| 2024-10-01 | Women / Jeans | 179 | 85 | 179 | 100% | 94.41% | 51.22% | 75.42% |
| 2025-02-04 | Men / Jeans | 124 | 55 | 143 | 100% | 100.00% | 26.20% | 45.97% |
| 2025-04-11 | Women / Jeans | 280 | 93 | 280 | 100% | 81.07% | 24.97% | 35.71% |
| 2025-07-15 | Women / Jeans | 240 | 57 | 374 | 100% | 99.58% | 40.82% | 50.83% |
| 2026-01-28 | Women / Jeans | 196 | 37 | 401 | 100% | 88.27% | 49.98% | 52.55% |
| 2026-02-19 | Men / Jeans | 109 | 42 | 109 | 100% | 94.50% | 31.21% | 52.29% |
| 2026-04-02 | Men / T-Shirts | 232 | 119 | 287 | 100% | 60.34% | 33.28% | 30.60% |
| 2026-06-25 | Men / T-Shirts | 186 | 83 | 191 | 100% | 69.89% | 50.00% | 55.38% |
| 2026-07-05 | Men / T-Shirts | 173 | 82 | 177 | 100% | 73.41% | 43.89% | 54.34% |
| 2026-07-05 | Women / T-Shirts & Tanks | 200 | 69 | 403 | 100% | 83.50% | 23.21% | 19.50% |
| 2026-08-03 | Men / T-Shirts | 153 | 77 | 162 | 100% | 76.47% | 42.43% | 52.94% |
| 2026-08-22 | Women / Jeans | 200 | 68 | 456 | 100% | 76.50% | 51.08% | 76.00% |
| 2026-08-23 | Women / T-Shirts & Tanks | 200 | 68 | 452 | 100% | 62.50% | 43.24% | 50.50% |

## Selection and rejected evidence

One representative per category/month is chosen by highest paired-price coverage, then largest observation count, then earliest capture timestamp. Discount magnitude and promotional text do not determine selection. Identical archive digests and consecutive identical observed price/assortment states are redundant. This creates a monthly-sampled research history, not a record of every promotion event. Exact capture dates remain unchanged.

Seven API replay requests returned redirects to later captures rather than their indexed capture dates. Those were not followed or relabeled as older observations. The later valid bodies are already represented. Twenty-two requests were excluded for filters, sorting, nonzero page numbers or other nonstandard request context. Three otherwise verified bodies failed the strict duplicate product-color identity check. Six valid bodies were not selected under the monthly representative rule. Every candidate and reason appears in the machine-readable audit.

Older category HTML discovery uses canonical legacy URLs across all indexed years and modern category paths. Annual representatives inspect structural eras, not every archived page. Some old pages expose style prices, price ranges or promotional text, but no validated color-specific reference/current-price mapping was recovered by this adapter. These are not converted into full-price rows, imputed prices or zero-discount periods. Replay failures and unsupported HTML structures are distinguished in `html-audit.json`. Older HTML remains a coverage limitation; it is not evidence that historical products had no discounts.

## Price-basis review: explicit inference and limits

The April 2025 POC directly verified an archived frontend mapping from effectivePrice to displayed current price and regularPrice to displayed original price. The new captured JSON responses use the same legacy `/cc` endpoint and color-level field contract, with explicit US market/locale and category identities. Every published body passes the existing numeric and identity validation. Source-reported percentage-off values were cross-checked against the price arithmetic; no checked pair differed by more than one percentage point. The source-reported percentages do not determine any metric.

**Transfer of displayed-price semantics across dates is a schema/contract-based inference**, not independent rendered-page confirmation for every capture. Additional archived frontend retrieval was attempted, but incomplete asset recovery did not establish a separate per-date rendering audit. The inference, capture hash, original URL, baseline archived mapping evidence, and limitations are explicit in `docs/backfill-price-reviews.json` and each snapshot’s validation file. This supports a qualified history of observed reference/current-price gaps; it does not establish final checkout savings, permanent markdowns, promotional causes or margin outcomes.

Historic samples differ in page size, ranking vendor, inventory and assortment. Parent style grouping changes across source eras, so style counts are identifiers observed at that date, not a stable matched-style panel. Product-color prices are not sales-weighted. Current all-page observations and archived single-response samples must not be treated as fully interchangeable. Missing months are neither zero values nor interpolated values.

## Reproduce and inspect

```sh
.venv/bin/python -m gap_tracker.backfill --collect --html
# Inspect any newly recovered evidence and add capture/hash-bound price-basis reviews before publication.
.venv/bin/python -m gap_tracker.backfill_publish
.venv/bin/python -m gap_tracker.backfill_report
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m streamlit run app.py
```

Discovery and replay bodies are cached under `data/raw/backfill-discovery/` and `data/raw/wayback/`. Each processed historical snapshot has observations.json/CSV, metrics.json, and validation.json under `data/processed/wayback/<capture timestamp>-<category>/`. The POC stays in its original folder. `data/processed/backfill/summary.json` inventories new selections; `audit.json` records all 64 API candidates; `html-audit.json` records inspected HTML. Data remains local and Git-ignored.

Backfill never calls live Gap or executes archived scripts. Replay timestamps require matching Memento headers. An ordinary curl transport fallback is used only after connection failures; HTTP denials are not retried or bypassed. Prior failed-request metadata is retained. Price-basis publication is fail-closed unless a capture-specific hash/URL review exists. Successful inputs can be reparsed offline. Re-running selection preserves prior files while marking superseded representatives as unselected for the dashboard.

## Dashboard integration

The time view includes archived API samples and the retained archive alternative as discrete, source-labeled points alongside current all-reported-page samples. There are no connecting lines or interpolation. Category, date and scope filters still apply; every dated historical point is available in the evidence selector. Historical availability text is data-driven across all four categories. The comparability inference remains explicit in the historical context and provenance views. Refresh Current Data is unchanged and never runs backfill.

## Verification

All 4,849 normalized historical product-color rows (including the retained POC)
were independently reconciled to their hashed raw files and JSON pointers; both
prices and color identities match. Recalculation through the unchanged metrics
module exactly reproduces all saved metric fields. The full 54-test suite passes,
including source/category filters, monthly selection, capture-bound review hashes,
actual archive dates, the transport denial guard and dashboard interactions.
The Streamlit server was restarted and the rendered Change Over Time view was
verified with the historical points present. Current collection and metric code
were not changed, and dashboard validation did not trigger a live refresh.

## Discovery index coverage

| Category key | Canonical legacy index records | Modern-path index records | Indexed HTML date span |
|---|---:|---:|---|
| men-jeans | 180 | 197 | 20060316–20260923 |
| men-tshirts | 174 | 179 | 20060316–20260923 |
| women-jeans | 186 | 268 | 20060316–20260822 |
| women-tshirts-tanks | 185 | 162 | 20061021–20260827 |

HTML indices are monthly-collapsed discovery inventories including URL variants and filtered URLs; they are not counts of usable research snapshots. Unfiltered annual representatives are inspected separately. The initial legacy-prefix query hit its cap and was replaced by canonical legacy URL discovery plus modern category paths. Neither final index family hit its configured cap.

## Completed HTML inspection pass

| Category | Annual representatives attempted | Verified replay bodies | Unverified / unavailable |
|---|---:|---:|---:|
| men-jeans | 21 | 20 | 1 |
| men-tshirts | 21 | 17 | 4 |
| women-jeans | 21 | 17 | 4 |
| women-tshirts-tanks | 21 | 21 | 0 |

All 84 annual representatives are logged. No older HTML observation was published: the adapter did not establish a trustworthy product-color reference/current price pairing from these page structures. This is an explicit parser/coverage limitation, not a claim that all older pages lack any prices. Replay failures and unsupported structures remain available for future targeted research.
