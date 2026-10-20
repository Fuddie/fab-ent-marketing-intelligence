# Synthetic raw-data dictionary

Fab ENT is a fictional UK direct-to-consumer fashion brand. Every row is synthetic portfolio data, with no names, contact details, addresses or personal information. IDs are fabricated, stable identifiers, not anonymised real records.

## Reproduce and validate

From the repository root, run Python 3.10+ (standard library only):

```text
python scripts/generate_synthetic_data.py
python scripts/validate_raw_data.py
```

The generator overwrites only the seven `data/raw/*.csv` snapshots. Seed: `20250101`; fixed reporting period: 2025-01-01 through 2025-12-31. No wall clock, network, external package or machine timezone is used. CSVs use UTF-8, a header, LF newlines and deterministic row ordering. Reproduction is verified with SHA-256 per file; retain the Python version with audit results (initial verification: Python 3.14.4).

Money is GBP, represented as decimal strings with exactly two decimal places; generation uses integer pence and validation uses Decimal. Raw timestamps are second-precision ISO 8601 UTC ending in `Z`. Reporting dates and campaign date boundaries use Europe/London. For this fixed 2025 snapshot, scripts encode BST as 2025-03-30 01:00 UTC through, but excluding, 2025-10-26 01:00 UTC, avoiding an external timezone database dependency. Do not reuse that interval for other years.

Blank `web_sessions.customer_id` means anonymous/unmatched identity. Blank `campaign_id` means valid Direct or Organic traffic. All other fields are required. There are no broken foreign keys. IDs use zero-padded prefixes: CAM, SES, CUS, ORD, ITM and PRD. Text fields contain only synthetic product/campaign labels and classifications.

## Tables and columns

### campaigns — one row per campaign; PK campaign_id

| Column | Type | Meaning |
| --- | --- | --- |
| campaign_id | text | CAM-0001 format; canonical single-channel campaign key |
| campaign_name | text | Synthetic marketing label |
| channel | enum | Meta Paid Social, Google Paid Search, TikTok Paid Social |
| objective | enum | Sales, Traffic, Awareness |
| start_date, end_date | date | Inclusive London campaign dates, YYYY-MM-DD |
| budget_gbp | decimal(2) | Fixed lifetime campaign media budget; no revisions |

### ad_performance — one row per date × campaign × channel

Composite PK: `date, campaign_id, channel`. Exactly one row for every active campaign day.

| Column | Type | Meaning |
| --- | --- | --- |
| date | date | London platform reporting date |
| campaign_id | FK | campaigns.campaign_id |
| channel | enum | Must match campaign channel |
| spend_gbp | decimal(2) | Daily media spend; excludes fees, tax, credits and other costs |
| impressions | integer | Non-negative synthetic ad exposures |
| clicks | integer | Non-negative synthetic outbound ad clicks, comparable by design |

Clicks are not session records; no one-to-one click/session reconciliation is implied. Budgets are spent at 65%, 75%, 98% or 112%, with deterministic daily variation. First active days have zero clicks for safe-ratio cases.

### web_sessions — one row per session; PK session_id

| Column | Type | Meaning |
| --- | --- | --- |
| session_id | text | SES-000001 format; stable lexical tie-breaker |
| session_timestamp | UTC timestamp | Session start and attribution interaction time |
| customer_id | nullable FK | customers.customer_id when known |
| campaign_id | nullable FK | campaigns.campaign_id for paid visits only |
| channel | enum | Three paid channels above, Direct, Organic |
| source_medium | text | facebook / paid_social; google / cpc; tiktok / paid_social; (direct) / (none); google / organic, respectively |
| device | enum | mobile, desktop, tablet |

A session is a supplied synthetic visit; there is no event-level sessionisation, bot or internal traffic. All visits are valid website sessions. Only identified campaign-linked paid visits qualify as campaign attribution candidates. Organic has no campaign and therefore cannot claim a campaign or overwrite a paid touch. Direct and Organic remain visible in session reporting.

### customers — one row per synthetic customer; PK customer_id

| Column | Type | Meaning |
| --- | --- | --- |
| customer_id | text | CUS-000001 format; exact identity join, no fuzzy matching or merges |
| created_at | UTC timestamp | All synthetic accounts initialised at 2025-01-01T00:00:00Z |

Some customers never order. Order history covers only 2025; acquisition metrics can establish first observed purchase, not verified lifetime acquisition.

### orders — one row per order; PK order_id

