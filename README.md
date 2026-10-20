# Fab ENT Marketing Intelligence

Synthetic UK fashion marketing data for the fixed 2025 reporting period, in GBP.
Read [PROJECT_BRIEF.md](PROJECT_BRIEF.md), [METRIC_CONTRACT.md](METRIC_CONTRACT.md)
and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for scope, metric policies and fields.

## Intended architecture

Raw marketing CSVs -> dbt transformations -> DuckDB analytics tables -> Wren AI
semantic layer -> browser-based marketing AI dashboard.

dbt will transform the seeded raw data into analytics tables in DuckDB. Wren AI
will provide the semantic layer over those tables for consistent, read-only
answers in the browser-based marketing AI dashboard.

Phase 1 loads and validates the raw CSV seeds in DuckDB. Phase 2 adds the clean
staging layer. Phase 3 adds tested order attribution. Reporting marts, the Wren AI
semantic layer and the browser-based dashboard remain future work.

## Phase 1: dbt + DuckDB seeds

The repository root is the dbt project. `seed-paths: [data/raw]` loads the seven
existing CSVs directly, without copying them. `data/raw/seeds.yml` declares every
column type: identifiers/text as VARCHAR, money as DECIMAL(18,2), counts as BIGINT,
dates as DATE and UTC timestamps as TIMESTAMPTZ. Blank session identities and
campaign IDs load as NULL. The connection timezone is UTC; raw values and all
order statuses are retained.

The local database is `data/generated/fab_ent.duckdb`, with tables in schema
`raw` (for example, `raw.orders`). This database, `.venv`, `.dbt`, local profiles,
dbt targets/logs/packages and DuckDB temporary files are excluded from Git.
`profiles.yml.example` contains only a relative path and no credentials.
Staging does not resolve outstanding business metric policies.

## Windows PowerShell setup

