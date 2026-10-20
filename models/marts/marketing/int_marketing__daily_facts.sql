{{ config(materialized='table', schema='marts') }}

with media as (
    select performance_date as reporting_date, campaign_id, channel as marketing_channel,
        sum(spend_gbp) as spend_gbp, sum(impressions) as impressions, sum(clicks) as clicks,
        count(*) filter (where spend_gbp < 0 or impressions < 0 or clicks < 0) as negative_input_count
    from {{ ref('stg_marketing__ad_performance') }} group by 1, 2, 3
), sessions as (
    select cast(timezone('Europe/London', session_timestamp) as date) as reporting_date,
        campaign_id, channel as marketing_channel, count(*) as valid_sessions
    from {{ ref('stg_marketing__web_sessions') }} group by 1, 2, 3
), orders as (
    select reporting_date, campaign_id, marketing_channel,
    count(*) as placed_orders,
    count(*) filter (where is_attributed) as attributed_placed_orders,
    count(*) filter (where not is_attributed) as unattributed_placed_orders,
    count(*) filter (where commercially_eligible) as eligible_conversions,
    count(*) filter (where commercially_eligible and is_attributed) as attributed_orders,
    count(*) filter (where commercially_eligible and not is_attributed) as unattributed_eligible_orders,
    sum(gross_order_amount_gbp) as raw_gross_order_amount_gbp,
    sum(case when status = 'cancelled' then gross_order_amount_gbp else 0 end) as cancellation_gross_amount_gbp,
    sum(case when revenue_scope then gross_order_amount_gbp else 0 end) as gross_merchandise_revenue_gbp,
    sum(case when revenue_scope then refund_amount_gbp else 0 end) as sales_refunds_gbp,
    sum(case when status = 'cancelled' then refund_amount_gbp else 0 end) as cancellation_reversals_gbp,
    sum(case when revenue_scope then net_order_amount_gbp else 0 end) as net_revenue_gbp,
    sum(net_order_amount_gbp) as raw_net_order_amount_gbp,
    sum(case when is_attributed and revenue_scope then gross_order_amount_gbp else 0 end) as attributed_gross_merchandise_revenue_gbp,
    sum(case when is_attributed and revenue_scope then refund_amount_gbp else 0 end) as attributed_sales_refunds_gbp,
    sum(case when is_attributed and status = 'cancelled' then refund_amount_gbp else 0 end) as attributed_cancellation_reversals_gbp,
    sum(case when is_attributed and revenue_scope then net_order_amount_gbp else 0 end) as attributed_net_revenue_gbp,
    sum(case when not is_attributed and revenue_scope then gross_order_amount_gbp else 0 end) as unattributed_gross_merchandise_revenue_gbp,
    sum(case when not is_attributed and revenue_scope then refund_amount_gbp else 0 end) as unattributed_sales_refunds_gbp,
    sum(case when not is_attributed and status = 'cancelled' then refund_amount_gbp else 0 end) as unattributed_cancellation_reversals_gbp,
    sum(case when not is_attributed and revenue_scope then net_order_amount_gbp else 0 end) as unattributed_net_revenue_gbp,
    sum(negative_input_count) as negative_input_count
    from {{ ref('int_marketing__governed_orders') }} group by 1, 2, 3
), acquisitions as (
    select reporting_date, campaign_id, marketing_channel, count(*) as first_observed_acquisitions,
        count(*) filter (where is_attributed) as attributed_first_observed_acquisitions,
        count(*) filter (where not is_attributed) as unattributed_first_observed_acquisitions
    from {{ ref('int_marketing__first_observed_acquisitions') }} group by 1, 2, 3
), budgets as (
    select cast(d.day as date) as reporting_date, c.campaign_id, c.channel as marketing_channel,
        c.budget_gbp / (date_diff('day', c.start_date, c.end_date) + 1) as allocated_budget_gbp,
        case when c.budget_gbp < 0 then 1 else 0 end as negative_input_count
    from {{ ref('stg_marketing__campaigns') }} c,
        lateral generate_series(c.start_date, c.end_date, interval '1 day') d(day)
), keys as (
    select reporting_date, campaign_id, marketing_channel from media
    union select reporting_date, campaign_id, marketing_channel from sessions
    union select reporting_date, campaign_id, marketing_channel from orders
    union select reporting_date, campaign_id, marketing_channel from acquisitions
    union select reporting_date, campaign_id, marketing_channel from budgets
)
select k.*,
    coalesce(m.spend_gbp, 0) as spend_gbp,
    coalesce(m.impressions, 0) as impressions,
    coalesce(m.clicks, 0) as clicks,
    coalesce(s.valid_sessions, 0) as valid_sessions,
    coalesce(o.placed_orders, 0) as placed_orders,
    coalesce(o.attributed_placed_orders, 0) as attributed_placed_orders,
    coalesce(o.unattributed_placed_orders, 0) as unattributed_placed_orders,
    coalesce(o.eligible_conversions, 0) as eligible_conversions,
    coalesce(o.attributed_orders, 0) as attributed_orders,
    coalesce(o.unattributed_eligible_orders, 0) as unattributed_eligible_orders,
    coalesce(a.first_observed_acquisitions, 0) as first_observed_acquisitions,
    coalesce(a.attributed_first_observed_acquisitions, 0) as attributed_first_observed_acquisitions,
    coalesce(a.unattributed_first_observed_acquisitions, 0) as unattributed_first_observed_acquisitions,
    coalesce(o.raw_gross_order_amount_gbp, 0) as raw_gross_order_amount_gbp,
    coalesce(o.cancellation_gross_amount_gbp, 0) as cancellation_gross_amount_gbp,
    coalesce(o.gross_merchandise_revenue_gbp, 0) as gross_merchandise_revenue_gbp,
    coalesce(o.sales_refunds_gbp, 0) as sales_refunds_gbp,
    coalesce(o.cancellation_reversals_gbp, 0) as cancellation_reversals_gbp,
    coalesce(o.net_revenue_gbp, 0) as net_revenue_gbp,
    coalesce(o.raw_net_order_amount_gbp, 0) as raw_net_order_amount_gbp,
    coalesce(o.attributed_gross_merchandise_revenue_gbp, 0) as attributed_gross_merchandise_revenue_gbp,
    coalesce(o.unattributed_gross_merchandise_revenue_gbp, 0) as unattributed_gross_merchandise_revenue_gbp,
    coalesce(o.attributed_sales_refunds_gbp, 0) as attributed_sales_refunds_gbp,
    coalesce(o.unattributed_sales_refunds_gbp, 0) as unattributed_sales_refunds_gbp,
    coalesce(o.attributed_cancellation_reversals_gbp, 0) as attributed_cancellation_reversals_gbp,
    coalesce(o.unattributed_cancellation_reversals_gbp, 0) as unattributed_cancellation_reversals_gbp,
    coalesce(o.attributed_net_revenue_gbp, 0) as attributed_net_revenue_gbp,
    coalesce(o.unattributed_net_revenue_gbp, 0) as unattributed_net_revenue_gbp,
    coalesce(b.allocated_budget_gbp, 0) as allocated_budget_gbp,
    coalesce(m.negative_input_count, 0) + coalesce(o.negative_input_count, 0) + coalesce(b.negative_input_count, 0) as negative_input_count
from keys k
left join media m on k.reporting_date = m.reporting_date and k.campaign_id is not distinct from m.campaign_id and k.marketing_channel = m.marketing_channel
left join sessions s on k.reporting_date = s.reporting_date and k.campaign_id is not distinct from s.campaign_id and k.marketing_channel = s.marketing_channel
left join orders o on k.reporting_date = o.reporting_date and k.campaign_id is not distinct from o.campaign_id and k.marketing_channel = o.marketing_channel
left join acquisitions a on k.reporting_date = a.reporting_date and k.campaign_id is not distinct from a.campaign_id and k.marketing_channel = a.marketing_channel
left join budgets b on k.reporting_date = b.reporting_date and k.campaign_id is not distinct from b.campaign_id and k.marketing_channel = b.marketing_channel
