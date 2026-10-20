with lines as (
    select order_id, count(*) as line_count,
        sum(gross_line_amount_gbp) as gross,
        sum(refund_amount_gbp) as refund,
        sum(net_line_amount_gbp) as net
    from {{ ref('stg_marketing__order_items') }}
    group by order_id
)
select o.order_id, l.order_id as line_order_id
from {{ ref('stg_marketing__orders') }} o
full outer join lines l using (order_id)
where o.order_id is null or l.order_id is null
   or l.line_count not between 1 and 4
   or o.gross_order_amount_gbp is distinct from l.gross
   or o.refund_amount_gbp is distinct from l.refund
   or o.net_order_amount_gbp is distinct from l.net
