# Pricing semantics validation — 25 September 2026

The defensible measurement is **displayed-price discount intensity relative to
Gap's reference price, for the observed product-color sample**. The arithmetic is
validated. It does not isolate permanent markdowns, clearance, event-only price
reductions, or the final price after conditional offers.

## Evidence and scope

- Original snapshot: `data/raw/20260925T150058215580Z/`, product response collected
  at 2026-09-25 15:00:59 UTC. Both raw response hashes still match the manifest.
- All 188 normalized price pairs and calculated discounts reconcile to their
  original JSON pointers. Existing collection, normalization, schema, and metrics
  definitions were not changed.
- Eight representative product pages were inspected through their rendered buy
  boxes on 25 September 2026. Product name, selected color, displayed price(s), and
  product marketing message matched the saved observations. These are later live
  corroboration, not retroactive proof of the original checkout experience.
- `data/validation/pricing-semantics-20260925/trace.json` preserves the selected
  normalized rows, raw field excerpts, parent fields, and live-check notes.
  It is an analysis artifact, not a replacement raw response.
- A public frontend asset retrieved during the original investigation has been
  preserved alongside the trace, with URL and hash in `frontend-provenance.json`.
  It maps `effectivePrice` to `currentPrice` directly. The original category
  checks also showed accessibility labels “Original price” and “Current price.”
- No cart, checkout, app, membership, or payment offer was exercised. We did not
  establish event terms or product-by-product eligibility from an offer contract.

## What the fields support

| Source field | Supported interpretation | Limits |
| --- | --- | --- |
| `regularPrice` | Retailer reference/original price used for the displayed price comparison; normalized as `original_price`. | Not proof of MSRP, a previously paid price, or a pre-event selling price. No price history is present. |
| `effectivePrice` | Advertised current product-color price; frontend mapping is `currentPrice:Number(e.effectivePrice)`, and checked product pages display this value. | It is not uniformly a clearance price or a final payable price. No decomposition into base selling price and event adjustment is supplied. |
| `percentageOff` | Source's whole-number discount indicator, consistent with the price-pair reduction rounded to the nearest integer for all 186 discounted observations. Empty for both full-price observations. | Do not substitute it for exact calculations or band membership; this sample does not establish a universal rounding rule for all Gap data. |
| `priceType` | Codes `P` (184 observations), `M` (2), `R` (2). R coincides with equal prices; M with the two sale/checkout-offer examples; P spans roughly 21%, 51%, and 71% reductions. | P plausibly denotes promotional pricing and M markdown pricing, but the exact business definitions are not documented by this response. Do not treat those expansions as an established taxonomy. |
| `ccLevelMarketingFlags` | Product-color messaging records, including content, position, and type. The displayed messages match selected flags in the eight checks. | They are not a machine-readable discount formula or proof of offer eligibility. Their `type="REGULAR"` is not evidence of regular/full pricing: it appears on all the selected offers. |
| `excludedFromPromotion` | Parent-style source field, the string `"false"` for all 64 styles. | Conflicts with explicit exclusion text on both full-price collaboration products. Cannot reliably determine eligibility; preserve the conflict. Do not apply Python truthiness to this string. |
| `styleMarketingFlags` | Parent-style messages, empty on all 64 styles here. | Empty does not prove no promotions. Color-level messages are populated. |
| `ccLevelBadges` | Separate merchandising labels such as New, Best seller, Selling fast, and Now on Sale. | Most are not pricing evidence. `NEW_TO_SALE` / Now on Sale specifically corroborates the sale status of 842628002, without proving permanence. |
| `defaultSizeVariantId`, `ccId`, `styleId`, `mergeType`, `experience` | Identity and merchandising context, separate from price. | Parent styles can group differently named color records. Do not assume `styleId` equals the product number shown on every PDP or use `experience="REGULAR"` as a pricing classification. |

The saved frontend additionally has a conditional visual-style rule: R and P use
`text-color-type-copy`, while M uses `text-color-type-sale`. This supports a
presentation distinction between P and M; it does not define the commercial
reason for a price change or prove a permanent markdown.

The complete color-record key inventory contains no separate pre-event selling
price, checkout-adjusted price, explicit coupon amount, or offer effective-date
field. That absence limits what this response alone can establish.

## Representative traces

In every row below, normalization copies `regularPrice → original_price` and
`effectivePrice → current_price`; the calculated percentage is
`100 × (regularPrice − effectivePrice) / regularPrice`. The marketing column
remains independent. All eight current PDP checks matched the saved price(s),
selected color, name, and message. Dollar values are USD.

