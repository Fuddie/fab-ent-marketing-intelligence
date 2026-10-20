# Marketing semantic project

This isolated Wren CLI 0.15.0 project reads the five governed dbt marts.
Setup and validation commands are in the [root README](../README.md#phase-5-wren-semantic-layer).
The repository root remains exclusively the dbt project; Wren YAML lives here.

`models/*/metadata.yml` preserves every physical mart column, with descriptions
from the governed schemas, readable display names, normalized observed types,
GBP currency metadata, dates, boolean flags and aggregation guidance.
Composite-grain models add a calculated `grain_key`; this does not change grain.
Physical mappings are exactly catalog `fab_ent`, schema `raw_marts`, and
`mart_marketing__campaign_daily`, `mart_marketing__campaign_monthly`, `mart_marketing__campaign_summary`,
`mart_marketing__channel_monthly`, `mart_marketing__monthly_overview`.
Internal Wren namespace is `wren.public`, independent of the physical namespace.

`cubes/*/metadata.yml` defines five matching `Marketing…Metrics` cubes. Additive
measure names start with `total_`; ratios use `ctr_pct`, `cpc_gbp`,
`conversion_rate_pct`, `gross_roas`, `net_roas`, `media_only_cac_gbp`,
`attribution_rate_pct`, `budget_utilisation_pct` and `budget_pacing_pct`.
All ratios divide aggregated components. The daily cube omits budget ratios
because cumulative daily utilisation/pacing cannot roll up safely. Query their
documented row columns at exact campaign/date grain. Budgets and cumulative
amounts are never summed across daily rows. Flags are row-level dimensions.
`properties.aggregation`, `semantic_role`, `currency` and `displayName` document
intent; they are metadata, not SQL access controls. Native cube expressions
implement aggregation semantics. Arbitrary SQL can still misuse model columns.

No relationships, raw-source models, dashboard, service, cloud profile, memory
index or natural-language endpoint are created. Explicit `--mdl` and
`--connection-file` flags prevent the user's global Jaffle profile being used.
The installed connector discovers DuckDB files in `url` (a directory, not a
database filename), then attaches them READ_ONLY using filename-stem aliases.
Use a directory containing only the intended database. MDL is not an authorization
boundary: this is a trusted local CLI workflow.

Authoritative inspected local sources: `wren --version`, `wren --help`,
`wren context --help`, `wren context build --help`, `wren query --help`,
`wren cube query --help`, bundled `skills_content/generate-mdl/SKILL.md`,
`skills_content/usage/references/wren-sql.md`, and installed `context.py`,
`cli.py`, `cube_cli.py`, `connector/duckdb.py`, connection models and type mapper.
The Jaffle example informed directory structure only. Installed behaviour
confirmed that additive cube names must differ from source-column names to
avoid measure dependency cycles, and Windows needs UTF-8 CLI output.

Read [business rules](knowledge/rules/marketing.md) and
[validation evidence](validation/README.md) before writing queries.

Campaign-month evidence and limitations: [monthly validation](../docs/CAMPAIGN_MONTHLY_VALIDATION.md).
