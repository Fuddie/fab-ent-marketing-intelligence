# Fab ENT Marketing Intelligence

Synthetic UK fashion marketing data for the fixed 2025 reporting period, in GBP.
Read [PROJECT_BRIEF.md](PROJECT_BRIEF.md), [METRIC_CONTRACT.md](METRIC_CONTRACT.md)
and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for scope, metric policies and fields.

## Architecture

Raw marketing CSVs -> dbt transformations -> DuckDB analytics tables -> Wren AI
semantic layer -> browser-based marketing AI dashboard.

dbt transforms the seeded raw data into governed analytics tables in DuckDB.
Wren provides a tested semantic layer for read-only local queries. A future
browser dashboard can consume those semantics.

Phase 1 loads and validates the raw CSV seeds in DuckDB. Phase 2 adds the clean
staging layer. Phase 3 adds tested order attribution. Phase 4 adds governed
marketing marts. Phase 5 connects these marts to a tested local Wren semantic
layer. The browser dashboard and natural-language service remain future work.

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

## Phase 4: governed business-facing marketing marts

The adopted governance section at the start of `METRIC_CONTRACT.md` governs these
marts. Raw, staging and Phase 3 attribution retain all statuses and unchanged
semantics. Every mart dependency uses `ref()`; the local profile creates tables
in `raw_marts`. Full column documentation, required-field, dimension, key and
relationship tests are in `models/marts/marketing/_marketing__marts.yml`.

| Business mart | Grain | Fixed snapshot rows |
| --- | --- | ---: |
| `mart_marketing__campaign_daily` | London reporting date + campaign | 3,022 |
| `mart_marketing__campaign_summary` | Campaign | 24 |
| `mart_marketing__channel_monthly` | London reporting month + marketing channel | 72 |
| `mart_marketing__monthly_overview` | London reporting month | 12 |

Daily campaigns include active budget days plus all observed fact dates, even
outside campaign bounds. Summaries retain every campaign, including CAM-0023 and
CAM-0024 with spend and no eligible attributed orders. Channel/month includes the
three paid channels, Direct, Organic and Unattributed. Direct/Organic describe
session traffic only; unmatched orders are never inferred to belong to either.
The overview retains all assigned/unassigned orders, acquisitions and monetary
components. Internal supporting tables are governed orders (2,500 rows), the first
observed acquisition ledger (1,174), and independently aggregated daily facts
(4,077); these are implementation details rather than additional consumer marts.

### Governed measures

- `placed_orders` counts all recorded attempts, including cancelled and refunded.
  `attributed_placed_orders` is the all-status assigned subset.
- `eligible_conversions` requires `status IN ('completed','partially_refunded')
  AND net_order_amount_gbp > 0`. `attributed_orders` is its campaign-assigned
  subset; `unattributed_eligible_orders` is retained separately.
- Gross merchandise revenue includes completed, partially refunded and fully
  refunded sales, excluding cancellations. Sales refunds use those same sales;
  cancellation reversals are a separate measure, not customer cash refunds.
  Net revenue includes signed/zero non-cancelled sale amounts. Never subtract
  refunds again from source net, or filter revenue to conversion-eligible orders.
- First observed acquisition chooses each customer's earliest eligible UTC order
  across all history, breaking ties by ascending order ID. It uses that order's
  assignment, retaining unmatched acquisitions. Period filtering happens after
  selection. `acquisition_basis = 'first_observed_2025_snapshot'` explicitly
  disclaims verified lifetime acquisition. Totals are 1,174, with 759 attributed
  and 415 unattributed.
- Event timestamps are converted to Europe/London before date/month assignment.
  Platform ad dates and campaign bounds already use London dates. Seven-day
  attribution continues to use elapsed UTC time without changing its winners.

Media, sessions, orders, acquisitions and active-day budgets are separately
aggregated before joining their union of grain keys. Zero activity is filled only
under this validated complete fixed-snapshot assumption. Preserve monetary
precision; allocated budget division and ratios use floating precision. Recompute
ratios from additive components; never sum or average stored ratios.

### Ratios and monitoring

