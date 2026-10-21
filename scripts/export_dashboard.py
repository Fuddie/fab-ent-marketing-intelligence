"""Export Wren-returned rows to typed Parquet, proving equality with governed marts.

Run validate_wren.py first. This script re-executes all five model exports and
every fixed dashboard query through Wren; a direct DuckDB connection is the oracle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import duckdb
from validate_wren import ROOT, PROJECT, MODELS, run, records, compare, reference, require
from governed_snapshot import source_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wren-exe', default=os.getenv('WREN_EXE') or shutil.which('wren'), required=not (os.getenv('WREN_EXE') or shutil.which('wren')))
    args = parser.parse_args()
    exe = str(Path(args.wren_exe).resolve())
    require(run([exe,'--version']) == 'wrenai 0.15.0', 'Wren version drift')
    evidence = json.loads((PROJECT/'target/validation/summary.json').read_text())
    source_stamp = source_digest()
    require(evidence.get('source_sha256') == source_stamp, 'Governed inputs changed; run Wren validation again')
    require(len(evidence['checks']) >= 32 and all(c['status']=='PASS' for c in evidence['checks']), 'Run Wren validation first')
    out = ROOT/'docs/data'
    out.mkdir(parents=True, exist_ok=True)
    report=ROOT/'target/dashboard'
    report.mkdir(parents=True,exist_ok=True)
    common = [exe,'query','--mdl',PROJECT/'target/mdl.json','--connection-file',PROJECT/'connection_info.json','--output','json','--quiet']
    manifest = json.loads((ROOT/'docs/queries.json').read_text())
    snapshots, query_results = [], {}
    with duckdb.connect(str(ROOT/'data/generated/fab_ent.duckdb'), read_only=True) as db, duckdb.connect() as memory:
        for model,(suffix,keys) in MODELS.items():
            physical = 'fab_ent.raw_marts.mart_marketing__'+suffix
            columns = db.execute('DESCRIBE '+physical).fetchall()
            selections = ', '.join(f'CAST("{c}" AS VARCHAR) AS "{c}"' if t=='DATE' else f'"{c}"' for c,t,*_ in columns)
            semantic = f'SELECT {selections} FROM {model} ORDER BY '+', '.join(keys)
            actual = records(run([*common,'--sql',semantic]))
            expected = reference(db, semantic.replace(model,physical))
            compare(actual,expected,'export '+model)
            memory.execute(f'CREATE TABLE "{model}" ('+', '.join(f'"{c}" {t}' for c,t,*_ in columns)+')')
            # Bulk-read the Wren response, casting into the governed schema.
            # This avoids thousands of per-row inserts and never reads physical
            # values as the export source. JSON staging is ignored, not shipped.
            staging=report/(model+'.wren.json')
            staging.write_text(json.dumps(actual,default=str),encoding='utf-8')
            typed=', '.join(f'CAST("{c}" AS {t}) AS "{c}"' for c,t,*_ in columns)
            memory.execute(f'INSERT INTO "{model}" SELECT {typed} FROM read_json_auto(?)',[str(staging)])
            path = out/(model+'.parquet')
            # Parquet has no signed INT128 logical type. Use checked BIGINT casts
            # for bounded snapshot counts, rather than DuckDB's DOUBLE fallback.
            portable=', '.join(f'CAST("{c}" AS BIGINT) AS "{c}"' if t=='HUGEINT' else f'"{c}"' for c,t,*_ in columns)
            memory.execute(f"COPY (SELECT {portable} FROM \"{model}\" ORDER BY {', '.join(keys)}) TO '{path.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            compare(reference(memory,semantic), expected, 'typed parquet '+model)
            compare(reference(memory,semantic.replace(model,f"read_parquet('{path.as_posix()}')")), expected, 'reread '+model)
            snapshots.append({'model':model,'rows':len(actual),'schema':[{'name':c,'type':'BIGINT' if t=='HUGEINT' else t} for c,t,*_ in columns], 'governed_schema':[{'name':c,'type':t} for c,t,*_ in columns], 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'keys':keys,'export_sql':semantic})
            print(f'PASS exported {model}: {len(actual)} rows',flush=True)
        for query in manifest['queries']:
            model=query['model']
            physical='fab_ent.raw_marts.mart_marketing__'+MODELS[model][0]
            actual=records(run([*common,'--sql',query['sql']]))
            expected=reference(db,query['sql'].replace(model,physical))
            compare(actual,expected,'dashboard '+query['id'])
            compare(reference(memory,query['sql']),expected,'snapshot query '+query['id'])
            query_results[query['id']]=actual
            print('PASS fixed query '+query['id'],flush=True)
        verified=[]
        for case in json.loads((PROJECT/'validation/cases.json').read_text()):
            sql=(PROJECT/'validation'/f"{case['id']}.wren.sql").read_text()
            answer=records(run([*common,'--sql',sql]))
            direct=(PROJECT/'validation'/f"{case['id']}.duckdb.sql").read_text()
            compare(answer,reference(db,direct),'verified '+case['id'])
            verified.append({**case,'answer':answer,'semantic_sql':sql,'direct_sql':direct})
    def save(path,value):
        path.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')
    save(ROOT/'docs/verified.json',verified)
    require(source_digest() == source_stamp, 'Governed inputs changed during export; revalidate and export again')
    save(ROOT/'docs/snapshot.json',{'snapshot':'fixed_2025_synthetic','source_sha256':source_stamp,'mdl_sha256':hashlib.sha256((PROJECT/'target/mdl.json').read_bytes()).hexdigest(),'reporting_timezone':'Europe/London','wren_version':'0.15.0','duckdb_export_version':duckdb.__version__,'models':snapshots,'queries_sha256':hashlib.sha256((ROOT/'docs/queries.json').read_bytes()).hexdigest(),'comparison':manifest['tolerance'],'checks':'All exported rows, all fixed SQL queries and all saved verified examples passed Wren versus direct DuckDB and typed Parquet parity.'})
    report=ROOT/'target/dashboard'
    report.mkdir(parents=True,exist_ok=True)
    save(report/'query-results.json',query_results)
    print(f'PASS: {len(snapshots)} Wren outputs -> typed ZSTD Parquet; {len(query_results)} dashboard queries; {len(verified)} saved verified answers')


if __name__=='__main__':
    main()
