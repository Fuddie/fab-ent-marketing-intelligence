{{ config(materialized="view", schema="staging") }}

select
    cast("order_id" as varchar) as order_id,
    cast("order_timestamp" as timestamptz) as order_timestamp,
    cast("customer_id" as varchar) as customer_id,
    cast("status" as varchar) as status,
    cast("gross_order_amount_gbp" as decimal(18,2)) as gross_order_amount_gbp,
    cast("refund_amount_gbp" as decimal(18,2)) as refund_amount_gbp,
    cast("net_order_amount_gbp" as decimal(18,2)) as net_order_amount_gbp
from {{ ref('orders') }}
