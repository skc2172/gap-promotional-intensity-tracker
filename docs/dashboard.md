# Gap pricing-discipline monitor

From the repository directory:

```sh
.venv/bin/python -m streamlit run app.py
```

Open the localhost URL printed by Streamlit (normally http://localhost:8501).
The existing virtual environment includes Streamlit, pandas and Altair. A minimal
fresh environment needs `requests streamlit pandas altair`. Keep the local data/
directory: it contains Git-ignored saved research evidence and processed outputs.

## Research workflow

1. **Signal:** latest saved current snapshot for the focus category. Discount
   Breadth and Median Discount Depth are primary; Deep-Discount Share is a
   supporting diagnostic. Category collection timestamps and scope are explicit.
   There is no pooled/composite promotional score.
2. **Trend:** select categories, date range, coverage regimes, and a metric.
   Charts use isolated dated points, without lines, interpolation, or change
   arrows. Exact UTC observation times and scope remain available in the table.
3. **Category:** compare the latest saved current metrics and sample sizes for
   selected categories. This view deliberately retains latest observations even
   when the trend date filter is narrowed; its caption identifies that scope.
4. **Evidence:** independently choose a snapshot for the focus category, inspect
   discount bands and coverage, search product names/colors/IDs, filter discounted
   rows, download visible rows as CSV, and inspect original normalized provenance.
   Evidence filters do not change snapshot KPIs.

Color is a read-only presentation enrichment from the saved raw ccName field,
resolved through each row's raw file/pointer after verifying the evidence hash.
It is blank if unavailable or unverifiable. Neither the normalized schema nor
pricing/promotion logic was changed. Reference prices are retailer references,
not verified previous transaction prices. Checkout/app offers remain text only.

## Explicit refresh

Only **Refresh Current Data** invokes collection. It launches the existing
`gap_tracker.current` module using the same Python environment and project working
directory, with a newly timestamped batch manifest. That pipeline collects all
reported pages for all four categories, preserves raw evidence, validates,
normalizes, and writes the existing metrics. The dashboard then reloads saved
outputs. Prior snapshots are not overwritten.

The refresh runs synchronously with a visible spinner. Its batch path and
per-category status are available under Refresh details. If a category fails,
successful categories are available and existing prior snapshots remain visible;
latest category timestamps make a mixed-date refresh visible. Error responses
and incomplete manifests remain preserved by the pipeline. Do not describe a
partial refresh as fully current. Simply loading, changing filters, or inspecting
evidence never starts collection. No background schedule was added.

The presentation loader validates each metrics file's observation hash and skips
invalid snapshots with a visible warning. It excludes schema-v1 backup copies
from history. It reads files on each interaction, so newly generated CLI outputs
also appear on the next interaction. It does not recalculate or redefine KPIs.

## Historical limits

The time view now loads 25 selected backfill snapshots plus the original April
2025 archive observation, across all four categories. Archived API samples and
current all-reported-page snapshots are visible by default as isolated dated
points with different source labels. First-page current samples remain optional.
The actual capture date is always used. Missing periods are never zero-filled,
interpolated, or connected with continuous lines.

Backfill price concepts are transferred from the directly verified April 2025
archived frontend through a matching legacy API field contract. This is a
schema-based comparability inference, not a separate rendered-price audit for
every date. Historical samples are single archived responses with differing
assortment, ranking and coverage; they are not a matched panel or directly
interchangeable with current standardized all-page collections. See
[the full dated inventory and limitations](historical-backfill.md).

Historical backfill is a separate CLI workflow. Refresh Current Data continues
to invoke only the existing live four-category pipeline.

## Validation

The full suite has 48 passing tests, including dashboard read-only interactions,
category and historical filters, explicit refresh dispatch, success/failure UI,
metrics-hash rejection, source color enrichment, and unique refresh batch paths.
UI tests use Streamlit AppTest. Refresh network calls are mocked in the suite;
a separate live refresh adapter smoke test exercises the existing pipeline.
Saved-data integration/UI tests skip if the ignored local dataset is absent.
The app was also launched on localhost and opened in the in-app browser.

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Live refresh smoke test on September 25, 2026: three categories completed;
Women's T-Shirts & Tanks failed the existing missing-source-record validation
for style 898923 / color 898923032. The failed raw response remains saved and
its prior valid snapshot remains the latest eligible one. No parser rules were
relaxed. Batch: data/processed/runs/20260925T223351513191Z-dashboard.json.

## Research UI refinement

The monitor is now titled **GAP / PROMOTIONAL INTENSITY MONITOR** and opens with
all four categories' latest valid measures rather than a single focus category.
Each category shows its collection time; no pooled or composite score is added.
Metric definitions is a collapsed plain-English guide to breadth, depth, deep-discount share and the product/color unit. No investment hypothesis is embedded in the dashboard. Ranked category bars compare each measure independently.

The longitudinal view selects the latest observation per UTC calendar day,
category and coverage regime. This is a presentation selection, not averaging
or a change to calculations. Intraday snapshots remain accessible in the evidence
selector and on disk. The UI explicitly flags when only one current day exists;
no intraday trend or persistence claim is inferred. Archived and first-page
samples remain separately marked and optional, with no connecting lines.

Research tables use one-decimal percentages and two-decimal USD prices.
Technical identifiers, full timestamps and detailed validation remain in Data
Coverage / Methodology / Provenance; the main evidence table emphasizes product,
color, prices, discount, promotional text and product link. CSV export retains
identifiers for reconciliation. Refresh remains an explicit action only.

Refinement validation: 49 tests pass, including daily selection across categories
and coverage regimes without mutating or deleting intraday inputs. Existing
read-only interaction and refresh-dispatch tests pass; no live collection was
needed for this presentation-only refinement.

### Local development: stale helper import

If a running server reports `cannot import name 'daily_snapshots'`, first confirm
that the helper imports in a fresh process:

```sh
.venv/bin/python -c 'from gap_tracker.dashboard_data import daily_snapshots; print(daily_snapshots)'
```

The helper is defined in dashboard_data.py and the app's import matches it.
A previously running Streamlit process can retain the older imported module after
source edits. Stop that server with Ctrl+C in its terminal, then restart using the
launch command above. A browser reload alone does not restart the Python process.
The September 25 local failure was resolved by restarting the pre-refinement
server; the revised UI and validated pipeline were retained. All 49 tests passed.

Backfill integration validation: the full suite now passes 54 tests. All 26
selected historical observations are available in the time view and evidence
selector, with actual dates and distinct archive sample labels. The local server
was restarted and the chart was checked in the browser across 2023–2026.

## Final information hierarchy

The subtitle is “Monitor GAP's promotional intensity across categories and over
time.” Each of the four sections opens with its research purpose. The investment
context section has been removed. Near the current picture, Metric definitions
explains each measure and why colors are measured separately.

The primary time-view controls concern category, metric and date. Detailed source
filters, daily selection rules and historical comparability are under the collapsed
Methodology & Data Quality expander. Chart labels use Current, Historical,
Historical (initial study), and Current (partial sample); the underlying source
classes and point-only presentation are unchanged. A visible caution still states
that historical and current samples are not directly comparable.

Underlying evidence retains its snapshot selector, distribution, filters, prices,
messages, product links and CSV download. Raw identifiers, hashes, local paths,
JSON pointers and detailed validation objects are retained in Technical Provenance.
Refresh behavior and all stored data and calculations are unchanged. The full
54-test suite passes after this copy/hierarchy pass.

## Restrained presentation (September 26)

The dashboard now summarizes historical limitations in four statements: variable
archived coverage, no continuously matched product panel, no interpolation, and
price-field coverage rather than full-assortment coverage. Observation tables and
detailed recovery explanations are no longer rendered. The dated inventory remains
in historical-backfill.md and the saved processed snapshots. The UTC-day selection,
API-sample limitations and April 2025 validation basis documented above still apply.
The original March 2025 discovery target yielded April 11, 2025 evidence; the initial
September 2025 and March 2026 searches yielded no usable pricing. Those searches and
raw evidence remain preserved, independently of the subsequent broader backfill.

Both archived source classes display as Historical. Both are archived product/color
pricing samples subject to the same broad limitations; this display grouping does
not assert identical coverage or independent rendered validation for every date.
Original scopes, review records and daily selection remain unchanged. The source
filter selects both archive classes together; current partial samples remain
optional and visibly distinguished.

Technical Provenance now shows only source, observation time, unit, price basis,
collection coverage/page count and price coverage. Full JSON, hashes, pointers,
versions and paths remain in saved files rather than the UI. Refresh and invalid
snapshot notices avoid rendering raw errors or local paths. CSV evidence export
and stored observations are unchanged.

Latest failed women's tees run: 20260926T180551097120Z-dashboard. The response listed
style 896816 / color 896816062 without a source product-color record on any collected
page. Normalization rejected the incomplete source; the Sep 25 valid snapshot
remains current. No parser rules were relaxed or dates relabeled.

## Portable submission bundle

The Git allowlist includes the 47 validated snapshots exposed by the finished
monitor: 21 current observations (including optional first-page samples and
intraday evidence) and 26 selected historical observations. Each includes metrics,
observations and validation JSON, matching raw product-response evidence, and
current manifests. Working captures, discovery caches, run logs and backups stay
ignored. The explicit allowlist means future refreshes remain local unless
intentionally added to the submission bundle.

Validation raw_snapshot paths in this bundle are repository-relative. The loader
resolves those against the repository root; older absolute metadata falls back to
the mirrored data/raw snapshot directory, never the original machine's path.
Observation and metrics bytes, source URLs, hashes and archive timestamps remain
unchanged. Historical discovery references in validation may refer to unbundled
working evidence; they are retained for provenance and not needed by the dashboard.

Verification copied only allowlisted data into an independent temporary directory:
all 47 snapshots loaded with identical metrics, observations and color enrichment.
The dashboard loaded through Streamlit AppTest against that relocated data without
collection. Only dashboard/data-loading tests were run for this packaging change.
