# Fab ENT business metric contract

## Adopted Phase 4 governance (supersedes earlier unresolved/provisional policies below)

These are adopted business definitions for the fixed synthetic snapshot, distinct from source facts. Earlier sections remain the design history; where they leave these questions open, this section governs Phase 4.

- **Placed orders / attempts:** every order once, all four statuses: `count(distinct order_id)`.
- **Commercial eligibility:** `status in ('completed', 'partially_refunded') and net_order_amount_gbp > 0`. Cancelled, fully refunded and zero/negative-net orders do not count as conversions. Preserve their amounts and flag negative inputs rather than clamping them.
- **Attributed orders:** commercially eligible orders with `attribution_status = 'attributed' and campaign_id is not null`. Separately expose `attributed_placed_orders` across all statuses. Attribution rate is attributed eligible orders / all eligible orders. Campaign rows necessarily have 100% when they have eligible orders; only the overview measures overall coverage.
- **Gross merchandise revenue:** `sum(gross_order_amount_gbp) filter (where status in ('completed','partially_refunded','refunded'))`. This includes subsequently refunded sales and excludes cancelled attempts; it is not accounting revenue.
- **Sales refunds:** `sum(refund_amount_gbp) filter (where status in ('completed','partially_refunded','refunded'))`. **Cancellation reversals:** `sum(refund_amount_gbp) filter (where status = 'cancelled')`. Never label the combined source adjustment as customer refunds.
- **Net merchandise revenue:** `sum(net_order_amount_gbp) filter (where status in ('completed','partially_refunded','refunded'))`, including zero and unexpected signed values. Reconcile `raw_gross_order_amount_gbp - cancellation_gross_amount_gbp = gross_merchandise_revenue_gbp`; `gross_merchandise_revenue_gbp - sales_refunds_gbp = net_revenue_gbp`; and `raw_gross_order_amount_gbp - sales_refunds_gbp - cancellation_reversals_gbp = raw_net_order_amount_gbp`. Cancellation gross equals reversals in this source; test that invariant. Do not subtract refunds again from source net.
- **First observed acquisition:** select eligible orders over all available history, then `row_number() over (partition by customer_id order by order_timestamp, order_id) = 1`. Rank UTC instants, use ascending lexical order_id for ties, then filter reporting periods. Use the chosen order's attribution, without seeking a later paid order for an unattributed customer. Publish `first_observed_acquisitions`, `attributed_first_observed_acquisitions`, and `unattributed_first_observed_acquisitions`, with `acquisition_basis = 'first_observed_2025_snapshot'`. This is not verified lifetime acquisition.
- **CAC:** period platform media spend / period paid-attributed first observed acquisitions, at matching campaign/channel scope. Overview uses all paid spend / all paid-attributed acquisitions, not all acquisitions. Direct, Organic and Unattributed have no cost coverage and CAC is NULL. This is media-only period CAC, not fully loaded or spend-cohort CAC.
- **Conversion rate:** attributed eligible orders / all valid campaign-classified sessions for campaigns/paid channels (including anonymous sessions). Overall website numerator includes both attributed and unattributed eligible orders, denominator includes all valid sessions. Direct/Organic/Unattributed channel order-to-session rates are NULL: unmatched orders cannot be assigned to Direct or Organic. Use purchase-period numerator and session-start-period denominator; not a unique-session conversion probability and may exceed 100%.
- **Other ratios:** CTR = clicks / impressions * 100; CPC = spend / clicks; gross ROAS = attributed gross merchandise revenue / media spend; net ROAS = attributed net merchandise revenue / media spend. Overview ROAS also uses attributed revenue only; total website revenue stays separately visible. ROAS is a multiple, CPC/CAC are GBP, conversion/CTR/attribution/budget utilisation/pacing are percentages. Every zero or missing denominator returns NULL; zero numerator with positive denominator returns zero. Never average ratios.
- **Dates:** convert event instants with `cast(timezone('Europe/London', event_timestamp) as date)` before day/month assignment. Ad dates and campaign bounds are already London dates. Attribution remains the existing 168 elapsed UTC-hour rule. No operator-local timezone inference.
- **Snapshot timing:** adjustments restate original order periods; eligible conversion and acquisition histories are recomputed from the current final-status snapshot on full refresh. No refund-event or cash-flow reporting is possible. No pre-2025 history or post-2025 conversion tail exists.
- **Budgets:** campaign summary compares full observed spend to its single lifetime budget (counted once). Campaign daily exposes cumulative spend / lifetime budget as utilisation; straight-line expected cumulative spend is budget * inclusive elapsed active days / inclusive lifetime days, clamped to [0, lifetime days]. Pacing is cumulative spend / expected cumulative spend. Channel/month and overview allocate lifetime budget evenly across active calendar days, then sum each day's allocated budget once. Their utilisation and pacing both mean monthly spend / allocated monthly budget; explicitly not an approved monthly budget. Do not sum daily repeated lifetime budgets. Summary pacing equals lifetime utilisation at the snapshot's completed campaign horizon.
- **Flags:** spend-without-eligible-attributed-orders means period spend > 0 and attributed eligible orders = 0 (not proof of waste). Overspend means utilisation > 100%; ahead-of-budget-pacing means pacing > 100%; approaching-budget means utilisation >= 90% and <= 100%. Thresholds are adopted monitoring conventions, not statistical alerts. Negative-input flags combine signed media, budget, session validity inputs where numeric, order and line amounts/quantities; no clamping. Incomplete attribution means unattributed placed orders > 0 within the row's scope; campaign scopes cannot contain unattributed orders, so false there does not establish global completeness. Channel cost coverage is explicit; zero recorded paid spend is not imputed unpaid-channel cost coverage.
- **Fact aggregation and coverage:** aggregate media, sessions, orders, acquisitions and allocated budgets separately at date/campaign/channel before joining their union of keys. Preserve spend-only and outcome-only rows, every campaign, valid Direct/Organic sessions, and a distinct Unattributed outcome channel. Channel rows include paid, Direct, Organic and Unattributed; do not infer a traffic channel for unmatched orders. Monthly overview exposes attributed/unattributed order, acquisition and monetary components. Months cover observed source activity and campaign budget dates; the fixed snapshot covers all twelve months. Missing feed coverage cannot be inferred from zero activity; these marts assume the validated complete fixed snapshot.

