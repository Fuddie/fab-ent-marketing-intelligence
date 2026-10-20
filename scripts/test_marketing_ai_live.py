"""Five uncached HTTP questions, each also checked against separate authored SQL."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from decimal import Decimal
import duckdb
from validate_wren import reference, records, compare

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('What is total marketing spend?', 'SELECT SUM(spend_gbp) AS spend_gbp FROM raw_marts.mart_marketing__monthly_overview'),
 ('How did spend and net revenue change by month?', 'SELECT CAST(reporting_month AS VARCHAR) AS reporting_month, spend_gbp, net_revenue_gbp FROM raw_marts.mart_marketing__monthly_overview ORDER BY reporting_month'),
 ('Which five campaigns generated the highest net revenue?', 'SELECT campaign_id, campaign_name, net_revenue_gbp FROM raw_marts.mart_marketing__campaign_summary ORDER BY net_revenue_gbp DESC, campaign_id LIMIT 5'),
 ('Which campaigns spent money without producing eligible conversions?', 'SELECT campaign_id, campaign_name, spend_gbp, attributed_orders FROM raw_marts.mart_marketing__campaign_summary WHERE spend_gbp > 0 AND attributed_orders=0 ORDER BY campaign_id'),
 ('Which campaigns exceeded their budgets?', 'SELECT campaign_id, campaign_name, spend_gbp, lifetime_budget_gbp FROM raw_marts.mart_marketing__campaign_summary WHERE spend_gbp > lifetime_budget_gbp ORDER BY campaign_id')]

def post(path,payload):
    req=Request('http://127.0.0.1:4174'+path,data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:4173'})
    with urlopen(req,timeout=100) as r:return json.load(r)

if __name__=='__main__':
    post('/cache/clear',{})
    evidence=[]
    for question,direct in CASES:
        try:
            a=post('/ask',{'question':question})
            assert not a['cached']
            with duckdb.connect(str(ROOT/'data/generated/fab_ent.duckdb'),read_only=True) as db:
                expected=reference(db,direct)
            if question == CASES[0][0]:
                assert Decimal(str(next(iter(a['rows'][0].values())))) == expected[0]['spend_gbp']
            else:
                key='reporting_month' if question == CASES[1][0] else 'campaign_id'
                actual={str(r[key]):r for r in a['rows']}
                assert set(actual)=={str(r[key]) for r in expected}
                for row in expected:
                    for col,value in row.items():
                        got=actual[str(row[key])][col]
                        if isinstance(value,(int,float,Decimal)):
                            assert abs(float(got)-float(value))<1e-8,(col,got,value)
                        else: assert str(got)==str(value),(col,got,value)
            a['separate_oracle']='PASS: independently authored direct SQL'
            a['separate_oracle_sql']=direct
            evidence.append(a)
            print(question, json.dumps(a),flush=True)
        except Exception as e:
            print('FAIL',question,e.read().decode() if isinstance(e,HTTPError) else repr(e),flush=True)
            evidence.append({'question':question,'error':str(e)})
        (ROOT/'target/marketing-ai/live-results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    if len(evidence)!=5 or any('error' in item for item in evidence):
        raise SystemExit('Live questions failed; inspect target/marketing-ai/live-results.json')
