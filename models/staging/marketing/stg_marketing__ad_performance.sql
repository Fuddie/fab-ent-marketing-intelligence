{{ config(materialized="view", schema="staging") }}

select
    cast("date" as date) as performance_date,
    cast("campaign_id" as varchar) as campaign_id,
    cast("channel" as varchar) as channel,
    cast("spend_gbp" as decimal(18,2)) as spend_gbp,
    cast("impressions" as bigint) as impressions,
    cast("clicks" as bigint) as clicks
from {{ ref('ad_performance') }}