Run all commands from the repository root. Use Python 3.14 (validated with
3.14.4), with `python` available on PATH, plus Git. Dependencies are pinned in
`requirements.txt`: dbt-core 1.12.6, dbt-duckdb 1.11.0 and DuckDB 1.5.6.
Installation needs access to PyPI; no database server or dbt account is needed.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
New-Item -ItemType Directory -Force .dbt, data/generated | Out-Null
if (-not (Test-Path .dbt/profiles.yml)) {
    Copy-Item profiles.yml.example .dbt/profiles.yml
}
```

Using the virtual environment executables directly avoids PowerShell activation
and execution-policy changes. Keep the database path in the local profile as
shown for the validation script below. Relative database paths resolve from the
working directory, so always run from the repository root. Explicit
`--profiles-dir .dbt` uses the repository's ignored local profile.

## Load and verify

```powershell
.\.venv\Scripts\python.exe scripts/validate_raw_data.py
.\.venv\Scripts\dbt.exe debug --profiles-dir .dbt
.\.venv\Scripts\dbt.exe seed --profiles-dir .dbt --full-refresh
.\.venv\Scripts\python.exe scripts/validate_seed_load.py
git diff --check
git status --short
```

Each command should exit successfully; stop if one fails. The raw validator
checks keys, references, date coverage, monetary arithmetic and isolated source
fixtures. Its attribution diagnostic covers all statuses and is not a dbt
attribution model or published metric. The seed validator opens DuckDB read-only,
checks all seven table counts, compares every typed row against the CSVs in both
directions (including duplicates and NULLs), checks fixed snapshot totals, and
reconciles every order to its lines. No dbt packages are required.

Repeat the seed and validation commands to rebuild the raw tables from the same
snapshot. `--full-refresh` recreates the seed tables, including their types.
Do not run `scripts/generate_synthetic_data.py` as part of this setup: it
overwrites the existing CSV snapshots. Close other DuckDB connections before
seeding to avoid file locks. `dbt clean --profiles-dir .dbt` removes only
`target/` and `dbt_packages/`; it retains the local database and raw CSVs.

## Phase 2: staging

After loading the seeds, build and validate staging from the repository root:

```powershell
.\.venv\Scripts\dbt.exe build --select staging --profiles-dir .dbt
.\.venv\Scripts\python.exe scripts/validate_staging.py
```

The seven views in `models/staging/marketing` are:

- `stg_marketing__campaigns`
- `stg_marketing__ad_performance`
- `stg_marketing__web_sessions`
- `stg_marketing__customers`
- `stg_marketing__orders`
- `stg_marketing__order_items`
- `stg_marketing__products`

With the example profile, dbt creates these in `raw_staging` (the target schema
`raw` plus the custom schema `staging`). Each view uses `ref()` to select and
cast every seed column explicitly. Ad `date` becomes `performance_date`; other
source field names remain unchanged. Timestamps remain UTC-aware TIMESTAMPTZ,
money remains DECIMAL(18,2), and source reporting dates remain DATE. No reporting
timezone conversion, attribution, status exclusions or calculated metrics occur.
NULL identities, campaignless visits, zero measures and signed amounts are
preserved without imputation, clipping or filtering.

Model and column documentation and built-in tests are in
`models/staging/marketing/_marketing__models.yml`. Singular tests in
`tests/staging` check the composite ad key, campaign date/channel structure,
session classifications, order/line arithmetic, status semantics and the fixed
snapshot totals below. Bidirectional `EXCEPT ALL` checks every staged row against
its seed, including NULLs and duplicates. Anonymous customer IDs and campaignless
Direct/Organic visits intentionally have no non-null test. Repeated products per
order are valid; clicks are not constrained to impressions or session counts.
The read-only validator reports all seven seed/staging counts and exact GBP
totals; its relation names come from dbt's generated manifest.

## Snapshot reconciliation

The documented generator and dictionary establish 24 campaigns, 1,500 customers,
15,000 sessions, 2,500 orders and 30 products. Active campaign dates determine
the 2,985 daily ad rows; the fixed generated order lines total 6,129.

| Raw table | Loaded rows |
| --- | ---: |
| ad_performance | 2,985 |
| campaigns | 24 |
| customers | 1,500 |
| order_items | 6,129 |
| orders | 2,500 |
| products | 30 |
| web_sessions | 15,000 |

The documents specify reconciliation rules rather than exact monetary totals.
The following fixed snapshot baselines come from the existing raw validator
and are independently checked in DuckDB:

| Measure (all raw statuses) | GBP |
| --- | ---: |
| Media spend | 189,198.54 |
| Gross order amount = gross line amount | 416,314.00 |
| Refunds/cancellation reversals, orders = lines | 62,956.50 |
| Net order amount = net line amount | 353,357.50 |

Gross minus refunds/reversals equals net exactly. These source amounts do not
define attributed order amount, eligible orders or accounting revenue. Metric
status and amount policies remain as documented in the metric contract.

## Phase 3: seven-day order attribution

`models/intermediate/marketing` contains two fully rebuilt tables in
`raw_intermediate`: `int_marketing__order_attribution_candidates` audits every
same-customer session (including exclusions), and `int_marketing__orders_attributed`
keeps exactly one row per staging order. Only identified paid sessions with an
existing campaign qualify in `[order_timestamp - 168 hours, order_timestamp)`
using UTC instants. Latest timestamp wins, then lexically greatest session ID.
Direct and campaignless Organic touches cannot overwrite a qualifying paid touch.
Source and medium are split from the supplied `source_medium` classification.

Every order status and all three source GBP amounts are preserved. Missing
identity, timestamps or campaign never produce inferred assignments. Unattributed
reasons follow the documented priority in the model YAML; the candidate table
retains all exclusion details. Anonymous visits cannot be linked to an order,
so orders with no matching identified visit report `no_customer_sessions`.
No status-based commercial eligibility or revenue metric is defined here.

After loading seeds and staging, run:

```powershell
.\.venv\Scripts\dbt.exe build --select +path:models/intermediate/marketing --profiles-dir .dbt
.\.venv\Scripts\python.exe scripts/validate_attribution.py
```

The build includes key/reference checks, exact order-field and money conservation,
assignment partition checks, an independent SQL winner check, all 12 documented
fixtures, and unit coverage for missing data, exact boundaries and lexical ties.
The read-only Python validator independently recomputes every assignment directly
from raw CSVs and prints assignment counts, reasons, channels, fixtures and GBP
reconciliation totals. Rebuild these tables to incorporate late-arriving data;
no incremental attribution or reporting-period filter is applied.