| Metric | Definition |
| --- | --- |
| CTR (%) | Clicks / impressions * 100 |
| CPC (GBP) | Media spend / clicks |
| Campaign/paid-channel conversion (%) | Attributed eligible orders / valid classified sessions * 100, including anonymous sessions |
| Overall website conversion (%) | All eligible orders / all valid sessions * 100 |
| Gross / net ROAS (multiple) | Attributed gross merchandise / net revenue respectively, divided by media spend; overview also excludes unattributed revenue from these numerators |
| Media-only CAC (GBP) | Period media spend / period attributed first observed acquisitions |
| Attribution rate (%) | Attributed eligible orders / all eligible orders * 100 at the row's scope |
| Campaign summary budget utilisation (%) | Full observed spend / lifetime budget * 100 |
| Campaign daily budget utilisation (%) | Cumulative spend / lifetime budget * 100 |
| Campaign daily pacing (%) | Cumulative spend / straight-line expected cumulative budget * 100 |
| Monthly budget utilisation / pacing (%) | Monthly spend / budget allocated over active calendar days * 100 |

Zero or missing denominators produce NULL (display as N/A). Direct, Organic and
Unattributed channel CAC, ROAS and conversion rates are NULL because costs or
order-to-traffic assignments are unavailable. Campaign/paid attribution rates are
necessarily 100% when defined; overall completeness comes from the overview.

Lifetime campaign budget is non-additive on daily rows. Daily expected budget
uses inclusive elapsed active days clamped to the campaign lifetime. Summary
pacing equals lifetime utilisation at this completed campaign horizon. Monthly
allocated budgets are straight-line monitoring allocations, not approved monthly
budgets. Ratios can be recomputed for selected periods from components, but CAC
is period-based rather than spend-cohort-based.

Flags expose period spend without eligible attributed orders; utilisation >100%;
pacing >100%; approaching budget at 90%-100%; unexpected negative source inputs;
and unattributed placed orders at row scope. Undefined budget flags are false.
Negative values are preserved. Campaign-scoped incomplete-attribution flags are
false because unmatched orders have no campaign; this is not global completeness.
Spend without orders is a monitoring condition, not proof of waste.

### Build and independent validation

After the Phase 1 setup, run from the repository root:

```powershell
.\.venv\Scripts\dbt.exe build --profiles-dir .dbt
.\.venv\Scripts\python.exe -B scripts/validate_seed_load.py
.\.venv\Scripts\python.exe -B scripts/validate_staging.py
.\.venv\Scripts\python.exe -B scripts/validate_attribution.py
.\.venv\Scripts\python.exe -B scripts/validate_marts.py
git diff --check
git status --short
```

The full build includes seeds, staging, attribution, marts and all data/unit
tests. Mart singular tests check source conservation/no fan-out, all additive
campaign/channel/monthly rollups, acquisition selection, cumulative budgets,
spend-only campaigns, ratio edge cases, and fixed totals. Unit fixtures cover
London month boundaries, all statuses, negative/zero values, multiple order
lines, acquisition ties, and retention of an unattributed first acquisition.
The new read-only validator recomputes attribution, London dates, first
acquisitions, budget allocations and all mart measures/ratios/flags directly from
raw CSVs without importing the mart SQL or aggregation macros. Its independent
London conversion uses the documented fixed 2025 BST interval only.

| Reconciliation measure | Fixed snapshot GBP |
| --- | ---: |
| Platform media spend | 189,198.54 |
| Raw gross order value = gross order lines | 416,314.00 |
| Governed gross merchandise revenue | 396,434.00 |
| Sales refunds | 43,076.50 |
| Cancellation reversals | 19,880.00 |
| Net merchandise revenue | 353,357.50 |

Raw gross less cancelled gross equals governed gross; governed gross less sales
refunds equals net revenue. Raw gross less sales refunds and cancellation
reversals equals source net. The cancelled gross and reversal amounts are equal
in this source. Attributed and unattributed components reconcile without overlap.
The snapshot contains 2,500 placed attempts, 2,228 eligible conversions (1,439
attributed and 789 unattributed), and 15,000 valid sessions.

### Limitations

