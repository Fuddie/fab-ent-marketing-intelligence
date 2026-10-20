{% test marketing_unique_grain(model, columns) %}
select {{ columns | join(', ') }}, count(*) as row_count
from {{ model }} group by {{ columns | join(', ') }} having count(*) > 1
{% endtest %}

{% test marketing_mart_invariants(model, scope, budget_kind) %}
with expected as (
    select *,
        100.0 * clicks / nullif(impressions, 0) as expected_ctr,
        spend_gbp / nullif(clicks, 0) as expected_cpc,
        {% if scope == 'overview' %}
        100.0 * eligible_conversions / nullif(valid_sessions, 0)
        {% else %}
        case when cost_coverage = 'platform_media_only' then 100.0 * attributed_orders / nullif(valid_sessions, 0) end
        {% endif %} as expected_conversion,
        case when cost_coverage = 'platform_media_only' then attributed_gross_merchandise_revenue_gbp / nullif(spend_gbp, 0) end as expected_gross_roas,
        case when cost_coverage = 'platform_media_only' then attributed_net_revenue_gbp / nullif(spend_gbp, 0) end as expected_net_roas,
        case when cost_coverage = 'platform_media_only' then spend_gbp / nullif(attributed_first_observed_acquisitions, 0) end as expected_cac,
        100.0 * attributed_orders / nullif(eligible_conversions, 0) as expected_attribution,
        {% if budget_kind == 'daily' %}
        100.0 * cumulative_spend_gbp / nullif(lifetime_budget_gbp, 0) as expected_utilisation,
        100.0 * cumulative_spend_gbp / nullif(expected_cumulative_spend_gbp, 0) as expected_pacing
        {% elif budget_kind == 'lifetime' %}
        100.0 * spend_gbp / nullif(lifetime_budget_gbp, 0) as expected_utilisation,
        100.0 * spend_gbp / nullif(lifetime_budget_gbp, 0) as expected_pacing
        {% else %}
        100.0 * spend_gbp / nullif(allocated_budget_gbp, 0) as expected_utilisation,
        100.0 * spend_gbp / nullif(allocated_budget_gbp, 0) as expected_pacing
        {% endif %}
    from {{ model }}
)
select * from expected where
    placed_orders <> attributed_placed_orders + unattributed_placed_orders
    or eligible_conversions <> attributed_orders + unattributed_eligible_orders
    or first_observed_acquisitions <> attributed_first_observed_acquisitions + unattributed_first_observed_acquisitions
    or raw_gross_order_amount_gbp - cancellation_gross_amount_gbp <> gross_merchandise_revenue_gbp
    or gross_merchandise_revenue_gbp - sales_refunds_gbp <> net_revenue_gbp
    or raw_gross_order_amount_gbp - sales_refunds_gbp - cancellation_reversals_gbp <> raw_net_order_amount_gbp
    or cancellation_gross_amount_gbp <> cancellation_reversals_gbp
    {% for metric in ['gross_merchandise_revenue_gbp','sales_refunds_gbp','cancellation_reversals_gbp','net_revenue_gbp'] %}
    or {{ metric }} <> attributed_{{ metric }} + unattributed_{{ metric }}
    {% endfor %}
    {% for actual, expected in [('ctr_pct','expected_ctr'),('cpc_gbp','expected_cpc'),('conversion_rate_pct','expected_conversion'),('gross_roas','expected_gross_roas'),('net_roas','expected_net_roas'),('media_only_cac_gbp','expected_cac'),('attribution_rate_pct','expected_attribution'),('budget_utilisation_pct','expected_utilisation'),('budget_pacing_pct','expected_pacing')] %}
    or ({{ actual }} is null) <> ({{ expected }} is null)
    or abs({{ actual }} - {{ expected }}) > 0.00000001
    {% endfor %}
    or flag_spend_without_eligible_attributed_orders is distinct from (spend_gbp > 0 and attributed_orders = 0)
    or flag_budget_overspend is distinct from coalesce(expected_utilisation > 100, false)
    or flag_ahead_of_budget_pacing is distinct from coalesce(expected_pacing > 100, false)
    or flag_approaching_budget is distinct from coalesce(expected_utilisation between 90 and 100, false)
    or flag_unexpected_negative_inputs is distinct from (negative_input_count > 0)
    or flag_incomplete_attribution is distinct from (unattributed_placed_orders > 0)
{% endtest %}
