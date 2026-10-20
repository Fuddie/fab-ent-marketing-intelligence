# Governed marketing query rules

METRIC_CONTRACT.md in the repository root is the business authority. Use only
the five Marketing models. Each maps directly to a governed dbt mart in
fab_ent.raw_marts. Do not query seeds or supporting intermediate tables.

Choose one fact model for each question. CampaignDaily is London date/campaign;
CampaignSummary is full-snapshot campaign; ChannelMonthly is London month/channel;
MonthlyOverview is London month across all outcomes. There are no relationships:
joining aggregate marts can duplicate spend, budgets, orders and revenue.

All money is GBP. CTR, conversion, attribution and budget rates are percentage
points; ROAS is a multiple. CPC and media-only CAC are GBP. Use cube measures
for grouped metrics, or explicitly divide SUM(numerator) by NULLIF(SUM(denominator),0).
Never SUM or AVG stored row ratios. Zero or missing denominators mean NULL/N/A;
zero numerator with positive denominator means zero. Preserve signed values.

Placed orders include every status. Eligible conversions require completed or
partially refunded status and positive net value. Attributed orders are the
campaign-assigned eligible subset. Revenue has a separate eligibility policy:
completed, partially refunded and fully refunded sales, excluding cancellations.
Gross merchandise revenue includes fully refunded sales; sales refunds reduce
gross to net. Cancellation reversals are not customer cash refunds. Never
subtract refunds from source net a second time. Do not describe gross revenue
as revenue from conversion-eligible orders. If asked about "eligible revenue",
explain this distinction and label the chosen scope explicitly.

ROAS always divides attributed gross/net revenue by media spend, including in
the overview. Total website net revenue includes unattributed revenue and must
remain separately visible. Overview conversion divides all eligible orders by
all valid sessions. Campaign and paid-channel conversion divides attributed
eligible orders by valid classified sessions, including anonymous sessions.
These are period order/session rates and can exceed 100%.

CAC divides period media spend by paid-attributed first-observed acquisitions,
not all acquisitions. First-observed acquisition selects the earliest eligible
UTC order per customer across the available history, ties by ascending order ID,
then filters reporting periods. Preserve that order's assignment even if a later
order is paid. This fixed 2025 snapshot cannot establish lifetime acquisition.
It has no pre-2025 history or post-2025 conversion tail. Acquisition basis is
first_observed_2025_snapshot. CAC is media-only and period-based, not cohort CAC.

Direct and Organic describe session traffic only. Unmatched orders belong to
Unattributed; do not infer Direct/Organic revenue. Conversion, ROAS and CAC are
NULL for channels with cost_coverage=not_available. Channel cube cost-dependent
rates also suppress mixed paid/unpaid groups. Use MonthlyOverview for overall
website rates and overall paid CAC rather than an unfiltered channel cube.

CampaignSummary lifetime budget is counted once per campaign. CampaignDaily
lifetime budgets, cumulative spend and expected cumulative budgets are
non-additive across dates. Daily utilisation and pacing apply only to the exact
date/campaign row: cumulative spend / lifetime budget, and cumulative spend /
straight-line expected cumulative budget respectively. Daily cubes deliberately
omit these two measures. Never replace them with daily spend / lifetime budget.
Monthly budget utilisation/pacing use period spend / allocated active-day budget;
allocations are monitoring conventions, not approved monthly budgets.

Quality flags are BOOLEAN dimensions describing the original mart row. Filtering
by a row flag selects rows, not a recalculated alert at the new aggregation grain.
For full-snapshot campaigns without orders or over budget, use CampaignSummary.
A false incomplete-attribution flag on a campaign does not establish global
completeness; use MonthlyOverview. Spend without orders is not proof of waste.

Events use Europe/London reporting dates; attribution keeps the existing 168-hour
UTC lookback. Final-status refunds/cancellations restate original purchase periods.
No adjustment-event dates, cash flow, profit, VAT, shipping, fees, causal effect,
missing-feed detection or verified lifetime customer acquisition are available.
Zero-filled activity relies on the validated complete synthetic snapshot.

CampaignMonthly is one row per Europe/London reporting month and campaign, rolled up from CampaignDaily. Campaign questions containing "per month", "monthly", or "each month" must use MarketingCampaignMonthly and reporting_month. Revenue generation defaults to attributed_net_revenue_gbp; gross revenue uses attributed_gross_merchandise_revenue_gbp. Top three per month uses QUALIFY ROW_NUMBER() OVER (PARTITION BY reporting_month ORDER BY attributed_net_revenue_gbp DESC, campaign_id ASC) <= 3, then ORDER BY reporting_month, attributed_net_revenue_gbp DESC, campaign_id. Stored monthly net_roas is monthly attributed net revenue / NULLIF(monthly spend,0); recompute from summed components for further rollups.
