# Release readiness

Final audit of the uncommitted portfolio working tree, 21 October 2026. No commit, push or hosting change was made. The snapshot is synthetic and fixed to 2025; this assessment covers the static dashboard and the optional loopback question service.

## Result and evidence

Fresh evidence: [complete expected and actual rows](docs/release-acceptance.json), [snapshot manifest](docs/snapshot.json), [dashboard calculations](docs/validation.json), and [browser checks](docs/browser-validation.json). Runtime logs remain under ignored `target/`. Earlier restricted-environment failures were retried with approved access: Codex startup, CDN access and Windows child-process termination work outside that sandbox. Historical reports do not supersede this run.

| Check | Final result |
| --- | --- |
| dbt build | 387 successful nodes, zero warnings/errors/skips: 7 seeds, 17 models, 359 data tests and 4 unit tests |
| Independent data validation | Raw validator plus seed, staging, attribution and mart CSV oracles pass |
| Wren strict context validation/build and compiled MDL | PASS; CLI 0.15.0; all five governed models, no relationships |
| Semantic/direct DuckDB parity | 32 validation comparisons pass; 14 acceptance cases also pass |
| Exports | Five governed Parquet files, 3,242 rows, four fixed dashboard queries and 11 saved answers; schemas, values, NULLs, source/MDL digests and SHA-256 checksums pass |
| Dashboard filters | All 25,200 combinations pass independent SQL comparison |
| Application tests | 17 policy/HTTP tests + 3 snapshot-drift tests + 6 ranking/intent tests = 26 Python unit tests; 6 Node presentation tests; separate campaign-month validation passes |
| Live questions | Ten exact uncached questions; three negative HTTP cases; three additional campaign-month phrasings |
| Browsers | Four executable Chrome suites pass; assertions are suite scripts, not individually counted test cases |
| Dependencies | pip check passes |

## Analytical acceptance matrix

Every supported case has a separately computed expected answer from read-only physical DuckDB marts. Ranking uses Python sorting of independently read rows; campaign-month validation also rebuilds results from daily rows. Wren executes the governed semantic query. Comparison checks row count, column names/order, grain keys, exact decimal money/counts, NULLs, values and sequence; floating ratios use absolute 1e-8 / relative 1e-10 tolerance. Every live answer is also checked by the service against a separately timed DuckDB execution.

| Exact regression question | Expected rows | Wren rows | Live result |
| --- | ---: | ---: | --- |
| What is total marketing spend? | 1 | 1 | PASS  |
| How did spend and attributed net revenue change by month? | 12 | 12 | PASS  |
| Which five campaigns generated the highest attributed net revenue overall? | 5 | 5 | PASS  |
| Top three campaigns based on attributed net revenue per month. | 36 | 36 | PASS  |
| Top three channels based on attributed net revenue per month. | 36 | 36 | PASS  |
| Which channel had the strongest net ROAS per month? | 12 | 12 | PASS  |
| Which campaigns spent money without producing eligible conversions? | 2 | 2 | PASS  |
| Which campaigns exceeded their budgets? | 6 | 6 | PASS  |
| What percentage of eligible outcomes was unattributed? | 1 | 1 | PASS  |
| How many first-observed acquisitions came from each channel? | 6 | 6 | PASS  |

Additional deterministic cases: channel comparisons with recomputed ROAS (six rows, including zero-denominator NULLs); March-May channel scope applied before campaign ranking (eight rows: 3/3/2); empty aggregate (one NULL); and empty result (zero rows). All pass. Scalar spend is GBP 189,198.54; budget exceptions contain six campaigns; spend without eligible conversions contains CAM-0023 and CAM-0024. Unattributed eligible outcomes are 789 / 2,228 = 35.412926...%; channel acquisition totals reconcile to 1,174.

## Monthly top-N evidence

The shared SQL boundary normalizes valid monthly ROW_NUMBER/RANK/DENSE_RANK plans to deterministic ROW_NUMBER semantics, keeps WHERE filters before ranking, exposes monthly_rank, enforces a 1-100 per-group bound and rejects a global LIMIT supplied by the planner. Rank = 1 is accepted as the equivalent top-one case. Output sorts by reporting_month, then monthly_rank. A generic monthly-intent check validates the requested bound before execution; a violated contract gets at most one planning repair within the original deadline, preserving the selected model and requiring the original scope. No question string has a canned SQL response.

| Entity | Expected / actual rows | Months | Rows per month | Maximum rank | Fourth-ranked entity |
| --- | --- | ---: | ---: | ---: | --- |
| MarketingCampaignMonthly | 36 / 36 | 12 | 3 | 3 | None |
| MarketingChannelMonthly | 36 / 36 | 12 | 3 | 3 | None |

