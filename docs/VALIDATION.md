# Query and validation contract

The dashboard has four fixed business SQL queries in `queries.json`. No filter
value changes SQL. DuckDB WebAssembly executes those queries against exported
Wren model outputs; `metrics.mjs` then selects additive result rows and divides
summed numerators by summed denominators. No stored row ratio participates.

| Query | Intended Wren model | Result grain | Filter use |
| --- | --- | --- | --- |
| campaigns | MarketingCampaignDaily | London month + campaign + name + channel | Campaign selection, campaign tables/rankings/alerts |
| channels | MarketingChannelMonthly | London month + channel | Channel selection and comparisons |
| overview | MarketingMonthlyOverview | London month | Website cards/trends; date-only attribution context |
| inventory | MarketingCampaignSummary | Campaign | Filter choices and labelled lifetime context, ignoring dates |

The registration DDL is also recorded in the manifest. It creates one local view
per allowlisted snapshot and has no Wren semantic-query equivalent. It performs
no joins or business calculations. Marts are never joined to one another.

`scripts/export_dashboard.py` executes each fixed query through Wren CLI 0.15.0,
compares it with direct SQL against the intended governed physical mart, and
compares its execution over the typed exported snapshot. Complete Wren model
outputs are also checked row by row. Snapshot values come from Wren responses,
not from an independently fabricated browser dataset. The ten verified answers
are re-executed and compared with their saved direct SQL references on export.

`scripts/validate_dashboard.py` checks every combination of the actual filter
controls: 12 start months, 12 end months, seven channel choices including All,
and 25 campaign choices including All: **25,200 combinations**. Reversed ranges
and incompatible dimensions are included. The same JS functions imported by the
dashboard run under Node, and their results are compared with independent SQL
over physical marts. This covers cards, monthly/channel/campaign tables, top-five
ordering, alerts and date-only website context. Fixed SQL is validated in Wren;
filter selection and calculations are tested exhaustively against native DuckDB.
There is no claim that Wren receives 25,200 dynamically generated browser queries.

Source counts are exact, as are booleans, strings, NULL positions and fixed-scale
decimal amounts in Wren export comparisons. Calculated DOUBLE values, allocated
budgets and browser numeric reductions satisfy:

```
abs(actual - expected) <= max(1e-8, 1e-10 * max(abs(actual), abs(expected)))
```

No rounding precedes comparison. Empty aggregates remain NULL and display N/A.
Real zero money displays £0.00. Counts remain integers; Parquet count portability
uses range-checked BIGINT instead of unsupported signed INT128. Dimension results
sort by complete ascending keys. Top campaigns sort by net ROAS descending, NULL
last, then campaign ID ascending. Ranking and alerts are re-evaluated per scope.

`scripts/test_dashboard_browser.py` uses real installed Chrome with pinned
Playwright 1.56.0 over a local HTTP server. It compares actual browser-engine
query outputs with native results, exercises all 175 channel/campaign pairs,
keyboard controls, empty/NULL states, unsafe labels, desktop/mobile/tablet
rendering and missing-CDN/missing-snapshot failures. Screenshots are stored in
`assets/screenshots/`. Runtime error checks never substitute cached KPI answers.

Machine-readable evidence: `snapshot.json`, `validation.json`, and
`browser-validation.json`. Intermediate detailed results stay in ignored
`target/dashboard/`, and Wren execution evidence stays in ignored `wren/target/`.
Commands and snapshot limitations are in the root README.