Fixed-snapshot acceptance: spend GBP 189,198.54; raw gross order/line value GBP 416,314.00; governed gross merchandise revenue GBP 396,434.00; sales refunds GBP 43,076.50; cancellation reversals GBP 19,880.00; net revenue GBP 353,357.50; placed orders 2,500; eligible conversions 2,228 (1,439 attributed, 789 unattributed).

Authority: `PROJECT_BRIEF.md`. Confirmed rules are stated directly. **Decision required** marks unresolved business policy; **Assumption to validate** marks proposed implementation. Physical mappings for the fixed synthetic source are confirmed in `DATA_DICTIONARY.md`; remaining business policies are still marked below.

**Provisional project decision** marks the agreed portfolio implementation policy, subject to later revision; source availability and physical mappings are separately established by the synthetic dictionary.

## 1. Table grain and expected primary key

Existing grains are preserved. The synthetic generator and raw validator confirm these keys and relationships; see `DATA_DICTIONARY.md` for physical column names.

| Table | Confirmed grain | Expected primary key (logical) |
| --- | --- | --- |
| campaigns | One row per marketing campaign | Campaign identifier |
| ad_performance | One row per date, campaign and channel | Date + campaign identifier + channel |
| web_sessions | One row per website session | Session identifier |
| customers | One row per customer | Customer identifier |
| orders | One row per order | Order identifier |
| products | One row per product | Product identifier |
| order_items | One row per order line | Order-line identifier |

**Synthetic source confirmed:** stable prefixed canonical IDs; exact customer_id matching; one paid channel per campaign. order_items bridges orders and products at line grain; orders can contain multiple products.

## Metric conventions

For sections 2–14, **Assumption to validate:** support daily and selected-period reporting by campaign/channel where the source permits. Use ad reporting date for spend/clicks/impressions, session start for sessions, purchase time for orders, and first qualifying purchase time for new customers. Attribution may connect purchases to interactions outside the selected period.

“Eligible orders” means orders under the unresolved status policy in section 17. Aggregate numerator and denominator separately at matching scope before dividing; never average row-level ratios. Source measure availability and mappings are documented for the synthetic snapshot; business policy and model validation remain required before publication.

## 2. Spend

