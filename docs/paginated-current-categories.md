# Paginated current snapshots — September 25, 2026

All API-reported pages were collected through the existing public endpoint at
approximately 22:22 UTC. Earlier snapshots and historical work remain intact.

| Category | API total, first → last page | Collected colors | Styles | Pages | Both prices | Discount Breadth | Median Discount Depth | Deep-Discount Share ≥30% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Women's Jeans | 455 → 456 | 378 | 103 | 3 | 100% | 99.47% | 51.08% | 73.81% |
| Women's T-Shirts & Tanks | 503 → 504 | 495 | 113 | 3 | 100% | 90.91% | 51.36% | 56.57% |
| Men's Jeans | 103 | 100 | 27 | 1 | 100% | 99.00% | 51.22% | 71.00% |
| Men's T-Shirts | 260 | 252 | 87 | 2 | 100% | 63.89% | 51.36% | 39.29% |

## Remaining discrepancies

- Women's Jeans lists 190, 180, and 10 unique product-colors on its three pages.
  Two repeated identities across pages are removed: 378 distinct observations.
  This is 77 below the first total (78 below the final total).
- Women's T-Shirts & Tanks lists 199, 197, and 100; one repeated identity is
  removed. The 495 observations are 8 below the first total (9 below the last).
- Men's Jeans lists 100 on its only reported page, 3 below its total of 103.
- Men's T-Shirts lists 195 and 58; one repeated identity is removed. The 252
  observations are 8 below its total of 260.

The counts are the union of category ccList identities, not all nested swatches.
Causes of the remaining gaps are not established. The small changes in women's
API totals show that these sequential requests do not represent an atomic,
frozen inventory snapshot. All responses retain the same personalized-response
setting. Completing reported pagination does not establish complete category
coverage. No additional guessed pages, unlisted swatches, or fabricated products
were added to force agreement.

Missing product promotional text: 2/378 Women's Jeans, 10/495 Women's T-Shirts &
Tanks, 1/100 Men's Jeans, and 91/252 Men's T-Shirts. Missing messages remain
unknown. All names and both prices are present. Prices retain the previously
validated displayed-current versus retailer-reference basis. Promotional text
and priceType codes remain separate source evidence; calculations are unchanged.

## Implementation and evidence

The collector reads zero-based currentPage and pageNumberTotal from page zero,
then requests every remaining reported page with the same category, department,
page size, locale, and anonymous parameters. Page zero retains products.json;
later responses use products-page-1.json, products-page-2.json, etc. Each response
has its own URL, collection time, headers, status, byte count, and SHA-256 hash in
the manifest. HTTP errors, unexpected page numbers, or changing page counts stop
the collection with an incomplete manifest; raw responses are still preserved.
A 100-page sanity bound fails visibly rather than silently truncating collection.

The offline parser verifies every raw hash, normalizes each page separately, and
unions (style_id, product_id). Identical repeated observations keep the earliest
row, with additional source locations and evidence metadata in
provenance.additional_occurrences. Different normalized values for a repeated
identity fail parsing for investigation rather than arbitrarily choosing prices.
The flat normalized schema, price formulas, metrics, and product-color unit stay
unchanged. Raw pointers refer to the actual originating page file. Legacy
single-page snapshots remain parseable without recollection.

All 1,225 observations were reconciled to their saved raw price records and
promotion flags. Normalized membership equals the union of listed identities
across all pages, without duplicates. Four duplicate occurrences were removed.
Validation files preserve individual page counts, totals, duplicate details,
first-total shortfall, and a flag for totals changing during collection.

The full offline suite passes **43 tests**. New pagination cases check requested
page numbers, cross-page deduplication and provenance, conflicting duplicates,
wrong returned pages, changed page counts, and later-page HTTP failure
preservation without retries. Existing pricing, category, and historical tests
remain in the suite.

## Reproduce

```sh
# A fresh dated batch of all four categories, with all reported pages:
.venv/bin/python -m gap_tracker.current
# Reparse this saved batch offline, without recollecting:
.venv/bin/python -m gap_tracker.current --batch data/processed/runs/paginated-four-categories-20260925.json
.venv/bin/python -m unittest discover -s tests -v
```

Exact raw and processed paths are recorded in
`data/processed/runs/paginated-four-categories-20260925.json`.
A consolidated reconciliation and metric summary is saved at
`data/processed/runs/paginated-four-categories-20260925-validation.json`.
All raw and generated data remain Git-ignored and retained locally.

Use these as expanded-sample snapshots, not directly interchangeable with the
previous first-page samples: additional product coverage changes their weights
and measured discount shares. Breadth and Median Depth remain the headline
measures, with Deep-Discount Share and other retained calculations as diagnostics.
