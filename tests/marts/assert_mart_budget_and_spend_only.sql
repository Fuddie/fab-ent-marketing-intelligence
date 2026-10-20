with summary as (
    select c.campaign_id, c.budget_gbp, m.lifetime_budget_gbp, m.allocated_budget_gbp,
        m.spend_gbp, m.attributed_orders, m.flag_spend_without_eligible_attributed_orders,
        (select sum(a.spend_gbp) from {{ ref('stg_marketing__ad_performance') }} a where a.campaign_id=c.campaign_id) as source_spend
    from {{ ref('stg_marketing__campaigns') }} c
    full join {{ ref('mart_marketing__campaign_summary') }} m using (campaign_id)
), daily as (
    select d.*,
        (select sum(a.spend_gbp) from {{ ref('stg_marketing__ad_performance') }} a
          where a.campaign_id=d.campaign_id and a.performance_date<=d.reporting_date) as expected_spend,
        lifetime_budget_gbp * least(greatest(date_diff('day', start_date, reporting_date)+1,0),
            date_diff('day',start_date,end_date)+1) / (date_diff('day',start_date,end_date)+1) as expected_budget
    from {{ ref('mart_marketing__campaign_daily') }} d
)
select 'summary_budget_or_missing_campaign' as failure, campaign_id from summary
where budget_gbp is distinct from lifetime_budget_gbp or abs(allocated_budget_gbp-budget_gbp)>0.000001
    or spend_gbp <> coalesce(source_spend,0)
    or (campaign_id in ('CAM-0023','CAM-0024') and
        (spend_gbp<=0 or attributed_orders<>0 or not flag_spend_without_eligible_attributed_orders))
union all
select 'daily_cumulative_budget',campaign_id from daily
where cumulative_spend_gbp <> coalesce(expected_spend,0) or abs(expected_cumulative_spend_gbp-expected_budget)>0.000001
