{% set metrics = [
    'spend_gbp',
    'impressions',
    'clicks',
    'valid_sessions',
    'placed_orders',
    'attributed_placed_orders',
    'unattributed_placed_orders',
    'eligible_conversions',
    'attributed_orders',
    'unattributed_eligible_orders',
    'first_observed_acquisitions',
    'attributed_first_observed_acquisitions',
    'unattributed_first_observed_acquisitions',
    'raw_gross_order_amount_gbp',
    'cancellation_gross_amount_gbp',
    'gross_merchandise_revenue_gbp',
    'sales_refunds_gbp',
    'cancellation_reversals_gbp',
    'net_revenue_gbp',
    'raw_net_order_amount_gbp',
    'attributed_gross_merchandise_revenue_gbp',
    'unattributed_gross_merchandise_revenue_gbp',
    'attributed_sales_refunds_gbp',
    'unattributed_sales_refunds_gbp',
    'attributed_cancellation_reversals_gbp',
    'unattributed_cancellation_reversals_gbp',
    'attributed_net_revenue_gbp',
    'unattributed_net_revenue_gbp',
    'allocated_budget_gbp',
    'negative_input_count'
] %}
select 'campaign_daily' as failure
from (
    select reporting_date, campaign_id,
        {% for metric in metrics %}
        sum({{ metric }}) as {{ metric }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref('int_marketing__daily_facts') }}
    where campaign_id is not null
    group by 1, 2
) e
full join {{ ref('mart_marketing__campaign_daily') }} a using (reporting_date, campaign_id)
where false
    {% for metric in metrics %}
    {% if metric == 'allocated_budget_gbp' %}
    or (a.{{ metric }} is null) <> (e.{{ metric }} is null)
    or abs(a.{{ metric }} - e.{{ metric }}) > 0.000001
    {% else %}
    or a.{{ metric }} is distinct from e.{{ metric }}
    {% endif %}
    {% endfor %}
union all
select 'campaign_summary' as failure
from (
    select campaign_id,
        {% for metric in metrics %}
        sum({{ metric }}) as {{ metric }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref('int_marketing__daily_facts') }}
    where campaign_id is not null
    group by 1
) e
full join {{ ref('mart_marketing__campaign_summary') }} a using (campaign_id)
where false
    {% for metric in metrics %}
    {% if metric == 'allocated_budget_gbp' %}
    or (a.{{ metric }} is null) <> (e.{{ metric }} is null)
    or abs(a.{{ metric }} - e.{{ metric }}) > 0.000001
    {% else %}
    or a.{{ metric }} is distinct from e.{{ metric }}
    {% endif %}
    {% endfor %}
union all
select 'channel_monthly' as failure
from (
    select cast(date_trunc('month', reporting_date) as date) as reporting_month, marketing_channel,
        {% for metric in metrics %}
        sum({{ metric }}) as {{ metric }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref('int_marketing__daily_facts') }}
    group by 1, 2
) e
full join {{ ref('mart_marketing__channel_monthly') }} a using (reporting_month, marketing_channel)
where false
    {% for metric in metrics %}
    {% if metric == 'allocated_budget_gbp' %}
    or (a.{{ metric }} is null) <> (e.{{ metric }} is null)
    or abs(a.{{ metric }} - e.{{ metric }}) > 0.000001
    {% else %}
    or a.{{ metric }} is distinct from e.{{ metric }}
    {% endif %}
    {% endfor %}
union all
select 'monthly_overview' as failure
from (
    select cast(date_trunc('month', reporting_date) as date) as reporting_month,
        {% for metric in metrics %}
        sum({{ metric }}) as {{ metric }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref('int_marketing__daily_facts') }}
    group by 1
) e
full join {{ ref('mart_marketing__monthly_overview') }} a using (reporting_month)
where false
    {% for metric in metrics %}
    {% if metric == 'allocated_budget_gbp' %}
    or (a.{{ metric }} is null) <> (e.{{ metric }} is null)
    or abs(a.{{ metric }} - e.{{ metric }}) > 0.000001
    {% else %}
    or a.{{ metric }} is distinct from e.{{ metric }}
    {% endif %}
    {% endfor %}
