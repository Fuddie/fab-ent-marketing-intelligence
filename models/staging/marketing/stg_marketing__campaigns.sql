{{ config(materialized="view", schema="staging") }}

select
    cast("campaign_id" as varchar) as campaign_id,
    cast("campaign_name" as varchar) as campaign_name,
    cast("channel" as varchar) as channel,
    cast("objective" as varchar) as objective,
    cast("start_date" as date) as start_date,
    cast("end_date" as date) as end_date,
    cast("budget_gbp" as decimal(18,2)) as budget_gbp
from {{ ref('campaigns') }}
