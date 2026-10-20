{{ config(materialized="view", schema="staging") }}

select
    cast("session_id" as varchar) as session_id,
    cast("session_timestamp" as timestamptz) as session_timestamp,
    cast("customer_id" as varchar) as customer_id,
    cast("campaign_id" as varchar) as campaign_id,
    cast("channel" as varchar) as channel,
    cast("source_medium" as varchar) as source_medium,
    cast("device" as varchar) as device
from {{ ref('web_sessions') }}