- **Business meaning:** recorded marketing cost for the activity period.
- **Formula:** sum recorded spend once per ad_performance row.
- **Source grain:** date × campaign × channel in ad_performance.
- **Reporting grain:** date/period × campaign and/or channel; overall total.
- **Exclusions/safeguards:** never sum spend after joining individual sessions/orders. **Synthetic source confirmed:** GBP platform media spend only; fees, taxes, credits and email costs are absent. Missing cost coverage is unknown, not zero.

## 3. Impressions and clicks

- **Business meaning:** recorded ad exposures and clicks, respectively.
- **Formula:** sum impressions; sum clicks, once per source row.
- **Source grain:** **Assumption to validate:** measures available at ad_performance grain.
- **Reporting grain:** date/period × campaign and/or channel; overall total.
- **Exclusions/safeguards:** **Synthetic source confirmed:** comparable synthetic outbound clicks and ad exposures; no email. Do not substitute email opens for impressions or mix incompatible click types. Preserve missing values as unknown.

## 4. CTR

- **Business meaning:** recorded clicks as a share of recorded impressions.
- **Formula:** total clicks / total impressions × 100%.
- **Source grain:** ad_performance aggregates.
- **Reporting grain:** matching period and campaign/channel scope for both components.
- **Exclusions/safeguards:** zero impressions gives an undefined ratio. Require comparable click/impression definitions; do not average daily or platform CTRs.

## 5. CPC

- **Business meaning:** recorded cost per recorded click.
- **Formula:** total spend / total clicks.
- **Source grain:** ad_performance aggregates.
- **Reporting grain:** period × campaign and/or channel; overall total.
- **Exclusions/safeguards:** zero clicks gives an undefined ratio. Match cost and click coverage, dates and channel scope; disclose incomplete costs.

## 6. Attributed orders

- **Business meaning:** eligible orders assigned to a marketing campaign.
- **Formula:** count unique eligible order identifiers with one assigned campaign.
- **Source grain:** orders with at most one attribution assignment per order.
- **Reporting grain:** purchase date/period × assigned campaign/channel.
- **Exclusions/safeguards:** exclude unattributed orders from campaign counts but retain them separately. Count orders, not units, products or customers; never assign an order twice.

## 7. Attributed order amount / revenue

- **Business meaning:** recorded value of eligible orders connected to campaigns. This is attributed order amount, not net revenue or causal incremental revenue.
- **Formula:** sum each attributed eligible order's recorded amount once.
- **Source grain:** orders with one attribution assignment per order.
- **Reporting grain:** purchase date/period × assigned campaign/channel.
- **Exclusions/safeguards:** the brief says this amount does not account for every refund, cancellation, fee, tax or business cost. **Decision required:** exact amount field and inclusions; apply section 17 consistently. Flag missing amounts rather than silently replacing them with zero.

## 8. ROAS

- **Business meaning:** attributed order amount per unit of recorded spend; not profit or proof of causation.
- **Formula:** attributed order amount / spend, displayed as a multiple.
- **Source grain:** independently aggregated attribution/orders and ad_performance.
- **Reporting grain:** period × campaign/channel; overall total.
- **Exclusions/safeguards:** zero spend gives an undefined ratio; match currency and scope. **Assumption to validate:** compare purchases in the period with spend in the period. This is period-based ROAS, not return on a spend cohort; earlier interactions may contribute orders.

## 9. Website sessions

- **Business meaning:** recorded website visits, not unique visitors.
- **Formula:** count unique session identifiers.
- **Source grain:** web_sessions, one row per session.
- **Reporting grain:** session-start date/period; campaign/channel where session classification exists.
- **Exclusions/safeguards:** **Synthetic source confirmed:** each supplied row is one valid website session, with no bot/internal traffic; paid campaign classification and campaignless Direct/Organic are explicit. Keep direct and unknown traffic visible. Order attribution must not duplicate or reclassify sessions.

## 10. Conversion rate

