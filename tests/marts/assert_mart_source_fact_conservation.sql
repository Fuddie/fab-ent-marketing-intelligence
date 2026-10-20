with media as (
    select performance_date as reporting_date, campaign_id, channel as marketing_channel,
        sum(spend_gbp) as spend_gbp, sum(impressions) as impressions, sum(clicks) as clicks
    from {{ ref('stg_marketing__ad_performance') }} group by 1,2,3
), sessions as (
    select cast(timezone('Europe/London',session_timestamp) as date) as reporting_date,
        campaign_id, channel as marketing_channel, count(*) as valid_sessions
    from {{ ref('stg_marketing__web_sessions') }} group by 1,2,3
), orders as (
    select cast(timezone('Europe/London',order_timestamp) as date) as reporting_date,
        campaign_id, coalesce(channel,'Unattributed') as marketing_channel,
        count(*) placed_orders,
        count(*) filter(where status in ('completed','partially_refunded') and net_order_amount_gbp>0) eligible_conversions,
        sum(gross_order_amount_gbp) raw_gross_order_amount_gbp,
        sum(case when status<>'cancelled' then gross_order_amount_gbp else 0 end) gross_merchandise_revenue_gbp,
        sum(case when status<>'cancelled' then refund_amount_gbp else 0 end) sales_refunds_gbp,
        sum(case when status='cancelled' then refund_amount_gbp else 0 end) cancellation_reversals_gbp,
        sum(case when status<>'cancelled' then net_order_amount_gbp else 0 end) net_revenue_gbp
    from {{ ref('int_marketing__orders_attributed') }} group by 1,2,3
), acquisitions as (
    select reporting_date, campaign_id, marketing_channel, count(*) first_observed_acquisitions
    from {{ ref('int_marketing__first_observed_acquisitions') }} group by 1,2,3
), actual as (select * from {{ ref('int_marketing__daily_facts') }})
select 'media' as failure from media e full join actual a
on e.reporting_date=a.reporting_date and e.campaign_id is not distinct from a.campaign_id and e.marketing_channel=a.marketing_channel
where coalesce(e.spend_gbp,0)<>coalesce(a.spend_gbp,0) or coalesce(e.impressions,0)<>coalesce(a.impressions,0) or coalesce(e.clicks,0)<>coalesce(a.clicks,0)
union all
select 'sessions' from sessions e full join actual a
on e.reporting_date=a.reporting_date and e.campaign_id is not distinct from a.campaign_id and e.marketing_channel=a.marketing_channel
where coalesce(e.valid_sessions,0)<>coalesce(a.valid_sessions,0)
union all
select 'orders' from orders e full join actual a
on e.reporting_date=a.reporting_date and e.campaign_id is not distinct from a.campaign_id and e.marketing_channel=a.marketing_channel
where coalesce(e.placed_orders,0)<>coalesce(a.placed_orders,0)
    or coalesce(e.eligible_conversions,0)<>coalesce(a.eligible_conversions,0)
    or coalesce(e.raw_gross_order_amount_gbp,0)<>coalesce(a.raw_gross_order_amount_gbp,0)
    or coalesce(e.gross_merchandise_revenue_gbp,0)<>coalesce(a.gross_merchandise_revenue_gbp,0)
    or coalesce(e.sales_refunds_gbp,0)<>coalesce(a.sales_refunds_gbp,0)
    or coalesce(e.cancellation_reversals_gbp,0)<>coalesce(a.cancellation_reversals_gbp,0)
    or coalesce(e.net_revenue_gbp,0)<>coalesce(a.net_revenue_gbp,0)
union all
select 'acquisitions' from acquisitions e full join actual a
on e.reporting_date=a.reporting_date and e.campaign_id is not distinct from a.campaign_id and e.marketing_channel=a.marketing_channel
where coalesce(e.first_observed_acquisitions,0)<>coalesce(a.first_observed_acquisitions,0)
