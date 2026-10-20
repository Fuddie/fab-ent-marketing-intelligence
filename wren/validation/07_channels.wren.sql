SELECT marketing_channel, cost_coverage, SUM(spend_gbp) AS spend_gbp, SUM(valid_sessions) AS valid_sessions, SUM(attributed_orders) AS attributed_orders, SUM(net_revenue_gbp) AS net_revenue_gbp,
100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0) AS ctr_pct,
SUM(spend_gbp) / NULLIF(SUM(clicks), 0) AS cpc_gbp,
CASE WHEN cost_coverage = 'platform_media_only' THEN 100.0 * SUM(attributed_orders) / NULLIF(SUM(valid_sessions), 0) END AS conversion_rate_pct,
CASE WHEN cost_coverage = 'platform_media_only' THEN SUM(attributed_net_revenue_gbp) / NULLIF(SUM(spend_gbp), 0) END AS net_roas,
CASE WHEN cost_coverage = 'platform_media_only' THEN SUM(spend_gbp) / NULLIF(SUM(attributed_first_observed_acquisitions), 0) END AS media_only_cac_gbp
FROM MarketingChannelMonthly GROUP BY marketing_channel, cost_coverage ORDER BY marketing_channel ASC;