- **Business meaning:** **Provisional project decision:** attributed eligible orders per eligible classified website session at the same campaign/channel reporting scope; an order-to-session rate.
- **Formula:** attributed eligible orders / eligible classified website sessions × 100%.
- **Source grain:** separate order-attribution and session aggregates.
- **Reporting grain:** matching period × campaign/channel; purchase dates for numerator and session-start dates for denominator under the proposed convention.
- **Exclusions/safeguards:** **Provisional project decision:** exclude unattributed orders from campaign/channel numerators. Cross-period purchases, multiple orders per session and non-website interactions can distort this rate or make it exceed 100%; suppress misleading comparisons with mismatched coverage. Zero/missing denominators follow section 17. **Synthetic source confirmed:** all supplied sessions are valid; paid campaign/channel classification is explicit. **Decision required:** numerator scope for any overall rate.

## 11. New customers

- **Business meaning:** **Provisional project decision:** customers identified by their first eligible order across all available history.
- **Formula:** count unique customers whose earliest eligible order falls in the period.
- **Source grain:** customers linked to order history; one acquisition record per customer.
- **Reporting grain:** first-purchase date/period; acquisition campaign/channel from that order's attribution.
- **Exclusions/safeguards:** later purchases do not create new customers; retain unattributed acquisitions. **Decision required:** qualifying status, guest/merged identity handling, historical coverage and simultaneous first-order tie-breaking. Incomplete history supports “first observed,” not confirmed new.

## 12. Customer acquisition cost by channel

- **Business meaning:** **Provisional project decision:** period channel spend per new customer acquired in that period and attributed through their first eligible order.
- **Formula:** period channel spend / new customers acquired in that period and assigned to that channel.
- **Source grain:** separate ad_performance and customer-acquisition aggregates.
- **Reporting grain:** period × acquisition channel; campaign where supported.
- **Exclusions/safeguards:** zero/missing denominators follow section 17. **Provisional project decision:** cohort CAC is a future enhancement. **Decision required:** included costs and source coverage. Exclude returning customers; do not assign unattributed customers to paid channels or call this fully loaded CAC without complete costs.

## 13. Campaign budget utilisation

- **Business meaning:** proportion of an approved campaign budget consumed.
- **Formula:** spend within budget scope and dates / approved budget × 100%.
- **Source grain:** ad_performance plus **Synthetic source confirmed:** campaigns supplies amount, GBP currency, inclusive dates and lifetime grain, without revisions. The synthetic source confirms campaigns.budget_gbp as a fixed lifetime GBP budget over inclusive start_date/end_date, without revisions.
- **Reporting grain:** campaign × applicable budget period; channel only with channel-allocated budgets.
- **Exclusions/safeguards:** match dates/currency; never repeat a budget per daily row. Zero/missing budget gives an undefined ratio. **Synthetic source confirmed:** lifetime budgets. **Decision required:** approaching-budget threshold and alert criteria.

## 14. Campaigns spending without attributed orders

- **Business meaning:** campaigns with spend but no attributed eligible orders in the evaluated period.
- **Formula:** flag campaign when spend > 0 and attributed order count = 0; count flagged campaign identifiers for summary.
- **Source grain:** independently aggregated spend and attribution joined to campaigns.
- **Reporting grain:** campaign × period; channel summary requires validated campaign/channel mapping.
- **Exclusions/safeguards:** missing order aggregates become zero only after feed completeness is verified. **Assumption to validate:** period-based monitoring, not mature spend-cohort performance. Recent interactions may still convert within seven days. **Decision required:** minimum spend, waiting period and alert thresholds; flag ingestion gaps and immature windows. This flag alone does not prove waste.

## 15. Attribution eligibility, tie-breaking and unattributed orders

**Confirmed:** each order is assigned to the customer's most recent non-direct campaign interaction within the seven days before purchase. An order can be attributed to only one campaign. If no qualifying interaction exists, the order remains unattributed. Attribution establishes sequence, not causation.

**Assumption to validate:** derive one assignment record per order, including unmatched orders, using customer identity, interaction time and campaign identity. web_sessions may supply interactions, but the brief does not establish all sessions as eligible or all interactions as website sessions. Evaluate candidates before applying report-period filters, including the seven-day lookback before the period starts. A later direct interaction does not overwrite an earlier qualifying non-direct interaction.

**Provisional project decisions:**

