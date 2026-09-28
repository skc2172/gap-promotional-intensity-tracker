# Update Historical Archive

The sidebar's collapsed archive workflow accepts a start/end date and runs only
when its button is pressed. Refresh Current Data remains independent. The CLI is:

```sh
.venv/bin/python -m gap_tracker.historical_update --start 2026-01-01 --end 2026-08-31
```

The workflow reuses the existing CDX API discovery (both endpoint eras), request
eligibility checks, archived replay transport/timestamp verification, historical
normalizer, capture-bound price-basis review and deterministic metrics. It does
not request live Gap data. Unsupported HTML-only archive captures cannot currently
supply validated product/color prices through this workflow.

## Publication gates

A capture must have a matching source URL, timestamp and SHA-256 price-basis review
in docs/backfill-price-reviews.json, with hash-verified supporting evidence. This is
the existing manual research gate, not an automatic inference from field names.
Previously unreviewed captures are retained as pending_price_basis_review; the
button cannot autonomously publish entirely new capture dates until their evidence
has been reviewed. Add evidence-backed reviews through the existing research
process, then rerun the period. Do not manufacture reviews or relax the gate.
Fresh clones also need any supporting review evidence not in the curated dashboard
bundle before a reviewed capture can be published. Missing files fail closed.

The parser must resolve every listed product/color, and every normalized observation
must have both prices. Invalid/incomplete responses are rejected in their entirety;
no partial rows are published. Existing single-response archive coverage limitations
still apply: complete price evidence within the response is not full assortment
coverage or complete historical pagination.

## Append-only selection and audit

Existing historical category/timestamp identities are skipped before replay. Monthly
slots already represented are retained; remaining candidates use the existing
coverage/sample-size/earliest-timestamp representative rule. Exact observed price
states already represented for that category are omitted. No existing raw or
processed directory is replaced, including current snapshots. A pre-existing
unpublished directory is preserved and requires manual inspection rather than
being overwritten automatically.

Each invocation has an isolated data/raw/archive-updates run directory containing
CDX responses, replay evidence, request metadata, selection logs and audit.json.
Published snapshots go into data/processed/wayback, with raw evidence under
 data/raw/wayback. Processing is staged outside the loader's search tree and the
complete processed directory is published only after metric validation. Failed
staging/raw remnants never become valid analytical snapshots.

The dashboard reloads validated outputs after an explicit update. Its existing
As-of resolver sees added snapshots without special Wayback date logic. Actual
capture dates and classifications remain unchanged. New files remain ignored by
the curated Git allowlist until intentionally selected for submission.

Archive/network failures may leave categories uncovered; capped discovery indices
are logged as potentially truncated. No daily coverage or complete archive search
is promised. Updates are synchronous and broad ranges may take time. A failed or
empty update retains all existing observations. Detailed diagnostics stay on disk.

## CDX failure handling

Discovery marks non-200 responses and malformed/non-record JSON as unusable, while
preserving the exact response and HTTP metadata. Candidate collection skips those
indices instead of trying to decode an error page as captures. Other usable indices
can still be processed. An unusable or truncated index makes the search incomplete.
The dashboard reports “Archive search could not be completed” even when another
category added observations; only a completed empty search uses the no-new-valid-
observations message. This does not change archive eligibility or pricing validation.
