# Fab ENT business metric contract

Authority: `PROJECT_BRIEF.md`. Confirmed rules are stated directly. **Decision required** marks unresolved business policy; **Assumption to validate** marks proposed implementation. Logical field descriptions below are not confirmed source column names.

**Provisional project decision** marks the agreed portfolio implementation policy, subject to later revision; it does not confirm source availability or physical mappings.

## 1. Table grain and expected primary key

Existing grains are preserved. **Assumption to validate:** these logical keys identify rows uniquely; physical columns and relationship mappings require source validation.

| Table | Confirmed grain | Expected primary key (logical) |
| --- | --- | --- |
| campaigns | One row per marketing campaign | Campaign identifier |
| ad_performance | One row per date, campaign and channel | Date + campaign identifier + channel |
| web_sessions | One row per website session | Session identifier |
| customers | One row per customer | Customer identifier |
| orders | One row per order | Order identifier |
| products | One row per product | Product identifier |

**Decision required:** canonical identifiers across platforms, customer identity matching between sessions and orders, and whether campaigns span channels. Product/order relationships are not established; do not assume one product per order.

## Metric conventions

For sections 2–14, **Assumption to validate:** support daily and selected-period reporting by campaign/channel where the source permits. Use ad reporting date for spend/clicks/impressions, session start for sessions, purchase time for orders, and first qualifying purchase time for new customers. Attribution may connect purchases to interactions outside the selected period.

“Eligible orders” means orders under the unresolved status policy in section 17. Aggregate numerator and denominator separately at matching scope before dividing; never average row-level ratios. Source measure availability and mappings require validation before publication.

## 2. Spend

- **Business meaning:** recorded marketing cost for the activity period.
- **Formula:** sum recorded spend once per ad_performance row.
- **Source grain:** date × campaign × channel in ad_performance.
- **Reporting grain:** date/period × campaign and/or channel; overall total.
- **Exclusions/safeguards:** never sum spend after joining individual sessions/orders. **Decision required:** included costs, email costs, fees, taxes, credits and currency. Missing cost coverage is unknown, not zero.

## 3. Impressions and clicks

- **Business meaning:** recorded ad exposures and clicks, respectively.
- **Formula:** sum impressions; sum clicks, once per source row.
- **Source grain:** **Assumption to validate:** measures available at ad_performance grain.
- **Reporting grain:** date/period × campaign and/or channel; overall total.
- **Exclusions/safeguards:** **Decision required:** comparable platform click definitions and treatment of email. Do not substitute email opens for impressions or mix incompatible click types. Preserve missing values as unknown.

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
- **Exclusions/safeguards:** exclude unattributed orders from campaign counts but retain them separately. Count orders, not tickets, products or customers; never assign an order twice.

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
- **Exclusions/safeguards:** **Decision required:** bot/internal-traffic filters, session boundaries and campaign/channel classification. Keep direct and unknown traffic visible. Order attribution must not duplicate or reclassify sessions.

## 10. Conversion rate

- **Business meaning:** **Provisional project decision:** attributed eligible orders per eligible classified website session at the same campaign/channel reporting scope; an order-to-session rate.
- **Formula:** attributed eligible orders / eligible classified website sessions × 100%.
- **Source grain:** separate order-attribution and session aggregates.
- **Reporting grain:** matching period × campaign/channel; purchase dates for numerator and session-start dates for denominator under the proposed convention.
- **Exclusions/safeguards:** **Provisional project decision:** exclude unattributed orders from campaign/channel numerators. Cross-period purchases, multiple orders per session and non-website interactions can distort this rate or make it exceed 100%; suppress misleading comparisons with mismatched coverage. Zero/missing denominators follow section 17. **Decision required:** source-dependent session eligibility/classification and the numerator scope for any overall rate.

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
- **Source grain:** ad_performance plus **Decision required:** budget source, amount, currency, dates, revisions and grain. No budget column is confirmed.
- **Reporting grain:** campaign × applicable budget period; channel only with channel-allocated budgets.
- **Exclusions/safeguards:** match dates/currency; never repeat a budget per daily row. Zero/missing budget gives an undefined ratio. **Decision required:** lifetime versus periodic budgets, approaching-budget threshold and alert criteria.

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
- Rank eligible interactions by latest interaction timestamp, then stable session identifier as the deterministic tie-breaker. Do not split an order across campaigns. **Decision required:** physical session-key mapping and stable identifier ordering; eligible non-session interactions require a validated session-key mapping before this rule can be implemented for them.
- Missing campaign, interaction timestamp or usable identity information leaves an order unattributed; do not infer a match.
- Use full refreshes for late-arriving data in this portfolio implementation, recomputing attribution and dependent metrics from available history.

