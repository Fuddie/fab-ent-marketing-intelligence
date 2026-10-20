{{ config(materialized="view", schema="staging") }}

select
    cast("order_item_id" as varchar) as order_item_id,
    cast("order_id" as varchar) as order_id,
    cast("product_id" as varchar) as product_id,
    cast("quantity" as bigint) as quantity,
    cast("unit_price_gbp" as decimal(18,2)) as unit_price_gbp,
    cast("gross_line_amount_gbp" as decimal(18,2)) as gross_line_amount_gbp,
    cast("refund_amount_gbp" as decimal(18,2)) as refund_amount_gbp,
    cast("net_line_amount_gbp" as decimal(18,2)) as net_line_amount_gbp
from {{ ref('order_items') }}