These are synthetic merchandise and media metrics, not accounting revenue,
profit, causal attribution or a calibrated funnel. There is no pre-2025 history
or post-2025 conversion tail. Account creation is not acquisition. Refunds and
cancellations restate original order periods using final snapshot status; there
are no adjustment-event dates, cash-flow measures, refund quantities, VAT,
shipping, discounts, fees or fully loaded acquisition costs. Refreshes may change
historic conversions and first observed acquisition dates/campaigns. Period
order-to-session conversion can exceed 100% because of multiple orders and
cross-period attribution; it is not a unique-session probability. Missing feeds
are not detected by zero-activity flags. Wren definitions and dashboard code are
not part of Phase 4.

## Phase 5: Wren semantic layer

The current architecture is CSV seeds -> dbt staging -> tested attribution ->
governed dbt marts in DuckDB -> Wren models and aggregate metric cubes -> local
semantic SQL. The browser dashboard and natural-language service are not built.
No dbt metric definitions changed for this phase.

The dedicated [wren/](wren/README.md) project keeps its YAML outside dbt's model,
seed and test paths. Wren CLI **0.15.0** and project schema version **5** were
validated using the installed help, bundled documentation and runtime behaviour.
The physical catalog is **fab_ent**, the schema is **raw_marts**. Wren's internal
namespace, `wren.public`, is separate from the physical mapping.

| Wren model | Governed relation in `fab_ent.raw_marts` | Grain | Rows |
| --- | --- | --- | ---: |
| `MarketingCampaignDaily` | `mart_marketing__campaign_daily` | London date + campaign | 3,022 |
| `MarketingCampaignSummary` | `mart_marketing__campaign_summary` | Campaign, full observed snapshot | 24 |
| `MarketingChannelMonthly` | `mart_marketing__channel_monthly` | London month + channel | 72 |
| `MarketingMonthlyOverview` | `mart_marketing__monthly_overview` | London month, all website outcomes | 12 |

Every model has a corresponding `Marketing…Metrics` cube. Additive cube measure
names start with `total_` (for example, `total_spend_gbp`). Calculated measures
include CTR, CPC, conversion rate, gross/net ROAS, media-only CAC, attribution
rate and budget utilisation/pacing. They divide aggregated numerators by
aggregated denominators, returning NULL for zero/missing denominators. Money is
labelled **GBP**, rates ending `_pct` are percentages, and ROAS is a multiple.
Dates, categorical dimensions, cost coverage, acquisition basis and boolean
quality flags retain their documented meaning. All physical mart fields remain
available; no seeds or internal supporting tables are semantic models.

Daily lifetime budget, cumulative spend and expected cumulative budget are
non-additive across dates. Daily budget utilisation/pacing are exposed at the
exact mart row grain and omitted from the daily aggregation cube. Summary
budgets count once per campaign; monthly budgets are active-day allocations,
not approved monthly budgets. Stored ratios and flags describe their original
row grain. Never average stored ratios. There are deliberately no relationships
between differently aggregated marts; choose one model per question.

### Local Wren setup (Windows PowerShell)

Complete the dbt setup above first. Run from the repository root. Use an isolated
Wren environment to preserve the dbt dependency pins:

```powershell
python -m venv wren/.venv
.\wren\.venv\Scripts\python.exe -m pip install -r wren/requirements.txt
.\wren\.venv\Scripts\python.exe -m pip check
$WrenExe = (Resolve-Path .\wren\.venv\Scripts\wren.exe).Path
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
& $WrenExe --version
if (-not (Test-Path wren/connection_info.json)) {
    Copy-Item wren/connection_info.json.example wren/connection_info.json
}
```

The safe example specifies `datasource: duckdb`, `format: duckdb` and directory
`../data/generated`. **Always run Wren queries with `wren/` as the working
directory**: relative connection URLs resolve from the process working directory,
not the connection file's location. This connector discovers `.duckdb` files in
the directory and attaches them **READ_ONLY** under filename-stem catalog names.
Keep only the intended `fab_ent.duckdb` there. The explicit connection file avoids
the globally active Wren/Jaffle profile. No credentials or server are required.
Local connection information, environments, Wren targets/reports, databases,
logs and caches are ignored by Git. Do not put an absolute local path in tracked
project YAML. The semantic definitions are not a database access-control boundary.

