{% macro marketing_attribution_candidates(orders, sessions, campaigns) %}
with evaluated as (
    select o.order_id, o.customer_id, o.order_timestamp,
        o.order_timestamp - interval '168 hours' as attribution_window_start,
        s.session_id, s.customer_id as session_customer_id,
        s.session_timestamp as interaction_timestamp, s.campaign_id,
        s.source_medium, nullif(trim(split_part(s.source_medium, ' / ', 1)), '') as source,
        nullif(trim(split_part(s.source_medium, ' / ', 2)), '') as medium, s.channel,
        case
            when nullif(trim(o.customer_id), '') is null then 'missing_order_customer_id'
            when o.order_timestamp is null then 'missing_order_timestamp'
            when s.session_id is null then 'no_customer_sessions'
            when s.session_timestamp is null then 'missing_interaction_timestamp'
            when s.session_timestamp < o.order_timestamp - interval '168 hours' then 'before_lookback'
            when s.session_timestamp >= o.order_timestamp then 'at_or_after_order'
            when s.channel = 'Direct' then 'direct_session'
            when nullif(trim(s.campaign_id), '') is null then 'missing_campaign_id'
            when c.campaign_id is null then 'unknown_campaign_id'
            when s.channel not in ('Meta Paid Social', 'Google Paid Search', 'TikTok Paid Social')
                or s.channel is null then 'not_paid_channel'
            else 'eligible'
        end as candidate_status
    from {{ orders }} o
    left join {{ sessions }} s on o.customer_id = s.customer_id
        and nullif(trim(o.customer_id), '') is not null
    left join {{ campaigns }} c on s.campaign_id = c.campaign_id
), ranked as (
    select *, candidate_status = 'eligible' as is_eligible,
        case when candidate_status = 'eligible' then row_number() over (
            partition by order_id
            order by case when candidate_status = 'eligible' then 0 else 1 end,
                interaction_timestamp desc, session_id desc
        ) end as eligible_rank
    from evaluated
)
select *, coalesce(eligible_rank = 1, false) as is_winner from ranked
{% endmacro %}

{% macro marketing_orders_attributed(orders, candidates) %}
with diagnostics as (
    select order_id, count(session_id) as customer_session_count,
        count(*) filter (where candidate_status = 'missing_interaction_timestamp') as missing_time_count,
        count(*) filter (where candidate_status = 'missing_campaign_id') as missing_campaign_count,
        count(*) filter (where candidate_status = 'unknown_campaign_id') as unknown_campaign_count
    from {{ candidates }} group by order_id
)
select o.*, w.session_id, w.campaign_id, w.source_medium, w.source, w.medium,
    w.channel, w.interaction_timestamp,
    case when w.session_id is not null then 'attributed' else 'unattributed' end as attribution_status,
    case when w.session_id is not null then null
        when nullif(trim(o.customer_id), '') is null then 'missing_order_customer_id'
        when o.order_timestamp is null then 'missing_order_timestamp'
        when coalesce(d.customer_session_count, 0) = 0 then 'no_customer_sessions'
        when d.missing_time_count > 0 then 'missing_interaction_timestamp'
        when d.unknown_campaign_count > 0 then 'unknown_campaign_id'
        when d.missing_campaign_count > 0 then 'missing_campaign_id'
        else 'no_eligible_interaction_in_window'
    end as unattributed_reason
from {{ orders }} o
left join {{ candidates }} w on o.order_id = w.order_id and w.is_winner
left join diagnostics d on o.order_id = d.order_id
{% endmacro %}