- Include interactions from exactly seven elapsed days before purchase; exclude interactions at or after purchase: purchase time minus seven elapsed 24-hour days <= interaction time < purchase time, after time normalization.
- Rank eligible interactions by latest interaction timestamp, then stable session identifier as the deterministic tie-breaker. Do not split an order across campaigns. **Synthetic source confirmed:** session_id is the key and lexically greatest ID wins; only website-session interactions are supplied.
- Missing campaign, interaction timestamp or usable identity information leaves an order unattributed; do not infer a match.
- Use full refreshes for late-arriving data in this portfolio implementation, recomputing attribution and dependent metrics from available history.

**Synthetic source confirmed:** identified campaign-linked paid web_sessions are the only campaign interactions; customer_id joins exactly, timestamps have second precision, and campaigns each have one channel. Direct and Organic have no campaign. See section 19.

Retain orders with no qualifying interaction or required matching information as unattributed. **Assumption to validate:** record reason flags for missing data and unresolved source issues within the unattributed bucket; never drop orders or manufacture assignments. Eligible order counts and amounts must reconcile to attributed plus unattributed totals without overlap.

## 16. Safe join rules

Daily campaign spend could be repeated once for every matching order or customer interaction. Preserve spend at date × campaign × channel while assigning each order only to its most recent eligible non-direct interaction within seven days.

- Aggregate spend, sessions, orders and acquisitions independently to the requested common reporting grain, then join on all grain keys. Never join raw fact tables and sum their measures afterward.
- Reduce attribution candidates to at most one assignment per order before joining amounts. Distinct order counts cannot fix duplicated spend/amount sums. SUM(DISTINCT amount) is unsafe because different orders can have identical values.
- Join dimensions only on validated unique keys. Check row counts and sums before/after joins; expose unmatched keys rather than silently losing them through inner joins.
- Include date and channel when joining daily campaign aggregates. Do not repeat a measure without channel detail across channels. Retain spend-only, session-only and order-only groups.
- **Synthetic source confirmed:** order_items provides the order/product bridge at line grain with reconciled amounts. **Decision required:** spend/session allocation rules before product reporting; never copy full order amounts or campaign spend to every product.
- Aggregate budgets at their approved grain. Customer/order/product filters require an explicit spend/session allocation policy before publishing corresponding ratios.

## 17. Common handling rules

- **Division by zero — Provisional project decision:** zero or missing denominators return NULL, displayed as N/A; never infinity. A known zero numerator with positive denominator returns zero. Missing components stay unknown.
- **Negative values — Provisional project decision:** preserve negative raw values and flag them for investigation; do not silently clamp, replace or discard them. **Decision required:** source-specific interpretation of credits, reversals and corrections.
- **Nulls — Assumption to validate:** expose missing-value counts; default absent aggregates to zero only when coverage proves no activity. Do not fabricate required keys or timestamps.
- **Currency — Decision required:** source/report currencies, conversion rate source/date and rounding. Until resolved, report currencies separately; do not sum mixed currencies or divide incompatible currency bases. Retain precision and round for display.
- **Timezone — Decision required:** business reporting timezone, source timezone interpretation, daylight-saving policy and daily ad-date alignment. Normalize timestamps before attribution. Do not infer business timezone from the operator's location; date-only data cannot be precisely shifted without supporting detail.
- **Cancelled orders — Decision required:** eligible statuses and whether cancellation restates prior periods. Apply one policy to counts, amounts, conversion and first-purchase calculations. No exclusion is confirmed by the brief.
- **Refunds — Decision required:** gross/adjusted recorded amount, full/partial refunds, timing and restatements. Do not invent refund fields or deductions. Separately name and reconcile any future net-revenue metric; the confirmed measure is attributed recorded order amount.

## 18. Required data-quality and reconciliation tests

These are acceptance requirements; implementation depends on validated mappings and the decisions above.

