"""Campaign month contract, direct daily oracle and exact-question regression.

--live additionally requires a running local Wren/Codex service and validates
its actual generated answer; offline checks never claim a live AI/Wren pass.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import duckdb
import yaml
import marketing_ai as ai
from validate_wren import reference, compare

ROOT=Path(__file__).resolve().parents[1]
QUESTION='Top three campaigns based on revenue generation per month'
MODEL='MarketingCampaignMonthly'
METRICS=['spend_gbp','eligible_conversions','attributed_gross_merchandise_revenue_gbp','attributed_net_revenue_gbp']

def validate_rows(rows,expected):
    assert len(rows)==36
    assert len({str(r['reporting_month']) for r in rows})==12
    assert set(Counter(str(r['reporting_month']) for r in rows).values())=={3}
    assert len({(str(r['reporting_month']),r['campaign_id']) for r in rows})==36
    assert [(str(r['reporting_month']),r['campaign_id']) for r in rows]==[(str(r['reporting_month']),r['campaign_id']) for r in expected]
    for a,e in zip(rows,expected,strict=True):
        assert a['campaign_name']==e['campaign_name']
        assert abs(float(a['attributed_net_revenue_gbp'])-float(e['attributed_net_revenue_gbp']))<1e-8

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    semantic=(ROOT/'wren/validation/11_top_campaigns_monthly.wren.sql').read_text().strip()
    direct=(ROOT/'wren/validation/11_top_campaigns_monthly.duckdb.sql').read_text()
    # Independently aggregate and sort the daily rows in Python (no ranking SQL).
    with duckdb.connect(str(ROOT/'data/generated/fab_ent.duckdb'),read_only=True) as db:
        daily=reference(db,'SELECT * FROM raw_marts.mart_marketing__campaign_daily ORDER BY reporting_date, campaign_id')
        groups={}
        for row in daily:
            key=(row['reporting_date'].replace(day=1),row['campaign_id'])
            if key not in groups:groups[key]={'reporting_month':key[0],'campaign_id':key[1],'campaign_name':row['campaign_name'],'marketing_channel':row['marketing_channel'],**{m:0 for m in METRICS}}
            for m in METRICS:groups[key][m]+=row[m]
        expected_all=[]
        for key,row in sorted(groups.items()):
            row['net_roas']=float(row['attributed_net_revenue_gbp']/row['spend_gbp']) if row['spend_gbp'] else None
            expected_all.append(row)
        actual=reference(db,'SELECT * FROM raw_marts.mart_marketing__campaign_monthly ORDER BY reporting_month,campaign_id')
        compare(actual,expected_all,'monthly versus independently accumulated daily rows')
        expected=[]
        for month in sorted({k[0] for k in groups}):
            expected.extend(sorted([r for r in expected_all if r['reporting_month']==month],key=lambda r:(-r['attributed_net_revenue_gbp'],r['campaign_id']))[:3])
        rows=reference(db,direct);validate_rows(rows,expected)
        governed=ai.governed_sql(semantic,MODEL)
        validate_rows(reference(db,governed.replace(MODEL,'raw_marts.mart_marketing__campaign_monthly')),expected)
        filters={'start':'2025-03','end':'2025-05','channel':'Meta Paid Social','campaign':''}
        scoped=ai.governed_sql(semantic,MODEL,filters)
        scoped_rows=reference(db,scoped.replace(MODEL,'raw_marts.mart_marketing__campaign_monthly'))
        scoped_expected=[]
        for month in sorted({r['reporting_month'] for r in expected_all if '2025-03' <= str(r['reporting_month'])[:7] <= '2025-05'}):
            scoped_expected.extend(sorted([r for r in expected_all if r['reporting_month']==month and r['marketing_channel']=='Meta Paid Social'],key=lambda r:(-r['attributed_net_revenue_gbp'],r['campaign_id']))[:3])
        assert [(r['reporting_month'],r['campaign_id']) for r in scoped_rows]==[(str(r['reporting_month']),r['campaign_id']) for r in scoped_expected]
        filtered=ai.governed_sql(semantic,MODEL,dict(filters,campaign='CAM-0001'))
        assert "campaign_id = 'CAM-0001'" in filtered
    with duckdb.connect() as fixture:
        tied=fixture.execute("SELECT campaign_id FROM (VALUES ('CAM-4', 10), ('CAM-2', 10), ('CAM-3', 10), ('CAM-1', 10)) t(campaign_id, revenue) QUALIFY ROW_NUMBER() OVER (ORDER BY revenue DESC, campaign_id ASC) <= 3 ORDER BY revenue DESC, campaign_id ASC").fetchall()
        assert tied==[('CAM-1',),('CAM-2',),('CAM-3',)]
    meta=yaml.safe_load((ROOT/'wren/models'/MODEL/'metadata.yml').read_text())
    assert {c['name'] for c in meta['columns'] if not c.get('is_calculated')}==set(actual[0])
    for phrase in ['per month','monthly','each month']:
        assert phrase in ai.context()
    evidence={'question':QUESTION,'status':'PASS: direct DuckDB and independent daily accumulation; no Wren or live AI execution','monthly_rows':len(actual),'result_rows':len(rows),'campaigns_per_month':3,'tie_breaker':'campaign_id ASC','semantic_sql':semantic,'rows':rows}
    if args.live:
        from test_marketing_ai_live import post
        post('/cache/clear',{})
        for question in [QUESTION,'Top three campaigns based on revenue generation monthly','Top three campaigns based on revenue generation each month']:
            answer=post('/ask',{'question':question})
            assert answer['model']==MODEL and not answer['cached']
            validate_rows(answer['rows'],expected)
            assert 'reporting_date' not in answer['rows'][0]
        evidence['live_status']='PASS: all three question phrasings, Wren and DuckDB parity'
    out=ROOT/'target/campaign-monthly';out.mkdir(parents=True,exist_ok=True)
    (out/'validation.json').write_text(json.dumps(evidence,default=str,indent=2)+'\n')
    print(evidence['status']);print(f'{len(actual)} campaign-month rows; 36 ranked rows; exactly three in each of 12 months; scoped filters PASS')

if __name__=='__main__':main()
