{{ config(materialized="view", schema="staging") }}

select
    cast("customer_id" as varchar) as customer_id,
    cast("created_at" as timestamptz) as created_at
from {{ ref('customers') }}