1. **Keys/grains:** non-null unique expected keys for all seven tables, including the full ad_performance composite key; detect duplicates and orphan references where relationships exist.
2. **Validity/coverage:** profile missing measures, timestamps, identities and currencies; verify date coverage and ingestion freshness by channel. Assert negative raw values are preserved and flagged. **Decision required:** source-specific credit/reversal interpretation and completeness thresholds. Do not impose unsupported bounds such as clicks always <= impressions.
3. **Attribution:** at most one campaign per order; verify identity, non-direct eligibility and absence of a more recent qualifying interaction. Assert inclusion at exactly seven elapsed days before purchase and exclusion at/after purchase. Cover direct-after-non-direct, no match, equal timestamps and cross-period lookback; verify the stable session-identifier tie-breaker and that missing campaign, interaction time or usable identity leaves the order unattributed.
4. **Conservation:** eligible order counts and amounts equal attributed plus unattributed totals for identical filters/currencies. Campaign/channel subtotals must not count any order twice.
5. **Join safety:** compare spend, sessions, order counts and amounts before/after joins. Include multiple daily ad rows, sessions and orders per campaign, equal-valued orders and multi-product orders; measures remain invariant at intended scope.
6. **Dashboard reconciliation:** independent SQL must match dashboard totals and campaign/channel results for spend, impressions, clicks, sessions, orders, amounts, new customers and every ratio. Calculate ratios from totals; assert NULL displayed as N/A for zero/missing denominators. Verify campaign/channel conversion excludes unattributed orders and uses eligible classified sessions at matching scope; test missing costs and spend without orders.
7. **Acquisition/budgets:** each customer acquired at most once using available full history and approved ties; reconcile attributed/unattributed acquisitions. Validate budget scope, effective dates and currency; ensure daily joins do not multiply budgets.
8. **Policy/reproducibility:** test approved timezone boundaries, currency conversion, cancellations and refunds. Verify full refreshes incorporate late-arriving data into attribution, first eligible orders and dependent metrics, and repeated refreshes on unchanged input produce identical results. Verify initial CAC uses period spend and customers acquired in that period. Record source mappings, decision versions, SQL, filters and refresh time for reproduction. Verify all six brief business questions and consistent, read-only Wren answers against these definitions.

## 19. Confirmed synthetic source design

This is fixed synthetic portfolio data for a fictional UK DTC fashion brand, not real customer data. `DATA_DICTIONARY.md` is the physical source specification; the reproducible generator and validator live in `scripts/`. The following resolves source-dependent questions above for this snapshot only; unresolved business decisions remain open.

- **Coverage and currency:** 2025-01-01 through 2025-12-31; GBP only, exact pence, no FX. Media spend includes platform media cost only, excluding fees, taxes and credits. Synthetic impressions and outbound clicks are comparable by construction; no email campaigns or costs exist.
- **Time:** raw timestamps are UTC to the second. Reporting timezone and daily ad dates are Europe/London, including BST. Seven-day windows use elapsed UTC time. No pre-2025 or post-2025 records exist; cross-month lookback is tested, cross-year coverage is unavailable.
- **Sessions and attribution:** web_sessions is the sole interaction source. Identified paid sessions with valid campaign_id qualify; campaignless Direct and Organic visits do not claim a campaign. Every supplied session is valid, with no bots/internal traffic or event-level sessionisation. Stable session_id is the physical tie-breaker; sort descending after timestamp, taking the lexically greatest ID. Order/customer joins use exact customer_id. Blank session customer_id means anonymous and cannot match; blank campaign_id is valid for Direct/Organic. All order identities are known; no guests or merged IDs are modelled.
- **Amounts and status:** orders.gross_order_amount_gbp is the available gross merchandise order value; orders.refund_amount_gbp includes cancellation reversals; orders.net_order_amount_gbp equals gross minus those adjustments. Each reconciles to corresponding order_items amounts. Statuses are completed, cancelled, partially_refunded and refunded. Adjustments are final snapshot amounts at original order grain; refund event time is unavailable. Shipping, VAT, discounts, fees and business costs are absent. Choosing eligible statuses and gross versus adjusted attributed amount remains a business decision; raw net is not automatically the contracted attributed amount.
- **Budgets:** campaigns.budget_gbp is a single lifetime media budget per single-channel campaign, bounded by inclusive campaign dates, with no revisions. Approaching-budget thresholds and alert policies remain open.
- **Customers:** only 2025 history is available; acquisition must be labelled first observed, not verified lifetime new. The first-eligible-order policy and simultaneous-order tie-breaking remain open.
- **Validation scope:** the raw validator checks the seven source grains, references, date/channel alignment, monetary arithmetic and deterministic attribution fixtures. Its assignment diagnostic includes all statuses to test interaction matching, and is not a business attribution model or dashboard metric. Raw spend is non-negative by design; credit/reversal anomaly preservation is a future source concern. SQL/dbt, dashboard reconciliation, missing-feed tests and broader policy tests in section 18 remain future work.