| Column | Type | Meaning |
| --- | --- | --- |
| order_id | text | ORD-000001 format |
| order_timestamp | UTC timestamp | Purchase attempt time, including cancelled orders |
| customer_id | FK | customers.customer_id; every order identified |
| status | enum | completed, cancelled, partially_refunded, refunded |
| gross_order_amount_gbp | decimal(2) | Sum of gross line amounts, including cancelled attempts |
| refund_amount_gbp | decimal(2) | Sum of line refunds/cancellation reversals |
| net_order_amount_gbp | decimal(2) | Gross minus refunds/reversals |

Completed orders have zero refunds; partially refunded orders have positive refunds below gross; refunded and cancelled orders have full reversal and zero net. A cancelled reversal is bookkeeping for a voided synthetic amount, not evidence of money being collected or returned. Refunds are final snapshot adjustments associated with original order time; refund-event timestamps are unavailable. Gross is merchandise value; no shipping, tax, discounts, fees or FX are modelled. Eligibility for business order metrics remains a separate status policy, not inferred from raw storage.

### order_items — one row per order line; PK order_item_id

| Column | Type | Meaning |
| --- | --- | --- |
| order_item_id | text | ITM-000001 format |
| order_id | FK | orders.order_id |
| product_id | FK | products.product_id |
| quantity | integer | Positive units, 1–3 |
| unit_price_gbp | decimal(2) | Snapshot catalogue unit price |
| gross_line_amount_gbp | decimal(2) | Quantity × unit price |
| refund_amount_gbp | decimal(2) | Final line refund/reversal |
| net_line_amount_gbp | decimal(2) | Gross line minus refund |

All three amount totals reconcile exactly to their parent order. Orders have 1–4 lines, may repeat products, and can contain multiple products. Do not copy full order amounts or spend onto each product. Partial refunds are half of each line's value; no refund quantity is supplied.

### products — one row per product; PK product_id

| Column | Type | Meaning |
| --- | --- | --- |
| product_id | text | PRD-0001 format |
| product_name | text | Fictional style label |
| category | enum | Tops, Dresses, Denim, Outerwear, Accessories |
| unit_price_gbp | decimal(2) | Fixed synthetic catalogue price |
| currency | enum | GBP |

## Attribution fixtures and validation scope

The validator computes an independent diagnostic assignment across **all statuses**, not a published business metric: choose the maximum `(session_timestamp, session_id)` among identified campaign sessions with `order_time - 7 days <= session_time < order_time`. The lexically greatest session ID wins timestamp ties. No attribution column is stored in raw orders.

ORD-000001 through ORD-000012 use isolated CUS-000001 through CUS-000012. Random activity uses customers 31–1500, so fixtures cannot be contaminated.

| Order suffix | Case | Expected campaign |
| --- | --- | --- |
| 000001 | Two paid touches, then Direct | CAM-0002 |
| 000002 | Exactly seven elapsed days | CAM-0001 |
| 000003 | Seven days plus one second | Unattributed |
| 000004 | Touch at purchase and touch after purchase | Unattributed |
| 000005 | Equal paid timestamps; greater session ID wins | CAM-0002 |
| 000006 | Organic then Direct only | Unattributed |
| 000007 | Anonymous paid visit, no identity match | Unattributed |
| 000008 | January session, February order | CAM-0001 |
| 000009 | Paid visit then Organic | CAM-0001 |
| 000010 | Cancelled order with paid touch | CAM-0002 in diagnostic only |
| 000011 | Refunded order with paid touch | CAM-0002 in diagnostic only |
| 000012 | No visits | Unattributed |

CAM-0023 and CAM-0024 have spend but no website sessions or attributed orders. Repeat customers, multi-product orders and equal-valued orders occur in the random population. Validation checks file/column presence, nonempty unique keys, foreign keys, dates, classifications, money precision, non-negative media measures, line arithmetic, order reconciliation, statuses, fixture outcomes and shapes, repeat buying and budget cases. It prints counts, date ranges, channels, statuses and monetary totals. Failures exit nonzero.

## Limitations

This is an engineered test population, not a calibrated UK fashion forecast. Costs, traffic, click counts and purchases are not a causal funnel or platform exports. There is no pre-2025 identity/order/interaction history or post-2025 conversion tail; cross-year lookback and lifetime acquisition cannot be validated from this snapshot. January orders begin on 11 January to avoid silently truncating their seven-day windows. Cross-month attribution is covered; missing timestamp/broken-reference and ingestion-lag scenarios are deliberately absent. There are no real people, event logs, consent records, VAT, fulfilment, stock, payment charges, marketing incrementality or profit measures. Do not interpret raw gross/net totals as accounting revenue. No dbt models are included.
