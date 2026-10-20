{{ config(materialized='table', schema='marts') }}

with facts as (
    select campaign_id, {{ marketing_mart_sum_columns() }}
    from {{ ref('int_marketing__daily_facts') }} where campaign_id is not null group by campaign_id
), summary as (
    select c.campaign_id, c.campaign_name, c.channel as marketing_channel, c.objective,
        c.start_date, c.end_date, c.budget_gbp as lifetime_budget_gbp,
        'platform_media_only' as cost_coverage, 'first_observed_2025_snapshot' as acquisition_basis,
        coalesce(f.spend_gbp, 0) as spend_gbp,
        coalesce(f.impressions, 0) as impressions,
        coalesce(f.clicks, 0) as clicks,
        coalesce(f.valid_sessions, 0) as valid_sessions,
        coalesce(f.placed_orders, 0) as placed_orders,
        coalesce(f.attributed_placed_orders, 0) as attributed_placed_orders,
        coalesce(f.unattributed_placed_orders, 0) as unattributed_placed_orders,
        coalesce(f.eligible_conversions, 0) as eligible_conversions,
        coalesce(f.attributed_orders, 0) as attributed_orders,
        coalesce(f.unattributed_eligible_orders, 0) as unattributed_eligible_orders,
        coalesce(f.first_observed_acquisitions, 0) as first_observed_acquisitions,
        coalesce(f.attributed_first_observed_acquisitions, 0) as attributed_first_observed_acquisitions,
        coalesce(f.unattributed_first_observed_acquisitions, 0) as unattributed_first_observed_acquisitions,
        coalesce(f.raw_gross_order_amount_gbp, 0) as raw_gross_order_amount_gbp,
        coalesce(f.cancellation_gross_amount_gbp, 0) as cancellation_gross_amount_gbp,
        coalesce(f.gross_merchandise_revenue_gbp, 0) as gross_merchandise_revenue_gbp,
        coalesce(f.sales_refunds_gbp, 0) as sales_refunds_gbp,
        coalesce(f.cancellation_reversals_gbp, 0) as cancellation_reversals_gbp,
        coalesce(f.net_revenue_gbp, 0) as net_revenue_gbp,
        coalesce(f.raw_net_order_amount_gbp, 0) as raw_net_order_amount_gbp,
        coalesce(f.attributed_gross_merchandise_revenue_gbp, 0) as attributed_gross_merchandise_revenue_gbp,
        coalesce(f.unattributed_gross_merchandise_revenue_gbp, 0) as unattributed_gross_merchandise_revenue_gbp,
        coalesce(f.attributed_sales_refunds_gbp, 0) as attributed_sales_refunds_gbp,
        coalesce(f.unattributed_sales_refunds_gbp, 0) as unattributed_sales_refunds_gbp,
        coalesce(f.attributed_cancellation_reversals_gbp, 0) as attributed_cancellation_reversals_gbp,
        coalesce(f.unattributed_cancellation_reversals_gbp, 0) as unattributed_cancellation_reversals_gbp,
        coalesce(f.attributed_net_revenue_gbp, 0) as attributed_net_revenue_gbp,
        coalesce(f.unattributed_net_revenue_gbp, 0) as unattributed_net_revenue_gbp,
        coalesce(f.allocated_budget_gbp, 0) as allocated_budget_gbp,
        coalesce(f.negative_input_count, 0) as negative_input_count
    from {{ ref('stg_marketing__campaigns') }} c left join facts f using (campaign_id)
)
select *, {{ marketing_mart_ratios('campaign', '100.0 * spend_gbp / nullif(lifetime_budget_gbp, 0)', '100.0 * spend_gbp / nullif(lifetime_budget_gbp, 0)') }}
from summary
