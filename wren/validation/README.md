# Phase 5 comparison evidence

Validated with Wren CLI 0.15.0 against the current fixed 2025 synthetic snapshot.
The full dbt build passed all 376 tasks: 23 seeds/models and 353 tests (including
unit tests). Independent seed, staging, attribution and mart CSV-oracle checks
passed before Wren validation. Strict Wren validation and context build pass.

Run `scripts/validate_wren.py` using the root README commands. It performs 27
comparisons: ten saved question pairs; four complete row comparisons (3,130
rows); two calculated composite key comparisons; ten native cube executions
(every measure overall, by channel/basis, and by campaign where applicable);
and an empty-selection NULL-ratio comparison. A failing subprocess, row count,
column/order mismatch, NULL mismatch or value discrepancy exits nonzero.

Each question has separate `.wren.sql` and `.duckdb.sql` files. The former is
executed with `wren query`, not directly in DuckDB. Reference queries use fully
qualified governed physical relations in a separate DuckDB read-only connection;
they never use Wren's expanded plan or substitute semantic names at runtime.
Cube reference formulas are separately specified in the validator from the
metric contract, not read from cube expressions. Cube executions use
`wren cube query`; `--sql-only` saves the generated semantic SQL for review.

Comparisons preserve row sequence, duplicate multiplicity and column order.
Top-N queries explicitly use `NULLS LAST` and stable identifier/month tie breaks.
Dimensions are ordered ascending; whole-mart comparisons order by complete
grain keys. Dates are explicitly cast to ISO VARCHAR in row comparisons to
avoid CLI/Pandas epoch-date serialization differences. Boolean values must
remain booleans. NULL must match NULL exactly, including empty selections and
undefined ratios in zero-activity daily rows. Whole-row parity also covers all
stored ratios, cost-coverage fields, acquisition bases and quality flags.

Integers and fixed-scale DECIMAL amounts match exactly (CLI decimals can be
JSON strings). DOUBLE calculations, budget allocations and ratios use Python
`math.isclose(rel_tol=1e-10, abs_tol=1e-8)`:

```
abs(actual - expected) <= max(1e-8, 1e-10 * max(abs(actual), abs(expected)))
```

The absolute tolerance accommodates CLI JSON's ten decimal places; relative
tolerance accommodates floating aggregation order. Nonfinite values fail.
Results are never rounded before comparison. Empty and zero-denominator rates
are NULL, not zero, NaN or infinity. Unpaid-channel rates remain NULL; mixed
coverage channel-cube totals deliberately suppress cost-dependent rates.

Ignored `wren/target/validation/` contains semantic SQL, reference SQL, actual
rows and `summary.json` for each comparison. It may contain runtime local paths
in build output, so targets/logs are never committed. The following human-readable
answers are rounded for display only. All money is GBP.

| Query | Verified answer |
| --- | --- |
| 01 Total spend | GBP 189,198.54 |
| 02 Overall CTR / CPC | 2.113077273% / GBP 0.3306435541 |
| 03 Highest campaign net ROAS | CAM-0001 2.810855303x; CAM-0005 2.5108755399x; CAM-0003 2.4349760316x; CAM-0002 2.2409006968x; CAM-0009 2.063213345x |
| 04 Spend, no eligible attributed orders | CAM-0023 GBP 8,665.44; CAM-0024 GBP 3,281.20; zero attributed orders each |
| 05 Lifetime overspend | CAM-0003, CAM-0007, CAM-0011, CAM-0015, CAM-0019, CAM-0023; all at 112% utilisation |
| 06 Monthly spend / net revenue | Twelve rows below |
| 07 Channel comparison | Six rows below; unpaid conversion, ROAS and CAC remain NULL |
| 08 Paid media-only CAC / acquisitions | GBP 249.2734387352; 1,174 first observed, 759 paid-attributed and 415 unattributed |
| 09 Unattributed revenue | Gross merchandise GBP 140,830.00; sales refunds GBP 16,348.50; net GBP 124,481.50; 789 eligible orders |
| 10 Strongest monthly net ROAS | June 2025, 2.026596634x |

Query 09 uses the contract's **revenue-eligible sales** scope, which includes
fully refunded sales and differs from positive-net conversion eligibility.
The marts do not contain separate conversion-eligible gross revenue. Net sales
revenue and conversion counts remain explicitly named; do not silently filter
refunds out of governed revenue to make eligibility sound uniform.

| London month | Spend GBP | Website net revenue GBP |
| --- | ---: | ---: |
| 2025-01 | 11,150.37 | 22,498.00 |
| 2025-02 | 10,570.53 | 29,802.00 |
| 2025-03 | 11,486.11 | 34,549.00 |
| 2025-04 | 12,400.65 | 30,355.00 |
| 2025-05 | 12,702.52 | 27,038.00 |
| 2025-06 | 12,260.95 | 32,968.00 |
| 2025-07 | 19,489.54 | 28,669.00 |
| 2025-08 | 20,462.01 | 29,571.50 |
| 2025-09 | 18,301.52 | 24,710.50 |
| 2025-10 | 20,469.56 | 30,263.50 |
| 2025-11 | 20,204.00 | 32,478.50 |
| 2025-12 | 19,700.78 | 30,454.50 |

| Channel | Spend GBP | Sessions | Attributed eligible orders | Net revenue GBP | Net ROAS | Media-only CAC GBP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct | 0.00 | 2,765 | 0 | 0.00 | NULL | NULL |
| Google Paid Search | 59,634.58 | 3,199 | 469 | 75,990.50 | 1.2742690566 | 234.7818110236 |
| Meta Paid Social | 69,569.56 | 3,649 | 533 | 82,643.50 | 1.1879261562 | 253.9035036496 |
| Organic | 0.00 | 2,266 | 0 | 0.00 | NULL | NULL |
| TikTok Paid Social | 59,994.40 | 3,121 | 437 | 70,242.00 | 1.1708092755 | 259.7160173160 |
| Unattributed | 0.00 | 0 | 0 | 124,481.50 | NULL | NULL |

Zero recorded Direct/Organic spend is not known zero acquisition cost; orders
are not reassigned to those traffic channels. ROAS uses attributed revenue;
monthly website net revenue includes unattributed sales. These are fixed-snapshot
media/merchandise measures, not profit or causal effect. First observed is based
only on 2025 history. Final statuses restate original order dates and there is
no post-2025 conversion tail or verified lifetime acquisition history.

Campaign-month extension: case `11_top_campaigns_monthly` adds the exact ranking question. The validator now compares five models, all monthly rows, their calculated key, and the new cube overall and by channel: 32 Wren/direct comparisons. See [current monthly validation](../../docs/CAMPAIGN_MONTHLY_VALIDATION.md) for execution status; the original Phase 5 evidence above predates this extension.
