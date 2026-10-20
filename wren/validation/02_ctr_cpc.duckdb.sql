SELECT 100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0) AS ctr_pct, SUM(spend_gbp) / NULLIF(SUM(clicks), 0) AS cpc_gbp FROM "fab_ent"."raw_marts"."mart_marketing__monthly_overview";
