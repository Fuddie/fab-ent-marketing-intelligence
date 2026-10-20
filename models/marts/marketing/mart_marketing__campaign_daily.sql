{{ config(materialized='table', schema='marts') }}

with daily as (
    select f.*, c.campaign_name, c.objective, c.start_date, c.end_date, c.budget_gbp as lifetime_budget_gbp,
        'platform_media_only' as cost_coverage,
        'first_observed_2025_snapshot' as acquisition_basis,
        sum(f.spend_gbp) over (partition by f.campaign_id order by f.reporting_date rows unbounded preceding) as cumulative_spend_gbp,
        c.budget_gbp * least(greatest(date_diff('day', c.start_date, f.reporting_date) + 1, 0),
            date_diff('day', c.start_date, c.end_date) + 1) / (date_diff('day', c.start_date, c.end_date) + 1) as expected_cumulative_spend_gbp
    from {{ ref('int_marketing__daily_facts') }} f
    join {{ ref('stg_marketing__campaigns') }} c using (campaign_id)
)
select *, {{ marketing_mart_ratios('campaign', '100.0 * cumulative_spend_gbp / nullif(lifetime_budget_gbp, 0)', '100.0 * cumulative_spend_gbp / nullif(expected_cumulative_spend_gbp, 0)') }}
from daily