```powershell
Push-Location wren
try {
    & $WrenExe context validate --path . --strict
    & $WrenExe context build --path .
    & $WrenExe query --mdl target/mdl.json --connection-file connection_info.json `
        --sql (Get-Content validation/02_ctr_cpc.wren.sql -Raw) --output json --quiet
    & $WrenExe cube query --mdl target/mdl.json --connection-file connection_info.json `
        --cube MarketingMonthlyOverviewMetrics `
        --measures total_spend_gbp,ctr_pct,cpc_gbp,net_roas,media_only_cac_gbp --output json
} finally {
    Pop-Location
}
```

Stop if any command fails. An existing 0.15.0 executable can also be assigned to
`$WrenExe`; no machine-specific installation path is needed in Git.

### Validation and example questions

Run the complete reproducible validation from the repository root:

```powershell
.\.venv\Scripts\python.exe -B scripts/validate_wren.py --wren-exe $WrenExe
git diff --check
git status --short
```

The validator first runs full `dbt build --profiles-dir .dbt`, then all four
independent seed/staging/attribution/mart validators. It validates Wren strictly,
builds the context, executes every saved semantic query through the Wren CLI,
and executes a separate direct DuckDB query using a read-only connection.
`--skip-dbt` is available only when the full current dbt validation has already
passed in the same session. There is no default result limit. See
[comparison policy and recorded answers](wren/validation/README.md).

All ten required questions have paired, reviewable `.wren.sql` and `.duckdb.sql`
files in [wren/validation](wren/validation/cases.json):

1. What is total marketing spend?
2. What are overall CTR and CPC?
3. Which five campaigns have the highest net ROAS?
4. Which campaigns spent money without eligible attributed orders?
5. Which campaigns exceeded their lifetime budget?
6. What is monthly spend and net revenue?
7. How does performance compare by channel?
8. What are overall paid CAC and first-observed acquisitions?
9. How much eligible revenue is unattributed?
10. Which month had the strongest net ROAS?

The broader suite compares all 3,130 exposed mart rows, calculated composite
keys, every cube measure at overall and grouped scopes, and NULL ratios on
empty selections. Integers, fixed-scale decimals, booleans, strings and NULL
positions match exactly. Floating values satisfy
`abs(actual - expected) <= max(1e-8, 1e-10 * max(abs(actual), abs(expected)))`.
Rows, duplicate multiplicity, column order and deterministic result ordering
must match. Raw CLI outputs, generated cube semantic SQL, independent reference
SQL and a summary are written only to ignored `wren/target/validation/`.

### Semantic limitations

Acquisition means **first observed in the fixed 2025 snapshot**, not verified
lifetime new customers. Earliest eligible order is selected across available
history before period filtering. Period paid CAC uses 759 attributed acquisitions,
not all 1,174 acquisitions, and includes only recorded media costs.

ROAS uses attributed revenue, while overview net revenue includes unmatched
sales. "Eligible revenue" in example 9 means the governed **revenue-eligible sales
scope**, including fully refunded sales; it does not mean gross revenue from
conversion-eligible orders. Those two policies differ. The four marts do not
provide a separate gross-revenue amount filtered to positive-net conversions.
Unattributed governed net revenue is GBP 124,481.50; never infer it belongs to
Direct or Organic. Those channels and Unattributed retain NULL conversion,
ROAS and CAC where coverage is unavailable. Use the overview for overall rates;
the channel cube suppresses cost-dependent rates for mixed paid/unpaid groups.

The fixed snapshot assumes complete feeds and has no pre-2025 history or
post-2025 conversion tail. Final-status refunds and cancellations restate original
order periods. Refreshes can change prior conversion and acquisition histories.
No cash-flow, profit, causal uplift or verified lifetime acquisition is implied.
These limitations and the existing Phase 4 limitations apply to every semantic
answer. Arbitrary SQL remains capable of misusing stored ratios; use the tested
cube measures and [business rules](wren/knowledge/rules/marketing.md).
