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

Phase 1 implements only loading and validating the raw CSV seeds in DuckDB.
Transformation models, analytics tables, the Wren AI semantic layer and the
browser-based dashboard are planned for later phases.

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
`models/` is reserved for future work; Phase 1 has no staging, attribution or
reporting models, and does not resolve outstanding business metric policies.

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
