{{ config(materialized='table', schema='marts') }}

with monthly as (
    select cast(date_trunc('month', reporting_date) as date) as reporting_month, marketing_channel,
        case when marketing_channel in ('Meta Paid Social', 'Google Paid Search', 'TikTok Paid Social')
            then 'platform_media_only' else 'not_available' end as cost_coverage,
        'first_observed_2025_snapshot' as acquisition_basis,
        {{ marketing_mart_sum_columns() }}
    from {{ ref('int_marketing__daily_facts') }} group by 1, 2
)
select *, {{ marketing_mart_ratios('channel', '100.0 * spend_gbp / nullif(allocated_budget_gbp, 0)', '100.0 * spend_gbp / nullif(allocated_budget_gbp, 0)') }}
from monthly
