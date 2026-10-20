{{ config(materialized="view", schema="staging") }}

select
    cast("product_id" as varchar) as product_id,
    cast("product_name" as varchar) as product_name,
    cast("category" as varchar) as category,
    cast("unit_price_gbp" as decimal(18,2)) as unit_price_gbp,
    cast("currency" as varchar) as currency
from {{ ref('products') }}
