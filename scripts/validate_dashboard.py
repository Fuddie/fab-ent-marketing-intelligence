"""Exhaustive filter oracle: browser JS compared with direct governed DuckDB SQL.

SQL executed in the browser is fixed and independently Wren validated at export.
Filters do not change SQL. All 144 ordered month-bound pairs (including reversed,
empty ranges), seven channel options and 25 campaign options are tested.
"""
import hashlib
import json
import math
import subprocess
from decimal import Decimal
from pathlib import Path

import duckdb
from validate_wren import ROOT, MODELS, require, reference, compare

FIELDS = {'spend':'spend_gbp','revenue':'net_revenue_gbp','attributed_revenue':'attributed_net_revenue_gbp',
          'conversions':'eligible_conversions','attributed_orders':'attributed_orders',
          'acquisitions':'first_observed_acquisitions','paid_acquisitions':'attributed_first_observed_acquisitions',
          'unmatched_orders':'unattributed_eligible_orders','unmatched_revenue':'unattributed_net_revenue_gbp',
          'budget':'allocated_budget_gbp','negative_inputs':'negative_input_count'}


def close(a,b,label):
    if a is None or b is None:
        require(a is None and b is None,label+': NULL mismatch')
    elif isinstance(a,dict):
        for key in b:
            require(key in a,label+': missing '+key)
            close(a[key],b[key],label+'/'+key)
    elif isinstance(a,list):
        require(len(a)==len(b),label+': row count')
        for i,(x,y) in enumerate(zip(a,b,strict=True)):
            close(x,y,label+f'/{i}')
    elif isinstance(b,int):
        require(a==b,f'{label}: exact count mismatch {a} != {b}')
    elif isinstance(b,(float,Decimal)):
        require(math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8),f'{label}: {a} != {b}')
    else:
        require(a==b,label+': value/order mismatch')


