{{ config(materialized='table', schema='marts') }}

-- reporting_date is already the governed Europe/London date. Never truncate UTC.
with monthly as (
    select date_trunc('month', reporting_date)::date as reporting_month,
        campaign_id, campaign_name, marketing_channel,
        sum(spend_gbp) as spend_gbp,
        sum(eligible_conversions) as eligible_conversions,
        sum(attributed_gross_merchandise_revenue_gbp) as attributed_gross_merchandise_revenue_gbp,
        sum(attributed_net_revenue_gbp) as attributed_net_revenue_gbp
    from {{ ref('mart_marketing__campaign_daily') }}
    group by 1, 2, 3, 4
)
select *, attributed_net_revenue_gbp / nullif(spend_gbp, 0) as net_roas
from monthly
