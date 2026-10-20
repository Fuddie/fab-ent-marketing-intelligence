{{ config(materialized='table', schema='marts') }}

with ranked as (
    select *, row_number() over (partition by customer_id order by order_timestamp, order_id) as acquisition_rank
    from {{ ref('int_marketing__governed_orders') }}
    where commercially_eligible
)
select customer_id, order_id as acquisition_order_id, order_timestamp as acquisition_timestamp,
    reporting_date, campaign_id, marketing_channel, is_attributed,
    'first_observed_2025_snapshot' as acquisition_basis
from ranked where acquisition_rank = 1
