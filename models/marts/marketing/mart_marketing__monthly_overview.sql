{{ config(materialized='table', schema='marts') }}

with monthly as (
    select cast(date_trunc('month', reporting_date) as date) as reporting_month,
        'platform_media_only' as cost_coverage,
        'first_observed_2025_snapshot' as acquisition_basis,
        {{ marketing_mart_sum_columns() }}
    from {{ ref('int_marketing__daily_facts') }} group by 1
)
select *, {{ marketing_mart_ratios('overview', '100.0 * spend_gbp / nullif(allocated_budget_gbp, 0)', '100.0 * spend_gbp / nullif(allocated_budget_gbp, 0)') }}
from monthly
