with inputs as (
    select * from (values
      ('zero',0.0,0,0,0,0,0,0,0,0,0,0,0,'platform_media_only'),
      ('missing',10.0,null,null,null,0,0,null,0,0,0,0,0,'platform_media_only'),
      ('positive',100.0,1000,20,10,2,1,1,200,150,1,1,0,'platform_media_only'),
      ('unpaid',0.0,0,0,10,0,0,0,0,0,0,1,0,'not_available')
    ) t(id,spend_gbp,impressions,clicks,valid_sessions,eligible_conversions,attributed_orders,
        attributed_first_observed_acquisitions,attributed_gross_merchandise_revenue_gbp,
        attributed_net_revenue_gbp,unattributed_placed_orders,negative_input_count,unused,cost_coverage)
), actual as (
    select *, {{ marketing_mart_ratios('channel', '100.0 * spend_gbp / nullif(0, 0)', '100.0 * spend_gbp / nullif(0, 0)') }}
    from inputs
)
select * from actual where
    (id in ('zero','missing') and (ctr_pct is not null or cpc_gbp is not null or conversion_rate_pct is not null
        or media_only_cac_gbp is not null or attribution_rate_pct is not null))
    or (id='zero' and (gross_roas is not null or net_roas is not null))
    or (id='missing' and (gross_roas<>0 or net_roas<>0))
    or (id='unpaid' and (gross_roas is not null or net_roas is not null or media_only_cac_gbp is not null or conversion_rate_pct is not null))
    or budget_utilisation_pct is not null or budget_pacing_pct is not null
    or flag_budget_overspend or flag_ahead_of_budget_pacing or flag_approaching_budget
    or (id='positive' and (ctr_pct<>2 or cpc_gbp<>5 or conversion_rate_pct<>10
        or gross_roas<>2 or net_roas<>1.5 or media_only_cac_gbp<>100 or attribution_rate_pct<>50
        or not flag_incomplete_attribution or not flag_unexpected_negative_inputs))
