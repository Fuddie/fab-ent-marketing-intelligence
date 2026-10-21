> Historical restricted-environment audit. Superseded by [the final release assessment](../RELEASE_READINESS.md), including successful escalated browser and service checks.

# Production-readiness audit — 20 October 2026

**Verdict: release sign-off blocked.** Fresh checks establish the governed data
and semantic path, but this environment cannot complete live AI generation or
the dashboard's WebAssembly startup. Earlier PASS reports do not override these
current failures. This is a fixed synthetic portfolio snapshot with a loopback
AI service, not an internet-facing AI deployment.

## Corrections

- Monthly ranking questions go through structured planning, including their date,
  entity, metric and exclusion constraints. Removed the working-tree keyword
  shortcut that could ignore those constraints and bypass AI interpretation.
- Monthly window rankings can return up to 1,200 rows instead of silently losing
  later months to the ordinary 100-row cap. Ordinary queries retain that cap;
  explicit `LIMIT 0` stays empty. Ranking SQL and scope predicates use the same
  validation/execution path as other questions. Business tie breakers remain in
  the generated SQL, visible for review.
- SQL validation rejects summing/averaging stored ratios and daily non-additive
  lifetime/cumulative measures. These errors can otherwise pass execution parity
  while producing an invalid business metric.
- Wren validation evidence and exported snapshots now carry a governed source
  digest. Exports require matching validation evidence and record the compiled
  model digest. The AI service checks the Wren version, explicit connection,
  source/build digests, snapshot checksums, physical schemas and every row of all
  five marts against browser exports. It checks before cache access and after
  execution; divergence withholds the answer. No live database files are hashed.
  Money/counts/NULLs remain exact; floating ratios retain the documented absolute
  `1e-8` / relative `1e-10` tolerances used by the Wren exporter.
- Cache fingerprints now include the compiled Wren model, connection, snapshot
  manifest, parity oracle and snapshot-check implementation. Answer details
  describe the ordinary and monthly row caps.

## Fresh results

| Boundary | Result |
| --- | --- |
| Full dbt build, including seeds, data and unit tests | PASS: 387, zero warnings/errors/skips |
| Independent seed, staging, attribution and mart CSV validators | PASS: all four |
| Wren strict context validation/build | PASS: five models, no relationships |
| Wren versus direct DuckDB | PASS: 32 comparisons |
| Regenerated exports | PASS: five Parquet files, four dashboard queries, 11 saved answers |
| Dashboard calculation functions versus direct SQL | PASS: all 25,200 filter combinations after re-export |
| Monthly ranking regressions | PASS: native and actual Wren execution; scoped rankings and all 112 campaign-month rows |
| AI policy/HTTP tests | PASS: 16 tests; model/execution responses mocked |
| Snapshot drift regressions | PASS: three tests covering source/build/checksum, database row/NULL and connection drift |
| Answer presentation | PASS: five Node tests |
| Ask AI browser suite | PASS: Chrome desktop/mobile, service responses mocked |
| Campaign monthly browser suite | PASS: Chrome desktop/mobile, deterministic fixtures |
| Dependency consistency | PASS: `pip check` |
| Full dashboard browser suite | BLOCKED: pinned CDN module fetch fails |
| Live AI startup and question generation | BLOCKED: native Codex startup fails with Windows access denied |

The new readiness check also passed against the actual rebuilt DuckDB database,
compiled Wren model and regenerated browser snapshots. The static HTTP server
successfully serves the UI and saved examples. Mocked UI checks do not establish
live model availability, SQL interpretation quality or WebAssembly execution.

## Release blockers

1. Chrome cannot import
   `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm`.
   A direct `curl` connection to that host also fails. The dashboard correctly
   shows its error state without invented KPI values. Restore CDN connectivity
   or provide a complete, version-pinned self-hosted WebAssembly distribution
   before claiming successful browser analytics execution. That distribution
   must include the module, workers, WASM and required extension dependencies.
2. The service reaches its real native Codex probe, which fails with
   `failed to initialize in-process app-server client: Access is denied. (os error 5)`.
   Wren and snapshot readiness pass before the probe. Native runtime warnings
   also report denied access under the local Codex temporary directory. The
   restricted audit environment cannot repair those permissions. No live AI
   question suite passed in this audit.

After resolving these environment failures, run the following from the repository
root. Use the documented local dashboard and AI services for the browser/live tests.
Stop on any failed command; do not reuse earlier success evidence.

```powershell
.\.venv\Scripts\python.exe -B scripts/validate_wren.py --wren-exe $env:WREN_EXE
.\.venv\Scripts\python.exe -B scripts/export_dashboard.py --wren-exe $env:WREN_EXE
.\.venv\Scripts\python.exe -B scripts/governed_snapshot.py
.\.venv\Scripts\python.exe -B scripts/validate_dashboard.py
.\.venv\Scripts\python.exe -B scripts/test_marketing_ai.py
.\.venv\Scripts\python.exe -B scripts/test_governed_snapshot.py
.\.venv\Scripts\python.exe -B scripts/test_monthly_top_n.py --wren
node --test scripts/test_answer.mjs
.\.venv\Scripts\python.exe -B scripts/test_dashboard_browser.py
.\.venv\Scripts\python.exe -B scripts/test_marketing_ai_browser.py
.\.venv\Scripts\python.exe -B scripts/test_campaign_monthly_browser.py
.\.venv\Scripts\python.exe -B scripts/test_marketing_ai_live.py
.\.venv\Scripts\python.exe -B scripts/test_campaign_monthly.py --live
git diff --check
```

## Remaining limits

Execution parity does not prove arbitrary natural-language interpretation or
every possible metric composition. Inspect assumptions and SQL; expand the live
question corpus before release. The new SQL guards reject specific invalid
aggregation classes, not every conceivable incorrect formula. Local source and
snapshot hashes provide consistency checks, not signed artifact provenance.
Concurrent source/database rebuilds should not run while serving questions.
The public site still relies on external CDN availability; the local AI service
still requires the user's authenticated native Codex installation. No metric
definitions, attribution rules, raw CSVs or public hosting settings changed.
