# Fab ENT Marketing Intelligence

A marketing analytics portfolio project that turns fragmented campaign, website and order data into a consistent view of spend, merchandise revenue and acquisition. I designed and implemented the data pipeline, metric definitions, interactive dashboard and optional local question service, with independent checks between the data warehouse, semantic layer and browser.

The project uses a **fixed synthetic 2025 snapshot in GBP**, not a live production feed. It demonstrates analytics engineering and decision support; it does not claim commercial impact for a real business.

## Live dashboard and repository

- [Explore the public dashboard](https://fuddie.github.io/fab-ent-marketing-intelligence/)
- [View the source repository](https://github.com/Fuddie/fab-ent-marketing-intelligence)
- [Read the current release assessment](RELEASE_READINESS.md)

![Marketing dashboard on desktop](docs/assets/screenshots/desktop.png)

## Business problem

A marketing manager needs to compare channels and campaigns without changing the meaning of revenue, conversion or acquisition between reports. Platform spend, website sessions and orders have different grains, and an order may have no attributable campaign. Joining these records carelessly inflates results and hides uncertainty.

I defined a common metric contract and built a dashboard that keeps attributed performance, website totals, budget monitoring and missing attribution visible as distinct business questions.

## What I built

- A reproducible pipeline from seven source datasets to tested marketing marts.
- Five governed Wren models with documented grains, measures and ratio rules.
- A public dashboard with filters, trends, campaign comparisons and monitoring alerts.
- Eleven saved Verified examples, plus Ask Marketing AI for arbitrary local questions.
- Independent validation of source records, attribution, marts, semantic queries, exported snapshots and browser calculations.

## Architecture and data flow

**Raw synthetic marketing data → dbt transformations and governed marts → DuckDB storage → Wren semantic layer → validated Parquet snapshots → browser dashboard**

In plain terms, dbt prepares consistent reporting tables, DuckDB stores them, and Wren supplies their business-facing query interface. The export process executes queries through Wren, checks results independently against DuckDB and publishes small Parquet snapshots. The browser queries these snapshots using DuckDB WebAssembly; it never receives the local database.

The optional local question service uses an **authenticated Codex CLI** to generate restricted semantic SQL. Queries are validated, executed through Wren and independently checked against DuckDB before results are shown. This verifies execution consistency, not every possible interpretation of a business question.

## Key analytical and governance decisions

I defined the policies in the [metric contract](METRIC_CONTRACT.md):

- **Attribution:** seven-day last non-direct paid touch, using elapsed UTC time and deterministic ties. Unmatched outcomes remain unattributed.
- **Reporting time:** raw timestamps retain UTC; reporting dates and months use Europe/London.
- **Eligibility:** completed and partially refunded orders with positive net value count as eligible conversions. Merchandise revenue follows a separate status policy, retaining fully refunded sales and excluding cancellations.
- **Acquisition:** each customer's earliest eligible order in the observed history. This is first-observed acquisition, not verified lifetime acquisition.
- **Ratios:** divide summed components; never average stored ratios. A zero or missing denominator produces NULL, displayed as N/A.
- **Budgets:** lifetime budgets are counted once; selected-period allocations assume straight-line distribution across active calendar days. These are monitoring allocations, not approved monthly budgets.

Media, sessions, orders and acquisitions are aggregated separately before joining at a common grain to prevent fan-out.

## Dashboard and Ask Marketing AI capabilities

The dashboard includes spend and revenue cards, monthly trends, net ROAS, channel comparisons, campaign rankings, budget alerts and attribution coverage. Date filters use inclusive whole months. Channel and campaign filters intersect; incompatible selections return an empty state. Website attribution context follows dates only because unmatched orders have no campaign.

**Verified examples** are saved Wren results for the full snapshot and ignore dashboard filters. **Local questions** can optionally use current dashboard filters. Single-value answers use KPI cards; other answers use a summary and responsive table, with technical details collapsed.

Monthly top-N questions rank within each reporting month, sort the requested metric descending and break ties by entity ID or name. Both monthly top-three campaign and channel checks return **36 rows: three for each of 12 months**, with monthly rank exposed and no fourth-ranked entity. See the [release evidence](RELEASE_READINESS.md) for deterministic versus live checks.

## Data model and governed metrics

| Wren model | Reporting grain | Rows |
| --- | --- | ---: |
| `MarketingCampaignDaily` | London date and campaign | 3,022 |
| `MarketingCampaignMonthly` | London month and campaign | 112 |
| `MarketingCampaignSummary` | Campaign lifetime in this snapshot | 24 |
| `MarketingChannelMonthly` | London month and channel | 72 |
| `MarketingMonthlyOverview` | London month | 12 |

Together the five exports contain 3,242 rows. Measures include media spend, impressions, clicks, sessions, eligible conversions, attributed and unattributed merchandise revenue, first-observed acquisitions, ROAS, media-only CAC and budget utilisation. Direct, Organic and Unattributed cost-dependent ratios remain undefined where costs or assignments are unavailable.

Source coverage: 24 campaigns, 2,985 ad-performance records, 15,000 sessions, 1,500 customer records, 2,500 orders, 6,129 order lines and 30 products. Field definitions are in the [data dictionary](DATA_DICTIONARY.md); semantic details are in the [Wren guide](wren/README.md).

## Validation and data-quality evidence

I validated the pipeline with **359 dbt data tests and four unit tests**. The full build has 387 successful nodes, including seeds and models; 387 is not the test count.

Independent Python validators recompute attribution and mart results from raw CSVs. Wren validation compares 32 query results with direct DuckDB SQL. Export checks cover schemas, values, NULLs and SHA-256 checksums. Dashboard calculations are checked against direct SQL across **25,200 filter combinations**: 12 start months × 12 end months × 7 channel choices × 25 campaign choices, including reversed and incompatible ranges.

The [release assessment](RELEASE_READINESS.md) records exact commands, acceptance results, browser coverage, security checks and any blockers. [Snapshot metadata](docs/snapshot.json) and [dashboard validation](docs/validation.json) provide detailed evidence. Historical validation documents should not override the current release decision.

## Key findings demonstrated by the project

| Fixed-snapshot measure | Result |
| --- | ---: |
| Media spend | £189,198.54 |
| Gross merchandise revenue, excluding cancellations | £396,434.00 |
| Sales refunds | £43,076.50 |
| Net merchandise revenue | £353,357.50 |
| Eligible conversions | 2,228 |
| Unattributed eligible conversions | 789 (35.41%) |
| First-observed acquisitions | 1,174 |

Gross merchandise revenue less sales refunds reconciles to net merchandise revenue. Cancellation reversals of £19,880.00 are separate from sales refunds. Of the first-observed acquisitions, 759 are attributed and 415 unattributed.

Two campaigns, CAM-0023 and CAM-0024, have spend without eligible attributed conversions. This is a monitoring signal, not proof of waste. The attribution gap also shows why campaign performance cannot stand in for total website performance. Merchandise revenue is not accounting revenue, profit, cash flow, lifetime customer value or causal impact.

## Public versus local functionality

The public GitHub Pages dashboard supports interactive analytics and all eleven Verified examples without Python, Wren or the local question service. It requires a modern browser, HTTPS and internet access to the pinned DuckDB WebAssembly CDN and extension distribution. A CDN failure shows an explicit error rather than substitute values.

Arbitrary Local questions require the local Python service, Wren and authenticated Codex CLI. Public pages display a clear local-only message and do not contact localhost. Credentials, local databases, authentication files, caches and logs are not published. Local questions send the question and governed semantic context through the authenticated CLI; returned rows are summarized locally.

The service binds to loopback, permits two explicit local dashboard origins and allows one active request. It restricts SQL to a single allowlisted model and read-only SELECT, rejects external access and unsafe composition, enforces a 90-second deadline and checks snapshot/database consistency before cached or new answers. See [the implementation](scripts/marketing_ai.py) and [acceptance tests](scripts/acceptance_matrix.py).

## Reproducible Windows setup

Run PowerShell from the repository root. The validated stack uses Python 3.14, Node.js for presentation checks, installed Google Chrome for browser tests, dbt-core 1.12.6, dbt-duckdb 1.11.0, DuckDB 1.5.6 and Wren CLI 0.15.0. Dependency installation requires network access.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-ai.txt -r requirements-dashboard.txt
New-Item -ItemType Directory -Force .dbt, data/generated | Out-Null
Copy-Item profiles.yml.example .dbt/profiles.yml
.\.venv\Scripts\dbt.exe build --profiles-dir .dbt

python -m venv wren/.venv
.\wren\.venv\Scripts\python.exe -m pip install -r wren/requirements.txt
$env:WREN_EXE = (Resolve-Path .\wren\.venv\Scripts\wren.exe).Path
.\.venv\Scripts\python.exe -B scripts/validate_wren.py --wren-exe $env:WREN_EXE
.\.venv\Scripts\python.exe -B scripts/export_dashboard.py --wren-exe $env:WREN_EXE
.\.venv\Scripts\python.exe -B scripts/validate_dashboard.py
.\.venv\Scripts\python.exe -m http.server 4173 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:4173/`. Keep an existing local profile rather than overwriting it on repeat setup; all database paths in the example profile are repository-relative. Do not regenerate the synthetic CSVs to reproduce this snapshot.

For Local questions, install and authenticate the Codex CLI separately. In a second PowerShell terminal, set `WREN_EXE` as above, then run:

```powershell
$env:MARKETING_AI_MODEL = 'gpt-6-luna'
$env:MARKETING_AI_REASONING = 'low'
.\.venv\Scripts\python.exe -B scripts/marketing_ai.py
```

The service probes model availability at startup; account access is required. Stop each foreground service with Ctrl+C. Rebuild and export together after governed source changes, with question serving stopped. The [release assessment](RELEASE_READINESS.md) contains the complete validation commands.

## Repository structure

| Location | Purpose |
| --- | --- |
| `data/raw/` | Versioned synthetic CSV snapshot and seed schemas |
| `models/`, `macros/`, `tests/` | dbt transformations, metric logic and tests |
| `wren/` | Five semantic models, metric cubes and validation SQL |
| `scripts/` | Independent validators, export pipeline, question service and tests |
| `docs/` | Static dashboard, Parquet snapshots and public evidence |
| `METRIC_CONTRACT.md`, `DATA_DICTIONARY.md` | Business definitions and field reference |
| `target/`, `data/generated/` | Ignored runtime evidence and local database |

## Limitations and future improvements

This is synthetic data with a fixed 2025 observation window: there is no pre-2025 history or post-2025 conversion tail. Seven-day observational attribution does not establish causality. Refunds and cancellations restate original order periods using final snapshot status; adjustment-event dates, cash-flow timing, tax, fees and fully loaded acquisition costs are unavailable.

Complete source feeds are assumed; a zero does not prove feed completeness. Period conversions can exceed sessions because of multiple orders and cross-period attribution. NULL denominators remain undefined. Budget allocations are assumptions, and first-observed acquisitions are not verified lifetime customers.

Arbitrary questions remain local-only, and execution parity cannot guarantee every natural-language interpretation. Useful extensions include broader live question evaluation, refresh orchestration with feed-completeness checks, adjustment-event history and reducing public CDN dependencies.