Both live monthly top-three questions match the independently ranked DuckDB result, including rank and column order. Each returns exactly 36 rows for 12 months, three per month, maximum rank 3, and no fourth entity. Campaign output includes campaign_name; both return reporting_month then monthly_rank ordering. Reusable regressions cover N=1,3,5,100, all 112 campaign-month rows, filtered groups and a four-way metric tie where entity-name ordering retains only ranks 1-3.

## Operational and security acceptance

| Category | Expected and observed result | Evidence |
| --- | --- | --- |
| Unsupported / malformed questions | Unsupported weather question, empty question and malformed JSON each return HTTP 400; no fabricated answer | Live matrix negative cases |
| Read-only SQL and routing | Reject writes, multi-statements, comments, joins, CTEs, nested queries, raw tables, external functions and invalid scope; allow all five models including MarketingCampaignMonthly | Policy tests; Wren execution |
| NULL / zero denominators | Undefined ROAS/CAC and empty sums remain NULL; real zero remains zero; browser displays N/A or GBP 0.00 appropriately | Matrix, dashboard and presentation tests |
| Timeout | Real sleeping child is terminated within five seconds with a 0.2-second test deadline; HTTP 504 and browser timeout states are injected deterministically | test_deadline, HTTP and browser tests |
| Stale cache | Changed fingerprints regenerate answers; readiness is checked before cache hits; source/build/checksum/connection/database-row drift blocks answers | Policy and three drift tests |
| Service unavailable / failure | Not-ready HTTP 503, safe execution error HTTP 500, busy HTTP 409, denied Host/Origin, offline browser message; detailed diagnostics stay local | HTTP tests, local log checks and browser suites |
| Database fingerprint | Explicit governed source/build hashes plus read-only schema and full-row parity against exports; no live database-file hashing | governed_snapshot.py, drift tests |
| Startup / shutdown / duplicates | Real Codex probe succeeds; one listener per dashboard/service port while running; owned services stopped after tests, neither port remains listening | Health, netstat and process-session checks |
| Repository hygiene | No tracked credentials/authentication, secret-key patterns, personal paths, databases, logs, caches, dbt targets or local Wren artifacts; sensitive runtime paths are ignored | Git inventory, text scan, git check-ignore |

HTTP failure cases and local UI responses are intentionally injected; supported analytical questions use real Wren and, in the live matrix, real authenticated Codex generation. The timeout test exercises a real child process; it does not deliberately consume the full 90-second model deadline. Sandbox taskkill denial was an explained environment failure; the approved final test passes. This is a trusted local service, not an internet-facing multi-user SQL gateway.

## Browser and public/local behaviour

Four final suites: dashboard WebAssembly parity and 175 channel/campaign interactions at widths 1440/768/390/320; Local questions at 1440/390/320 with deterministic UI fixtures; saved monthly rankings at 1440/390; and an isolated public HTTPS origin at 1440/390 with CDN unavailable. Tests cover GBP, percentages, ROAS, counts, months/dates, readable labels, scalar KPI cards, multi-row summary/tables, collapsed SQL/metadata, keyboard controls, focus styling, labelled controls, escaped hostile text, loading/empty/failure states and document overflow.

The public-origin test confirms saved examples remain usable without the engine or local service and makes zero localhost requests. Local questions display an explicit local-only message there. The public dashboard itself needs the pinned CDN/extension distribution but no localhost backend. Both README public URLs returned HTTP 200. These checks validate the working tree; the final changes have not been published to the existing hosted site.

## README claims verified

The rewritten README follows the requested narrative order, uses valid UTF-8 and retains limitations. Verified against current files/evidence: five governed models: MarketingCampaignDaily (3,022 rows), MarketingCampaignMonthly (112), MarketingCampaignSummary (24), MarketingChannelMonthly (72), and MarketingMonthlyOverview (12); 359 data + four unit tests; 11 saved examples; 25,200 filter combinations; both monthly top-three behaviours; seven source datasets and their row counts; GBP totals; acquisition and eligibility totals; architecture; default gpt-6-luna/low service configuration; current commands, relative paths and public/local scope. Both public URLs return HTTP 200. The existing compatible Wren executable was selected through WREN_EXE; the README installs an equivalent project-local environment.

Twelve internal Markdown links resolve; one H1 and 13 H2 sections follow the requested hierarchy; tables have consistent columns and code fences balance. No mojibake, personal paths, obsolete model/example counts, assistant references or internal task language remain in README. The Wren guide link was corrected. git diff --check passes. The security scan is a pattern/inventory check, not a forensic scan of Git history.

## Exact test commands