| Product-color ID and product | Regular → effective | Calculated % | Source % / type | Separate marketing text |
| --- | --- | --- | --- | --- |
| [902738012 — Victoria Beckham Straight Jeans](https://www.gap.com/browse/product.do?pid=902738012), dark rinse wash | 118.00 → 118.00 | 0.0000 | empty / R | Excluded from promotions |
| [1185301002 — Stride Wide-Leg Jeans](https://www.gap.com/browse/product.do?pid=1185301002), dark tint wash | 89.95 → 71.00 | 21.0673 | 21 / P | Extra 10% off in the app |
| [1194450002 — Mid Rise Culotte Jeans](https://www.gap.com/browse/product.do?pid=1194450002), dark wash | 79.95 → 63.00 | 21.2008 | 21 / P | 50% off + extra 10% in the app |
| [842628002 — Lace-Up ’90s Loose Jeans](https://www.gap.com/browse/product.do?pid=842628002), medium washed indigo | 99.95 → 54.99 | 44.9825 | 45 / M | Extra 50% off at checkout |
| [747627002 — Khaki Stripe Barrel Jeans](https://www.gap.com/browse/product.do?pid=747627002), khaki stripe | 99.95 → 49.99 | 49.9850 | 50 / M | Extra 50% off at checkout |
| [911424002 — Low Slung Extra Baggy Jeans](https://www.gap.com/browse/product.do?pid=911424002), terra brown | 89.95 → 44.00 | 51.0839 | 51 / P | 50% off + extra 10% in the app |
| [827104002 — Curvy Long & Lean Jeans](https://www.gap.com/browse/product.do?pid=827104002), dark indigo | 89.95 → 26.00 | 71.0951 | 71 / P | 60% off: limited time |
| [832586002 — Pleated Baggy Jeans](https://www.gap.com/browse/product.do?pid=832586002), dark indigo | 89.95 → 26.00 | 71.0951 | 71 / P | 60% off: limited time |

Exact raw locations in `products.json` (the trace retains full normalized rows):

| Product-color ID | Parent style ID | JSON pointer |
| --- | --- | --- |
| 902738012 | 902738 | `/products/5/styleColors/0` |
| 1185301002 | 406647 | `/products/45/styleColors/15` |
| 1194450002 | 1194450 | `/products/36/styleColors/0` |
| 842628002 | 815642 | `/products/13/styleColors/13` |
| 747627002 | 485013 | `/products/9/styleColors/2` |
| 911424002 | 682958 | `/products/10/styleColors/1` |
| 827104002 | 827106 | `/products/21/styleColors/1` |
| 832586002 | 832586 | `/products/1/styleColors/0` |

## Why the high values need careful interpretation

The source grouping explains the 159 observations at ≥50% without any inferred
coupon calculations:

- 144 P observations have approximately 51% calculated reductions and messaging
  referring to 50% plus an app offer.
- 15 P observations have approximately 71% calculated reductions and 60%
  limited-time messaging.
- The remaining 25 P observations have approximately 21% calculated reductions:
  24 advertise the app offer; the Culotte example also advertises 50%.
- The two M observations have 44.9825% and 49.9850% calculated reductions and
  advertise an additional checkout offer. The latter rounds to source value 50,
  but correctly stays outside the calculated ≥50% band.
- Two R observations are full-price and display exclusions.

The saved HTML and the current site advertise a Fall Style Event at 50%, including
sale, with exclusions. This is contextual evidence of a broad event, not evidence
that every effective price is generated by applying exactly 50% to regularPrice.
The 71%/60% and 21%/50% examples demonstrate the absence of a uniform relationship
between the numeric pair and the marketing percentage.

For the M examples, the page displays the saved effective price and separately
advertises an extra reduction at checkout. This supports calling the field a
pre-checkout displayed price for those examples. It does not establish the final
payable amount or eligibility. We do not halve those prices in the dataset.
Likewise, the app offer is not applied to browser prices in the analysis.

No evidence identifies whether mismatched messages reflect a different base,
stacking, stale content, offer eligibility, or another mechanism. None is assumed.
The high aggregate discounts are supported by displayed prices, but cannot be
interpreted as proof that nearly all inventory is on clearance or that margins
have fallen proportionately. Observations are not sales-, inventory-, or revenue-
weighted, and reference prices are not a transaction-history baseline.

## Recommended terminology and unresolved questions

Use **displayed-price discount intensity versus retailer reference price** for
this metrics series. “Promotional intensity” can remain the project umbrella,
with separate numeric-price and messaging measures. “Markdown intensity” alone
could incorrectly suggest permanent product markdowns: 184 of the 186 discounted
observations carry P rather than M, and event context is prominent.

Still unresolved: the exact P/M business taxonomy; event-versus-product discount
attribution; whether reference prices were previously charged; offer stacking,
eligibility, and checkout outcomes; message/flag contradictions; size-dependent
prices beyond the checked default selections; and browser/API coverage differences.
The existing 188-versus-200 discrepancy and personalization caveat remain relevant.
A single snapshot cannot establish duration or whether a reduction is temporary.

## Advisable schema additions before historical work (not implemented)

Retain the existing price fields and calculated definitions. Add a small set of
nullable evidence/context fields in a versioned extension or companion table:

1. `source_price_type` and `source_percentage_off`, preserving their raw values.
   They allow source classifications and rounded figures to be audited separately
   from calculated discounts; unknown historical values remain null.
2. Structured promotion evidence with scope (`product_color`, `style`, `page`),
   raw flag content/type/position, badges, and the raw exclusion field. Keep a
   disagreement indicator rather than resolving the exclusion contradiction.
3. `price_basis` such as `displayed_current_vs_reference`, with source-specific
   field mappings. Avoid assigning `clearance`, `event_adjusted`, or
   `checkout_final` unless directly supported by evidence.
4. Explicit `snapshot_id`/evidence reference and full observed timestamp at the
   row or linked-snapshot level. For Wayback, distinguish archive capture time,
   retrieval time, and the site's claimed dates. Preserve market, currency,
   channel, and known selected variant; unknown context must stay unknown.

Keep `product_id` (ccId) and `style_id` separate, document the parent grouping,
and retain the raw pointer. Current provenance already supports these additions
without recollecting the saved snapshot. Archived HTML may expose fewer fields;
comparable arithmetic requires comparable price meaning, not merely matching
column names. No concrete price-mapping or arithmetic error was found, so no
collection/parser/metrics change was made.