def main():
    dest=ROOT/'target/dashboard'
    dest.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'docs/queries.json').read_text())
    snapshots=json.loads((ROOT/'docs/snapshot.json').read_text())
    require(snapshots['queries_sha256']==hashlib.sha256((ROOT/'docs/queries.json').read_bytes()).hexdigest(),'SQL changed; regenerate snapshots')
    expected_counts=[3022,24,72,12]
    with duckdb.connect(str(ROOT/'data/generated/fab_ent.duckdb'),read_only=True) as db:
        for m,count in zip(snapshots['models'],expected_counts,strict=True):
            path=ROOT/'docs/data'/f"{m['model']}.parquet"
            require(hashlib.sha256(path.read_bytes()).hexdigest()==m['sha256'],'Checksum mismatch')
            schema=db.execute(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()
            require([{'name':c,'type':t} for c,t,*_ in schema]==m['schema'], 'Schema drift: '+str([(a,b[:2]) for a,b in zip(m['schema'],schema) if a['type']!=b[1]]))
            require(db.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]==count==m['rows'],'Row count drift')
            physical='fab_ent.raw_marts.mart_marketing__'+MODELS[m['model']][0]
            cols=', '.join(f'CAST("{c["name"]}" AS VARCHAR) AS "{c["name"]}"' if c['type']=='DATE' else '"'+c['name']+'"' for c in m['schema'])
            ordered=' ORDER BY '+', '.join(m['keys'])
            compare(reference(db,f"SELECT {cols} FROM read_parquet('{path.as_posix()}')"+ordered),reference(db,f'SELECT {cols} FROM {physical}'+ordered),'Whole-row snapshot parity')
        data={q['id']:reference(db,q['sql'].replace(q['model'],'fab_ent.raw_marts.mart_marketing__'+MODELS[q['model']][0])) for q in manifest['queries']}
        (dest/'query-results.json').write_text(json.dumps(data,default=str),encoding='utf-8')
        months=sorted({r['month'][:7] for r in data['overview']})
        channels=['']+sorted({r['marketing_channel'] for r in data['channels']})
        campaigns=['']+[r['campaign_id'] for r in data['inventory']]
        cases=[{'start':a,'end':b,'channel':c,'campaign':d} for a in months for b in months for c in channels for d in campaigns]
        (dest/'filter-cases.json').write_text(json.dumps(cases),encoding='utf-8')
        subprocess.run(['node','tests/dashboard_metrics.mjs'],cwd=ROOT,check=True)
        actual=json.loads((dest/'filter-results.json').read_text())
        # Vectorized independent physical-mart SQL: join the full filter matrix
        # to facts once per intended grain. Never read the browser query manifest
        # or JS outputs to construct the numeric reference.
        cases_path=(dest/'filter-cases.json').as_posix()
        db.execute(f"CREATE TEMP TABLE filter_cases AS SELECT row_number() OVER () - 1 AS case_id, * FROM read_json_auto('{cases_path}')")
        aggregates=', '.join(f'SUM(m.{column}) AS {alias}' for alias,column in FIELDS.items())
        formulas=', SUM(m.attributed_net_revenue_gbp)/NULLIF(SUM(m.spend_gbp),0) AS roas, SUM(m.spend_gbp)/NULLIF(SUM(m.attributed_first_observed_acquisitions),0) AS cac, 100.0*SUM(m.attributed_orders)/NULLIF(SUM(m.eligible_conversions),0) AS attribution, 100.0*SUM(m.spend_gbp)/NULLIF(SUM(m.allocated_budget_gbp),0) AS utilisation'
        expected={kind:{} for kind in ['kpis','monthly','channels','performance','global']}
        def batch(kind,suffix,scope):
            date='m.reporting_date' if suffix=='campaign_daily' else 'm.reporting_month'
            month_expr=f"CAST(CAST(date_trunc('month', {date}) AS DATE) AS VARCHAR)" if suffix=='campaign_daily' else 'CAST(m.reporting_month AS VARCHAR)'
            dimension={'monthly':month_expr+' AS month','channels':'m.marketing_channel','performance':'m.campaign_id, m.campaign_name'}.get(kind)
            conditions=[f"{date} >= CAST(f.start || '-01' AS DATE)",f"{date} < CAST(f.\"end\" || '-01' AS DATE) + INTERVAL 1 MONTH"]
            if kind!='global':
                if suffix!='monthly_overview':conditions.append("(f.channel='' OR m.marketing_channel=f.channel)")
                if suffix=='campaign_daily':conditions.append("(f.campaign='' OR m.campaign_id=f.campaign)")
            count_dims=2 if kind=='performance' else 1 if dimension else 0
            positions=', '.join(str(i) for i in range(1,count_dims+2))
            sql='SELECT f.case_id, '+(dimension+', ' if dimension else '')+aggregates+formulas+' FROM filter_cases f '+('JOIN ' if dimension else 'LEFT JOIN ')+f'fab_ent.raw_marts.mart_marketing__{suffix} m ON '+' AND '.join(conditions)+' WHERE '+scope+' GROUP BY '+positions+' ORDER BY '+positions
            for row in reference(db,sql):
                case_id=row.pop('case_id')
                if dimension:expected[kind].setdefault(case_id,[]).append(row)
                else:expected[kind][case_id]=row
        for kind in ['kpis','monthly']:
            batch(kind,'campaign_daily',"f.campaign<>''")
            batch(kind,'channel_monthly',"f.campaign='' AND f.channel<>''")
            batch(kind,'monthly_overview',"f.campaign='' AND f.channel=''")
        batch('channels','campaign_daily',"f.campaign<>''")
        batch('channels','channel_monthly',"f.campaign=''")
        batch('performance','campaign_daily','TRUE')
        batch('global','monthly_overview','TRUE')
        for i,(f,r) in enumerate(zip(cases,actual,strict=True)):
            for kind in ['kpis','monthly','channels','performance']:
                close(r[kind],expected[kind].get(i,[]),f'case {i} {kind}')
            close(r['global'],expected['global'][i],'global context')
            perf=expected['performance'].get(i,[])
            top=sorted(perf,key=lambda x:(-(float(x['roas']) if x['roas'] is not None else -math.inf),x['campaign_id']))[:5]
            close(r['top'],top,'top ordering')
            close(r['spendAlerts'],[x for x in perf if x['spend']>0 and x['attributed_orders']==0],'spend alerts')
            close(r['budgetAlerts'],[x for x in perf if x['utilisation'] is not None and x['utilisation']>100],'budget alerts')
            if i and i%5000==0:print(f'Validated {i}/{len(cases)} combinations',flush=True)
        baseline=actual[cases.index({'start':months[0],'end':months[-1],'channel':'','campaign':''})]
        for field in ['spend','attributed_revenue','attributed_orders','paid_acquisitions']:
            close(baseline['kpis'][field],sum(float(x[field]) for x in baseline['performance']),'campaign/website reconciliation')
        close(baseline['kpis']['revenue'],float(baseline['global']['attributed_revenue'])+float(baseline['global']['unmatched_revenue']),'revenue partition')
        report={'status':'PASS','filter_combinations':len(cases),'fixed_sql_queries':len(manifest['queries']),'wren_validation':'All fixed browser SQL executed through Wren 0.15.0 and compared with separate direct DuckDB SQL during export. Whole-row semantic parity establishes all possible filter subsets. No SQL is generated by user filters. Exhaustive JS filtering and calculation results are compared with direct physical-mart SQL here.','coverage':'12 start months × 12 end months × 7 channel choices × 25 campaign choices. Includes reversed ranges, no data, conflicting dimensions, unpaid channels, zero denominators, all rankings, monthly/channel/campaign tables, alerts, date-only context.','tolerance':manifest['tolerance'],'ordering':manifest['ordering'],'schemas_and_rows':'3022 / 24 / 72 / 12; every typed row matches governed marts including stored NULLs.','registration_ddl':'CREATE VIEW "{allowlisted_model}" AS SELECT * FROM read_parquet(\'{allowlisted_model}.parquet\'); local snapshot setup only, not a semantic business query.','baseline_kpis':baseline['kpis']}
        (ROOT/'docs/validation.json').write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
        print(f"PASS: snapshot schemas/rows/checksums; 4 fixed SQL queries; {len(cases)} combinations; all KPIs, tables, rankings and alerts versus direct SQL")


if __name__=='__main__':
    main()
