{{ config(materialized='table', schema='marts') }}

with line_flags as (
    select order_id, count(*) filter (where quantity < 0 or unit_price_gbp < 0
        or gross_line_amount_gbp < 0 or refund_amount_gbp < 0 or net_line_amount_gbp < 0) as negative_line_inputs
    from {{ ref('stg_marketing__order_items') }} group by order_id
)
select o.*,
    cast(timezone('Europe/London', order_timestamp) as date) as reporting_date,
    status in ('completed', 'partially_refunded') and net_order_amount_gbp > 0 as commercially_eligible,
    status in ('completed', 'partially_refunded', 'refunded') as revenue_scope,
    attribution_status = 'attributed' and campaign_id is not null as is_attributed,
    case when attribution_status = 'attributed' then channel else 'Unattributed' end as marketing_channel,
    case when gross_order_amount_gbp < 0 or refund_amount_gbp < 0 or net_order_amount_gbp < 0
        or coalesce(l.negative_line_inputs, 0) > 0 then 1 else 0 end as negative_input_count
from {{ ref('int_marketing__orders_attributed') }} o
left join line_flags l using (order_id)
