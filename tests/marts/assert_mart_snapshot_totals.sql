with totals as (
    select sum(spend_gbp) spend, sum(raw_gross_order_amount_gbp) raw_gross,
        sum(gross_merchandise_revenue_gbp) gross, sum(sales_refunds_gbp) refunds,
        sum(cancellation_reversals_gbp) reversals, sum(net_revenue_gbp) net,
        sum(placed_orders) placed, sum(eligible_conversions) eligible,
        sum(attributed_orders) attributed, sum(unattributed_eligible_orders) unattributed,
        sum(valid_sessions) sessions, sum(attributed_placed_orders) attributed_placed
    from {{ ref('mart_marketing__monthly_overview') }}
)
select * from totals
where spend <> 189198.54 or raw_gross <> 416314.00 or gross <> 396434.00
    or refunds <> 43076.50 or reversals <> 19880.00 or net <> 353357.50
    or placed <> 2500 or eligible <> 2228 or attributed <> 1439 or unattributed <> 789
    or sessions <> 15000 or attributed_placed <> 1606
    or raw_gross <> (select sum(gross_line_amount_gbp) from {{ ref('stg_marketing__order_items') }})
    or spend <> (select sum(spend_gbp) from {{ ref('stg_marketing__ad_performance') }})
