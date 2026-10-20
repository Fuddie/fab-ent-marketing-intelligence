-- Source structure only: no order eligibility, attribution, or click/impression bound.
with active_days as (
    select c.campaign_id, d.active_date
    from {{ ref('stg_marketing__campaigns') }} c
    cross join lateral generate_series(c.start_date, c.end_date, interval '1 day') d(active_date)
)
select 'duplicate_ad_grain' as failure, campaign_id as source_id
from {{ ref('stg_marketing__ad_performance') }}
group by performance_date, campaign_id, channel
having count(*) > 1

union all
select 'campaign_dates', campaign_id
from {{ ref('stg_marketing__campaigns') }}
where start_date > end_date

union all
select 'ad_campaign_alignment', a.campaign_id
from {{ ref('stg_marketing__ad_performance') }} a
join {{ ref('stg_marketing__campaigns') }} c using (campaign_id)
where a.channel <> c.channel
   or a.performance_date not between c.start_date and c.end_date

union all
select 'missing_active_campaign_day', d.campaign_id
from active_days d
left join {{ ref('stg_marketing__ad_performance') }} a
    on a.campaign_id = d.campaign_id and a.performance_date = d.active_date
where a.campaign_id is null

union all
select 'session_campaign_classification', s.session_id
from {{ ref('stg_marketing__web_sessions') }} s
left join {{ ref('stg_marketing__campaigns') }} c using (campaign_id)
where (s.channel in ('Direct', 'Organic') and s.campaign_id is not null)
   or (s.channel not in ('Direct', 'Organic') and s.campaign_id is null)
   or s.channel <> c.channel
   or s.source_medium <> case s.channel
       when 'Meta Paid Social' then 'facebook / paid_social'
       when 'Google Paid Search' then 'google / cpc'
       when 'TikTok Paid Social' then 'tiktok / paid_social'
       when 'Direct' then '(direct) / (none)'
       when 'Organic' then 'google / organic'
   end

union all
select 'line_arithmetic', order_item_id
from {{ ref('stg_marketing__order_items') }}
where quantity not between 1 and 3
   or gross_line_amount_gbp <> quantity * unit_price_gbp
   or net_line_amount_gbp <> gross_line_amount_gbp - refund_amount_gbp

union all
select 'order_arithmetic_or_status', order_id
from {{ ref('stg_marketing__orders') }}
where net_order_amount_gbp <> gross_order_amount_gbp - refund_amount_gbp
   or (status = 'completed' and refund_amount_gbp <> 0)
   or (status in ('cancelled', 'refunded')
       and (refund_amount_gbp <> gross_order_amount_gbp or net_order_amount_gbp <> 0))
   or (status = 'partially_refunded'
       and not (refund_amount_gbp > 0 and refund_amount_gbp < gross_order_amount_gbp))