**Decision required before implementation:** interaction sources/types, non-direct classification, customer identity matching, valid campaign linkage, timestamp precision, campaign/channel structure and channel assignment for multi-channel campaigns.

Retain orders with no qualifying interaction or required matching information as unattributed. **Assumption to validate:** record reason flags for missing data and unresolved source issues within the unattributed bucket; never drop orders or manufacture assignments. Eligible order counts and amounts must reconcile to attributed plus unattributed totals without overlap.

## 16. Safe join rules

Daily campaign spend could be repeated once for every matching order or customer interaction. Preserve spend at date × campaign × channel while assigning each order only to its most recent eligible non-direct interaction within seven days.

- Aggregate spend, sessions, orders and acquisitions independently to the requested common reporting grain, then join on all grain keys. Never join raw fact tables and sum their measures afterward.
- Reduce attribution candidates to at most one assignment per order before joining amounts. Distinct order counts cannot fix duplicated spend/amount sums. SUM(DISTINCT amount) is unsafe because different orders can have identical values.
- Join dimensions only on validated unique keys. Check row counts and sums before/after joins; expose unmatched keys rather than silently losing them through inner joins.
- Include date and channel when joining daily campaign aggregates. Do not repeat a measure without channel detail across channels. Retain spend-only, session-only and order-only groups.
- **Decision required:** product/order bridge or line-item grain and allocation rules before product reporting; never copy full order amounts or campaign spend to every product.
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

1. **Keys/grains:** non-null unique expected keys for all six tables, including the full ad_performance composite key; detect duplicates and orphan references where relationships exist.
2. **Validity/coverage:** profile missing measures, timestamps, identities and currencies; verify date coverage and ingestion freshness by channel. Assert negative raw values are preserved and flagged. **Decision required:** source-specific credit/reversal interpretation and completeness thresholds. Do not impose unsupported bounds such as clicks always <= impressions.
3. **Attribution:** at most one campaign per order; verify identity, non-direct eligibility and absence of a more recent qualifying interaction. Assert inclusion at exactly seven elapsed days before purchase and exclusion at/after purchase. Cover direct-after-non-direct, no match, equal timestamps and cross-period lookback; verify the stable session-identifier tie-breaker and that missing campaign, interaction time or usable identity leaves the order unattributed.
4. **Conservation:** eligible order counts and amounts equal attributed plus unattributed totals for identical filters/currencies. Campaign/channel subtotals must not count any order twice.
5. **Join safety:** compare spend, sessions, order counts and amounts before/after joins. Include multiple daily ad rows, sessions and orders per campaign, equal-valued orders and multi-product orders; measures remain invariant at intended scope.
6. **Dashboard reconciliation:** independent SQL must match dashboard totals and campaign/channel results for spend, impressions, clicks, sessions, orders, amounts, new customers and every ratio. Calculate ratios from totals; assert NULL displayed as N/A for zero/missing denominators. Verify campaign/channel conversion excludes unattributed orders and uses eligible classified sessions at matching scope; test missing costs and spend without orders.
7. **Acquisition/budgets:** each customer acquired at most once using available full history and approved ties; reconcile attributed/unattributed acquisitions. Validate budget scope, effective dates and currency; ensure daily joins do not multiply budgets.
8. **Policy/reproducibility:** test approved timezone boundaries, currency conversion, cancellations and refunds. Verify full refreshes incorporate late-arriving data into attribution, first eligible orders and dependent metrics, and repeated refreshes on unchanged input produce identical results. Verify initial CAC uses period spend and customers acquired in that period. Record source mappings, decision versions, SQL, filters and refresh time for reproduction. Verify all six brief business questions and consistent, read-only Wren answers against these definitions.
