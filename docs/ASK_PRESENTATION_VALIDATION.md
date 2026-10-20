# Ask Marketing AI presentation validation

Validated 20 October 2026.

Changed for this task:
- docs/answer.mjs: business labels, unit formatting, scalar KPI, multi-value summary/table, collapsed execution provenance.
- docs/ask.mjs: uses the answer renderer.
- docs/styles.css: answer card, table and responsive detail styles.
- scripts/marketing_ai.py: adds presentation units from validated SQL projections, including aliases; removes raw first-row answer text. Generation, governance, Wren execution, independent parity and cache boundaries are preserved.
- scripts/test_answer.mjs: formatter and renderer unit coverage.
- scripts/test_marketing_ai.py: response metadata and alias unit coverage.
- scripts/test_marketing_ai_browser.py: layout, formats, disclosure, injection and screenshot coverage while retaining existing UI checks.
- README.md: documents presentation, tests and screenshot fixtures.
- docs/assets/screenshots/ask-kpi-1440.png, ask-kpi-390.png, ask-table-1440.png, ask-table-390.png: deterministic browser fixtures, not live AI outputs.

Results:
- node --test scripts/test_answer.mjs: PASS, 3 tests.
- .venv/Scripts/python.exe -B scripts/test_marketing_ai.py: PASS, 13 tests. Error log output is expected from timeout/error-path tests.
- .venv/Scripts/python.exe -B scripts/validate_dashboard.py: PASS, existing JS formatting/NULL/escaping/reconciliation checks and 25,200 filter combinations against independent direct SQL.
- .venv/Scripts/python.exe -B scripts/test_marketing_ai_browser.py: PASS, installed Chrome; saved-example/offline modes, filters, errors, currency/percent/ROAS/count/date formatting, NULL/zero, scalar/table layouts, collapsed details, escaping, 1440/390/320px overflow checks. Four screenshots refreshed.
- .venv/Scripts/python.exe -B scripts/test_dashboard_browser.py: ATTEMPTED, blocked at initial engine load because https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm could not be reached. Direct curl also failed to connect. Dashboard browser assertions after startup could not run; this suite is not reported as passing.
- node --check docs/ask.mjs and docs/answer.mjs: PASS.
- git diff --check: PASS.

No live Codex/Wren requests were made for this presentation change. Existing workspace edits were preserved. No commit or push was performed.
