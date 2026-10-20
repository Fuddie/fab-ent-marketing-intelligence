{% macro marketing_mart_sum_columns() %}
sum(spend_gbp) as spend_gbp,
sum(impressions) as impressions,
sum(clicks) as clicks,
sum(valid_sessions) as valid_sessions,
sum(placed_orders) as placed_orders,
sum(attributed_placed_orders) as attributed_placed_orders,
sum(unattributed_placed_orders) as unattributed_placed_orders,
sum(eligible_conversions) as eligible_conversions,
sum(attributed_orders) as attributed_orders,
sum(unattributed_eligible_orders) as unattributed_eligible_orders,
sum(first_observed_acquisitions) as first_observed_acquisitions,
sum(attributed_first_observed_acquisitions) as attributed_first_observed_acquisitions,
sum(unattributed_first_observed_acquisitions) as unattributed_first_observed_acquisitions,
sum(raw_gross_order_amount_gbp) as raw_gross_order_amount_gbp,
sum(cancellation_gross_amount_gbp) as cancellation_gross_amount_gbp,
sum(gross_merchandise_revenue_gbp) as gross_merchandise_revenue_gbp,
sum(sales_refunds_gbp) as sales_refunds_gbp,
sum(cancellation_reversals_gbp) as cancellation_reversals_gbp,
sum(net_revenue_gbp) as net_revenue_gbp,
sum(raw_net_order_amount_gbp) as raw_net_order_amount_gbp,
sum(attributed_gross_merchandise_revenue_gbp) as attributed_gross_merchandise_revenue_gbp,
sum(unattributed_gross_merchandise_revenue_gbp) as unattributed_gross_merchandise_revenue_gbp,
sum(attributed_sales_refunds_gbp) as attributed_sales_refunds_gbp,
sum(unattributed_sales_refunds_gbp) as unattributed_sales_refunds_gbp,
sum(attributed_cancellation_reversals_gbp) as attributed_cancellation_reversals_gbp,
sum(unattributed_cancellation_reversals_gbp) as unattributed_cancellation_reversals_gbp,
sum(attributed_net_revenue_gbp) as attributed_net_revenue_gbp,
sum(unattributed_net_revenue_gbp) as unattributed_net_revenue_gbp,
sum(allocated_budget_gbp) as allocated_budget_gbp,
sum(negative_input_count) as negative_input_count
{% endmacro %}

{% macro marketing_mart_ratios(scope, utilisation, pacing) %}
    100.0 * clicks / nullif(impressions, 0) as ctr_pct,
    spend_gbp / nullif(clicks, 0) as cpc_gbp,
    {% if scope == 'overview' %}
    100.0 * eligible_conversions / nullif(valid_sessions, 0) as conversion_rate_pct,
    {% else %}
    case when cost_coverage = 'platform_media_only' then
        100.0 * attributed_orders / nullif(valid_sessions, 0) end as conversion_rate_pct,
    {% endif %}
    {% if scope == 'channel' %}case when cost_coverage = 'platform_media_only' then{% endif %}
    attributed_gross_merchandise_revenue_gbp / nullif(spend_gbp, 0)
    {% if scope == 'channel' %}end{% endif %} as gross_roas,
    {% if scope == 'channel' %}case when cost_coverage = 'platform_media_only' then{% endif %}
    attributed_net_revenue_gbp / nullif(spend_gbp, 0)
    {% if scope == 'channel' %}end{% endif %} as net_roas,
    {% if scope == 'channel' %}case when cost_coverage = 'platform_media_only' then{% endif %}
    spend_gbp / nullif(attributed_first_observed_acquisitions, 0)
    {% if scope == 'channel' %}end{% endif %} as media_only_cac_gbp,
    100.0 * attributed_orders / nullif(eligible_conversions, 0) as attribution_rate_pct,
    {{ utilisation }} as budget_utilisation_pct,
    {{ pacing }} as budget_pacing_pct,
    spend_gbp > 0 and attributed_orders = 0 as flag_spend_without_eligible_attributed_orders,
    coalesce(({{ utilisation }}) > 100, false) as flag_budget_overspend,
    coalesce(({{ pacing }}) > 100, false) as flag_ahead_of_budget_pacing,
    coalesce(({{ utilisation }}) between 90 and 100, false) as flag_approaching_budget,
    negative_input_count > 0 as flag_unexpected_negative_inputs,
    unattributed_placed_orders > 0 as flag_incomplete_attribution
{% endmacro %}
