with a as (select * from {{ ref('int_marketing__orders_attributed') }}),
s as (select * from {{ ref('stg_marketing__web_sessions') }})
select a.order_id from a left join s using (session_id)
where (a.attribution_status = 'attributed' and (
    s.session_id is null or a.customer_id is distinct from s.customer_id
    or a.interaction_timestamp is distinct from s.session_timestamp
    or a.campaign_id is distinct from s.campaign_id
    or a.channel is distinct from s.channel
    or a.source_medium is distinct from s.source_medium
    or a.unattributed_reason is not null
    or s.channel not in ('Meta Paid Social', 'Google Paid Search', 'TikTok Paid Social')
    or not (s.session_timestamp >= a.order_timestamp - interval '168 hours'
        and s.session_timestamp < a.order_timestamp)))
    or (a.attribution_status = 'unattributed' and (a.unattributed_reason is null
        or a.session_id is not null or a.campaign_id is not null
        or a.interaction_timestamp is not null or a.channel is not null
        or a.source is not null or a.medium is not null or a.source_medium is not null))
union all
select order_id from {{ ref('int_marketing__order_attribution_candidates') }}
group by order_id having count(*) filter (where is_winner) > 1
union all
-- Independent anti-join proves no eligible touch outranks the selected one,
-- and an unattributed order has no eligible touch.
select a.order_id from a join s on a.customer_id = s.customer_id
join {{ ref('stg_marketing__campaigns') }} c on s.campaign_id = c.campaign_id
where s.channel in ('Meta Paid Social', 'Google Paid Search', 'TikTok Paid Social')
  and s.session_timestamp >= a.order_timestamp - interval '168 hours'
  and s.session_timestamp < a.order_timestamp
  and (a.session_id is null or s.session_timestamp > a.interaction_timestamp
    or (s.session_timestamp = a.interaction_timestamp and s.session_id > a.session_id))
