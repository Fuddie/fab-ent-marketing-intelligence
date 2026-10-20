with expected as (
    select customer_id, order_id as acquisition_order_id, order_timestamp as acquisition_timestamp,
        cast(timezone('Europe/London', order_timestamp) as date) as reporting_date,
        campaign_id, coalesce(channel, 'Unattributed') as marketing_channel,
        attribution_status = 'attributed' and campaign_id is not null as is_attributed,
        'first_observed_2025_snapshot' as acquisition_basis
    from {{ ref('int_marketing__orders_attributed') }}
    where status in ('completed', 'partially_refunded') and net_order_amount_gbp > 0
    qualify row_number() over (partition by customer_id order by order_timestamp, order_id) = 1
), actual as (select * from {{ ref('int_marketing__first_observed_acquisitions') }})
(select * from expected except all select * from actual)
union all
(select * from actual except all select * from expected)
