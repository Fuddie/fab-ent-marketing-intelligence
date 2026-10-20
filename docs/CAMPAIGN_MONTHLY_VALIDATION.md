# Campaign-month validation

Exact question: **Top three campaigns based on revenue generation per month**.

Implemented `MarketingCampaignMonthly` at Europe/London month/campaign grain. Revenue generation defaults to attributed net revenue; campaign ID ascending breaks ties. Result: 36 rows, exactly three per month. All 112 monthly rows reconcile to independent Python accumulation of governed daily data. Revenue eligibility and reporting time zone definitions are preserved.

Passed: full dbt build (387 nodes: 359 data tests, four unit tests, 17 models, seven seeds), seed/staging/attribution/mart validators, monthly oracle and ranking/filter/tie checks, 14 AI policy tests, four presentation tests, all 25,200 dashboard filter combinations. Chromium checked Reporting month, 36 rows, and overflow at 1440px and 390px.

**Completed 2026-10-20 using the existing `WREN_EXE` (Wren 0.15.0):** strict context validation/build (five models, no relationships), all 32 semantic/direct DuckDB comparisons including native cubes and the exact 36-row monthly ranking. Refreshed all five typed Parquet exports (112 + 3,022 + 24 + 72 + 12 = 3,242 rows), snapshot and query manifests, and all 11 saved verified answers. Every export passed Wren/direct/typed-Parquet parity. All four fixed queries and 25,200 filter combinations passed. Both CLI scripts now honor `WREN_EXE` by default; the snapshot validator requires all five models.

**Browser results:** Ask UI suite passed. Monthly suite passed against the actual saved dashboard answer and the answer renderer at 1440px/390px: 36 rows, Reporting month, no overflow. Monthly screenshots now use saved Wren output and identify it as a saved answer, not a live AI response.

**Remaining limitations:** Full dashboard browser suite failed at fetching the pinned jsDelivr DuckDB-Wasm module; WASM parity and subsequent interaction assertions were not reached this run. Local AI startup failed its real Codex configuration probe: `failed to initialize in-process app-server client: Access is denied (os error 5)`. Both live suites were attempted and received connection refused; no uncached AI answer is claimed. Governed context and snapshot inputs are refreshed for local AI. No Wren installation, commit or push.

## Monthly result

| Reporting month | Campaign ID | Attributed net revenue (GBP) |
|---|---|---:|
| 2025-01 | CAM-0003 | 2,729.50 |
| 2025-01 | CAM-0020 | 2,669.00 |
| 2025-01 | CAM-0012 | 2,523.00 |
| 2025-02 | CAM-0008 | 3,373.50 |
| 2025-02 | CAM-0004 | 2,980.50 |
| 2025-02 | CAM-0016 | 2,899.00 |
| 2025-03 | CAM-0002 | 4,341.00 |
| 2025-03 | CAM-0001 | 4,176.00 |
| 2025-03 | CAM-0020 | 3,448.00 |
| 2025-04 | CAM-0002 | 3,396.50 |
| 2025-04 | CAM-0003 | 2,642.50 |
| 2025-04 | CAM-0021 | 2,444.00 |
| 2025-05 | CAM-0013 | 3,328.00 |
| 2025-05 | CAM-0009 | 2,497.00 |
| 2025-05 | CAM-0003 | 2,491.00 |
| 2025-06 | CAM-0001 | 3,828.50 |
| 2025-06 | CAM-0005 | 3,504.00 |
| 2025-06 | CAM-0002 | 3,343.50 |
| 2025-07 | CAM-0018 | 2,802.00 |
| 2025-07 | CAM-0014 | 2,382.50 |
| 2025-07 | CAM-0001 | 2,370.00 |
| 2025-08 | CAM-0022 | 2,748.00 |
| 2025-08 | CAM-0010 | 2,675.00 |
| 2025-08 | CAM-0002 | 2,605.00 |
| 2025-09 | CAM-0022 | 3,696.50 |
| 2025-09 | CAM-0018 | 2,628.00 |
| 2025-09 | CAM-0003 | 2,500.00 |
| 2025-10 | CAM-0015 | 3,623.50 |
| 2025-10 | CAM-0003 | 3,480.50 |
| 2025-10 | CAM-0007 | 3,049.00 |
| 2025-11 | CAM-0011 | 4,151.50 |
| 2025-11 | CAM-0002 | 3,916.50 |
| 2025-11 | CAM-0001 | 3,597.00 |
| 2025-12 | CAM-0007 | 4,089.50 |
| 2025-12 | CAM-0011 | 3,012.50 |
| 2025-12 | CAM-0019 | 2,788.00 |

Full names and SQL: [result evidence](campaign-monthly-validation.json). Screenshots: [desktop](assets/screenshots/ask-campaign-monthly-1440.png), [mobile](assets/screenshots/ask-campaign-monthly-390.png).

## Files changed for this task

- dbt: `models/marts/marketing/mart_marketing__campaign_monthly.sql`, `_marketing__marts.yml`; `tests/marts/assert_campaign_monthly_reconciliation.sql`.
- Wren: `models/MarketingCampaignMonthly/metadata.yml`, `cubes/MarketingCampaignMonthlyMetrics/metadata.yml`, `knowledge/rules/marketing.md`, `validation/11_top_campaigns_monthly.{wren,duckdb}.sql`, `validation/cases.json`, both README files.
- Service/validation: `scripts/marketing_ai.py`, `validate_wren.py`, `export_dashboard.py`, `validate_dashboard.py`, `test_marketing_ai.py`, `test_answer.mjs`, `test_marketing_ai_browser.py`, `test_dashboard_browser.py`; new `test_campaign_monthly.py`, `test_campaign_monthly_browser.py`, `monthly_preview.mjs`.
- UI: `docs/app.mjs` accepts the fifth model when a validated export exists; existing renderer labels `reporting_month` as Reporting month.
- Documentation/evidence: `METRIC_CONTRACT.md`, root `README.md`, this file, `campaign-monthly-validation.json`, two monthly screenshots.

Pre-existing workspace changes were retained. No commit or push.
