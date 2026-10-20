-- Exact bidirectional multiset equality checks all order fields, including NULL amounts.
{% set cols = 'order_id, customer_id, order_timestamp, status, gross_order_amount_gbp, refund_amount_gbp, net_order_amount_gbp' %}
with original as (select {{ cols }} from {{ ref('stg_marketing__orders') }}),
final as (select {{ cols }} from {{ ref('int_marketing__orders_attributed') }})
(select * from original except all select * from final)
union all
(select * from final except all select * from original)
