-- Fixed synthetic snapshot baselines from README; all source order statuses.
select 'media_spend' as failure
from {{ ref('stg_marketing__ad_performance') }}
having sum(spend_gbp) is distinct from 189198.54::decimal(18,2)
union all
select 'order_amounts'
from {{ ref('stg_marketing__orders') }}
having sum(gross_order_amount_gbp) is distinct from 416314.00::decimal(18,2)
    or sum(refund_amount_gbp) is distinct from 62956.50::decimal(18,2)
    or sum(net_order_amount_gbp) is distinct from 353357.50::decimal(18,2)
