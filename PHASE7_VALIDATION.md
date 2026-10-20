# Phase 7 validation record

Validated locally on 2026-10-20. The live service used authenticated native
Codex CLI, `gpt-6-luna`, low reasoning, and Wren CLI 0.15.0. Its structured
output smoke test passed. No API key was used.

All five questions were uncached. Every result passed the service's full Wren
versus direct DuckDB row, column, order, value and NULL comparison, and a second
independently authored DuckDB query:

| Question | Verified outcome |
| --- | --- |
| What is total marketing spend? | GBP 189,198.54 |
| How did spend and net revenue change by month? | 12 months returned; January GBP 11,150.37 spend and GBP 22,498.00 net revenue. All months matched direct SQL. |
| Which five campaigns generated the highest net revenue? | CAM-0002 GBP 30,385.00; CAM-0001 GBP 29,027.00; CAM-0003 GBP 27,389.00; CAM-0007 GBP 9,531.50; CAM-0015 GBP 8,801.00. |
| Which campaigns spent money without producing eligible conversions? | CAM-0023: GBP 8,665.44, 0 attributed eligible orders; CAM-0024: GBP 3,281.20, 0 orders. |
| Which campaigns exceeded their budgets? | Six campaigns; governed utilisation was 112% for each. Highest spend was CAM-0015, GBP 13,687.52 against a GBP 12,221.00 lifetime budget. |

Detailed responses and exact SQL are in ignored `target/marketing-ai/live-results.json`.

Checks passed:

- Full dbt build and seed, staging, attribution and mart independent validators;
  dbt reported 376 PASS, 0 WARN and 0 ERROR.
- Wren validation: 10 saved questions, all exposed model rows, cube rollups and
  NULL ratios; 27 direct comparisons passed.
- Dashboard Python validator: 25,200 filter combinations passed.
- Existing dashboard Chrome tests: actual WebAssembly parity, 175 channel/campaign
  interactions, keyboard use, hostile labels, mobile/tablet/desktop layouts, and
  missing CDN/snapshot handling. This suite was rerun with the local AI service
  stopped; all ten verified examples remained available.
- Ask AI Chrome tests at 1440, 390 and 320 px: modes, stopped-service behavior,
  question search, suggestions, 500-character limit, explicit filters, escaped
  results, NULLs, empty results, unavailable service, execution errors and timeout.
- Eight service unit tests: injection and SQL policy, invalid filters, filter
  predicate injection resistance, native executable resolution, locked database
  fingerprint, mocked execution, cache reuse/invalidation, timeout, HTTP origin
  rejection and concurrency response.
- `git diff --check` passed. No governed dbt or Wren metric definition changed.

The service deliberately restricts each query to one Wren model. Consequently,
some comparisons that need several models cannot be expressed in a single local
answer. It returns monthly levels rather than month-over-month deltas where the
semantic model has no supported comparison measure. Generated plans can be
rejected or fail Wren compilation; use the displayed assumptions and SQL or
choose a verified example. The data remains a fixed synthetic 2025 snapshot.
