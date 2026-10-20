"""Phase 5: CLI execution versus an independent read-only DuckDB connection.

Run from any directory, using the dbt venv Python; supply --wren-exe if needed.
Default: rebuild/test dbt and run its four independent validators first.
No Wren Python API or expanded Wren SQL is used as the reference oracle.
"""
import argparse
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "wren"
CASES = PROJECT / "validation"
ABS_TOL = 1e-8
REL_TOL = 1e-10
MODELS = {
    "MarketingCampaignMonthly": ("campaign_monthly", ["reporting_month", "campaign_id"]),
    "MarketingCampaignDaily": ("campaign_daily", ["reporting_date", "campaign_id"]),
    "MarketingCampaignSummary": ("campaign_summary", ["campaign_id"]),
    "MarketingChannelMonthly": ("channel_monthly", ["reporting_month", "marketing_channel"]),
    "MarketingMonthlyOverview": ("monthly_overview", ["reporting_month"]),
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def run(args, cwd=PROJECT):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=env,
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        # Connection contents and environment variables are never logged.
        raise RuntimeError(f"{Path(args[0]).name} {args[1]} failed:\n"
                           f"{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def records(output):
    if not output:
        return []
    try:
        value = json.loads(output, parse_float=Decimal)
        if isinstance(value, list):
            return value
        # CLI fallback when pandas is absent: column-oriented JSON.
        if value and all(isinstance(v, list) for v in value.values()):
            return [dict(zip(value, row)) for row in zip(*value.values(), strict=True)]
        return [value]
    except json.JSONDecodeError:
        return [json.loads(line, parse_float=Decimal) for line in output.splitlines() if line.strip()]


def compare(actual, expected, label):
    require(len(actual) == len(expected), f"{label}: row count {len(actual)} != {len(expected)}")
    for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
        require(list(a) == list(e), f"{label} row {i}: column names/order differ")
        for key, wanted in e.items():
            got = a[key]
            where = f"{label} row {i} {key}: {got!r} != {wanted!r}"
            if wanted is None or got is None:
                require(got is None and wanted is None, where)
            elif isinstance(wanted, bool):
                require(type(got) is bool and got == wanted, where)
            elif isinstance(wanted, int):
                require(not isinstance(got, bool) and Decimal(str(got)) == wanted, where)
            elif isinstance(wanted, Decimal):
                # Fixed-scale monetary amounts and integer sums must match exactly.
                require(Decimal(str(got)) == wanted, where)
            elif isinstance(wanted, float):
                require(math.isfinite(float(got)) and math.isfinite(wanted), where)
                require(math.isclose(float(got), wanted, rel_tol=REL_TOL, abs_tol=ABS_TOL), where)
            else:
                require(type(got) is type(wanted) and got == wanted, where)


def reference(db, sql):
    result = db.execute(sql)
    names = [c[0] for c in result.description]
    return [dict(zip(names, row, strict=True)) for row in result.fetchall()]


def cube_oracle(suffix):
    """Independent contract formulas, deliberately not read from cube expressions."""
    formulas = {
        "ctr_pct": "100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0)",
        "cpc_gbp": "SUM(spend_gbp) / NULLIF(SUM(clicks), 0)",
        "conversion_rate_pct": "100.0 * SUM(attributed_orders) / NULLIF(SUM(valid_sessions), 0)",
        "gross_roas": "SUM(attributed_gross_merchandise_revenue_gbp) / NULLIF(SUM(spend_gbp), 0)",
        "net_roas": "SUM(attributed_net_revenue_gbp) / NULLIF(SUM(spend_gbp), 0)",
        "media_only_cac_gbp": "SUM(spend_gbp) / NULLIF(SUM(attributed_first_observed_acquisitions), 0)",
        "attribution_rate_pct": "100.0 * SUM(attributed_orders) / NULLIF(SUM(eligible_conversions), 0)",
    }
    if suffix == "monthly_overview":
        formulas["conversion_rate_pct"] = "100.0 * SUM(eligible_conversions) / NULLIF(SUM(valid_sessions), 0)"
    if suffix not in ("campaign_daily", "campaign_monthly"):
        budget = "lifetime_budget_gbp" if suffix == "campaign_summary" else "allocated_budget_gbp"
        for name in ("budget_utilisation_pct", "budget_pacing_pct"):
            formulas[name] = f"100.0 * SUM(spend_gbp) / NULLIF(SUM({budget}), 0)"
    if suffix == "channel_monthly":
        for name in ("conversion_rate_pct", "gross_roas", "net_roas", "media_only_cac_gbp"):
            formulas[name] = ("CASE WHEN MIN(CASE WHEN cost_coverage = 'platform_media_only' "
                              f"THEN 1 ELSE 0 END) = 1 THEN {formulas[name]} END")
    return formulas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wren-exe", default=os.getenv("WREN_EXE") or shutil.which("wren"))
    parser.add_argument("--connection-file", type=Path, default=PROJECT / "connection_info.json")
    parser.add_argument("--skip-dbt", action="store_true", help="Only after full current dbt validation in this session")
    args = parser.parse_args()
    require(args.wren_exe, "Install wrenai[duckdb]==0.15.0 or provide --wren-exe")
    executable = shutil.which(args.wren_exe) or args.wren_exe
    args.wren_exe = str(Path(executable).resolve())
    connection = args.connection_file.resolve()
    require(connection.is_file(), "Copy wren/connection_info.json.example to the ignored connection_info.json")
    info = json.loads(connection.read_text(encoding="utf-8-sig"))
    require(info.get("datasource") == "duckdb" and info.get("format") == "duckdb", "Expected a DuckDB file-directory connection")
    folder = Path(info["url"])
    if not folder.is_absolute():
        folder = PROJECT / folder
    database = folder.resolve() / "fab_ent.duckdb"
    require(database.is_file(), "Configured directory must contain fab_ent.duckdb")
    require(database.resolve() == (ROOT / "data/generated/fab_ent.duckdb").resolve(),
            "Validation must use this project's dbt database")
    if not args.skip_dbt:
        dbt = Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
        print(run([dbt, "build", "--profiles-dir", ".dbt"], ROOT).splitlines()[-1])
        for script in ("validate_seed_load", "validate_staging", "validate_attribution", "validate_marts"):
            print(run([sys.executable, "-B", ROOT / "scripts" / f"{script}.py"], ROOT).splitlines()[-1])
    version = run([args.wren_exe, "--version"])
    require(version == "wrenai 0.15.0", f"Revalidate CLI behaviour before using {version}")
    print(version)
    print(run([args.wren_exe, "context", "validate", "--path", PROJECT, "--strict"]))
    print(run([args.wren_exe, "context", "build", "--path", PROJECT]))
    common = ["--mdl", PROJECT / "target/mdl.json", "--connection-file", connection]
    report = PROJECT / "target/validation"
    report.mkdir(parents=True, exist_ok=True)
    results = []

    def check(label, semantic, direct, cube_args=None):
        expected = reference(db, direct)
        command = ([args.wren_exe, "cube", "query", *common, *cube_args, "--output", "json"]
                   if cube_args else [args.wren_exe, "query", *common, "--sql", semantic, "--output", "json", "--quiet"])
        actual = records(run(command))
        compare(actual, expected, label)
        (report / f"{label}.wren.sql").write_text(semantic + "\n", encoding="utf-8")
        (report / f"{label}.duckdb.sql").write_text(direct + "\n", encoding="utf-8")
        (report / f"{label}.json").write_text(json.dumps(actual, default=str, indent=2) + "\n", encoding="utf-8")
        results.append({"id": label, "rows": len(actual), "status": "PASS"})
        print(f"PASS {label}: {len(actual)} ordered rows; values and NULLs match")
        return actual

    with duckdb.connect(str(database), read_only=True) as db:
        manifest = json.loads((PROJECT / "target/mdl.json").read_text())
        require(not manifest.get("relationships"), "Aggregate marts must have no relationships")
        require({m['name'] for m in manifest['models']} == set(MODELS), "Unexpected semantic model inventory")
        for case in json.loads((CASES / "cases.json").read_text()):
            label = case["id"]
            answer = check(label, (CASES / f"{label}.wren.sql").read_text(),
                           (CASES / f"{label}.duckdb.sql").read_text())
            print(json.dumps(answer, default=str))

        for model, (suffix, keys) in MODELS.items():
            physical = f'"fab_ent"."raw_marts"."mart_marketing__{suffix}"'
            meta = yaml.safe_load((PROJECT / "models" / model / "metadata.yml").read_text())
            require(meta['table_reference'] == {'catalog':'fab_ent','schema':'raw_marts','table':'mart_marketing__'+suffix}, "Only governed mart mappings allowed")
            cols = db.execute(f"DESCRIBE {physical}").fetchall()
            require({c["name"] for c in meta["columns"] if not c.get("is_calculated")} == {c[0] for c in cols}, "Physical column inventory drift")
            selections = [f'CAST("{c}" AS VARCHAR) AS "{c}"' if t == "DATE" else f'"{c}"' for c,t,*_ in cols]
            selected = ", ".join(selections)
            direct = f"SELECT {selected} FROM {physical} ORDER BY " + ", ".join(keys)
            semantic = f'SELECT {selected} FROM "{model}" ORDER BY ' + ", ".join(keys)
            check("rows_" + suffix, semantic, direct)
            pk = meta["primary_key"]
            require(db.execute(f'SELECT count(*) = count(DISTINCT ({", ".join(keys)})) FROM {physical}').fetchone()[0], f"{model}: duplicate grain")
            if pk == "grain_key":
                expr = f"CAST({keys[0]} AS VARCHAR) || '|' || {keys[1]}"
                check("key_" + suffix, f'SELECT grain_key FROM "{model}" ORDER BY grain_key',
                      f"SELECT {expr} AS grain_key FROM {physical} ORDER BY grain_key")

            cube = yaml.safe_load((PROJECT / "cubes" / (model + "Metrics") / "metadata.yml").read_text())
            formulas = cube_oracle(suffix)
            expressions = []
            names = []
            for measure in cube["measures"]:
                name = measure["name"]
                if name.startswith("total_"):
                    column = name.removeprefix("total_")
                    require(column in {c[0] for c in cols if c[1] not in ("VARCHAR", "DATE", "BOOLEAN")}, "Non-numeric cube measure")
                    expression = f'SUM("{column}")'
                else:
                    expression = formulas[name]
                expressions.append(f'{expression} AS "{name}"')
                names.append(name)
            # Both overall and dimensioned rollups exercise every cube measure.
            dimensions = [None, "marketing_channel" if suffix != "monthly_overview" else "acquisition_basis"]
            if suffix in ("campaign_daily", "campaign_summary"):
                dimensions.append("campaign_id")
            for dimension in dimensions:
                flags = ["--cube", cube["name"], "--measures", ",".join(names)]
                prefix, tail = "", ""
                if dimension:
                    flags += ["--dimensions", dimension, "--order-by", dimension + ":asc"]
                    prefix = dimension + ", "
                    tail = f" GROUP BY {dimension} ORDER BY {dimension} ASC"
                # Record Wren's generated semantic SQL, but never use it for the oracle.
                semantic = run([args.wren_exe, "cube", "query", *common, *flags, "--sql-only"])
                direct = "SELECT " + prefix + ", ".join(expressions) + f" FROM {physical}" + tail
                check("cube_" + suffix + ("_by_" + dimension if dimension else "_overall"), semantic, direct, flags)

        # Empty selection tests missing aggregate denominators; daily row parity
        # additionally tests actual zero-impression/click/acquisition denominators.
        formula = "100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0) AS ctr_pct, SUM(spend_gbp) / NULLIF(SUM(clicks), 0) AS cpc_gbp"
        empty = check("empty_null_ratios", f"SELECT {formula} FROM MarketingMonthlyOverview WHERE 1=0",
                      f"SELECT {formula} FROM fab_ent.raw_marts.mart_marketing__monthly_overview WHERE 1=0")
        require(all(v is None for v in empty[0].values()), "Empty ratios must be NULL")
    (report / "summary.json").write_text(json.dumps({"version": version, "absolute_tolerance": ABS_TOL,
        "relative_tolerance": REL_TOL, "checks": results}, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(results)} comparisons; report in wren/target/validation (ignored)")


if __name__ == "__main__":
    main()