Run from the repository root. Set WREN_EXE to the compatible Wren CLI 0.15.0 executable; Windows tests require permission to launch Chrome/Codex and terminate their own child processes. The first validation command runs dbt build and the four CSV oracles before strict Wren validation/build and 32 comparisons.

```powershell
.\.venv\Scripts\python.exe -u -B scripts/validate_wren.py --wren-exe $env:WREN_EXE
.\.venv\Scripts\python.exe -u -B scripts/export_dashboard.py --wren-exe $env:WREN_EXE
.venv/Scripts/python.exe -B scripts/validate_raw_data.py
.venv/Scripts/python.exe -B scripts/governed_snapshot.py
.venv/Scripts/python.exe -B scripts/validate_dashboard.py
.venv/Scripts/python.exe -B scripts/test_marketing_ai.py
.venv/Scripts/python.exe -B scripts/test_governed_snapshot.py
.venv/Scripts/python.exe -B scripts/test_monthly_top_n.py --wren
.venv/Scripts/python.exe -B scripts/test_campaign_monthly.py
.venv/Scripts/python.exe -B scripts/acceptance_matrix.py
node --test scripts/test_answer.mjs
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -B scripts/test_dashboard_browser.py
.venv/Scripts/python.exe -B scripts/test_marketing_ai_browser.py
.venv/Scripts/python.exe -B scripts/test_campaign_monthly_browser.py
.venv/Scripts/python.exe -B scripts/test_public_browser.py
.\.venv\Scripts\python.exe -m http.server 4173 --bind 127.0.0.1 --directory docs
.\.venv\Scripts\python.exe -B scripts/marketing_ai.py
.\.venv\Scripts\python.exe -u -B scripts/test_marketing_ai_live.py
.\.venv\Scripts\python.exe -u -B scripts/test_campaign_monthly.py --live
git diff --check
git status --short
```

The live script calls the shared matrix in live mode, clears the service cache and repeats all ten exact questions. The three additional phrasings run afterwards. Use separate terminals for the two foreground services and Ctrl+C to stop them. Detailed final command exit codes are recorded in the linked acceptance JSON; local stdout/stderr are under target/final-*.log. README link/encoding/hygiene checks used Python pathlib/re/json and the git ls-files inventory; public link checks used curl.exe -I -L --max-time 20 for each of the two HTTPS URLs.

## Changed files

The audit began with existing uncommitted changes, which were preserved and validated. This is the complete final working-tree change inventory, including regenerated evidence and screenshots:

- `.gitignore`
- `README.md`
- `RELEASE_READINESS.md`
- `docs/PRODUCTION_READINESS_AUDIT.md`
- `docs/answer.mjs`
- `docs/app.mjs`
- `docs/ask.mjs`
- `docs/assets/screenshots/ask-campaign-monthly-1440.png`
- `docs/assets/screenshots/ask-campaign-monthly-390.png`
- `docs/assets/screenshots/desktop.png`
- `docs/assets/screenshots/mobile.png`
- `docs/browser-validation.json`
- `docs/release-acceptance.json`
- `docs/snapshot.json`
- `docs/validation.json`
- `docs/verified.json`
- `scripts/acceptance_matrix.py`
- `scripts/export_dashboard.py`
- `scripts/governed_snapshot.py`
- `scripts/marketing_ai.py`
- `scripts/test_answer.mjs`
- `scripts/test_campaign_monthly.py`
- `scripts/test_campaign_monthly_browser.py`
- `scripts/test_governed_snapshot.py`
- `scripts/test_marketing_ai.py`
- `scripts/test_marketing_ai_browser.py`
- `scripts/test_marketing_ai_live.py`
- `scripts/test_monthly_top_n.py`
- `scripts/test_public_browser.py`
- `scripts/validate_wren.py`
- `wren/README.md`
- `wren/validation/11_top_campaigns_monthly.duckdb.sql`
- `wren/validation/11_top_campaigns_monthly.wren.sql`

## Remaining limitations and blocked tests

Fixed synthetic 2025 history; no live feed, verified lifetime acquisition, pre-2025 history or post-2025 conversion tail. Seven-day last non-direct attribution is observational. UTC events become Europe/London reporting periods. Final refund/cancellation states restate order periods; merchandise revenue is not accounting revenue, profit, cash flow or causal impact. Straight-line budgets and complete feeds are assumptions. Undefined denominators remain NULL. Arbitrary questions require local authenticated services; execution parity cannot prove every interpretation. Public runtime depends on CDN/extension availability. Source hashes establish consistency, not signed provenance. Stop serving before rebuilds.

No required final test is failed, skipped or blocked. Earlier exploratory failures were corrected or rerun with approved environment access; only final evidence supports this decision.

READY TO DEPLOY
