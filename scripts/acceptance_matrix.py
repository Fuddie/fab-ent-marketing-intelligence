"""Deterministic semantic acceptance; --live additionally tests exact NL questions.

The independent oracle reads physical marts, then ranks in Python. It never
translates the generated semantic SQL to obtain the expected answer.
"""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import duckdb
import marketing_ai as ai
from validate_wren import reference, compare

def cases(db):
    overview=reference(db,'SELECT * FROM raw_marts.mart_marketing__monthly_overview ORDER BY reporting_month')
    campaigns=reference(db,'SELECT * FROM raw_marts.mart_marketing__campaign_summary ORDER BY campaign_id')
    monthly=reference(db,'SELECT * FROM raw_marts.mart_marketing__campaign_monthly ORDER BY reporting_month,campaign_id')
    channels=reference(db,'SELECT * FROM raw_marts.mart_marketing__channel_monthly ORDER BY reporting_month,marketing_channel')
    def project(rows,cols): return [{c:r[c] for c in cols.split(', ')} for r in rows]
    def ranked(rows,key,n,metric):
        out=[]
        for month in sorted({r['reporting_month'] for r in rows}):
            ordered=sorted((r for r in rows if r['reporting_month']==month),key=lambda r:(r[metric] is None,-float(r[metric] or 0),r[key]))[:n]
            for i,r in enumerate(ordered,1):
                out.append(dict(r,monthly_rank=i))
        return out
    result=[]
    def add(q,model,sql,expected): result.append((q,model,sql,expected))
    add('What is total marketing spend?','MarketingMonthlyOverview',
        'SELECT SUM(spend_gbp) AS spend_gbp FROM MarketingMonthlyOverview ORDER BY spend_gbp',
        [{'spend_gbp':sum(r['spend_gbp'] for r in overview)}])
    cols='reporting_month, spend_gbp, attributed_net_revenue_gbp'
    add('How did spend and attributed net revenue change by month?','MarketingMonthlyOverview',
        f'SELECT {cols} FROM MarketingMonthlyOverview ORDER BY reporting_month',project(overview,cols))
    cols='campaign_id, campaign_name, attributed_net_revenue_gbp'
    add('Which five campaigns generated the highest attributed net revenue overall?','MarketingCampaignSummary',
        f'SELECT {cols} FROM MarketingCampaignSummary ORDER BY attributed_net_revenue_gbp DESC, campaign_id LIMIT 5',
        project(sorted(campaigns,key=lambda r:(-r['attributed_net_revenue_gbp'],r['campaign_id']))[:5],cols))
    for entity,model,rows,key,n,metric,question in [
        ('campaigns','MarketingCampaignMonthly',monthly,'campaign_id',3,'attributed_net_revenue_gbp','Top three campaigns based on attributed net revenue per month.'),
        ('channels','MarketingChannelMonthly',channels,'marketing_channel',3,'attributed_net_revenue_gbp','Top three channels based on attributed net revenue per month.'),
        ('channels','MarketingChannelMonthly',channels,'marketing_channel',1,'net_roas','Which channel had the strongest net ROAS per month?')]:
        cols=f'reporting_month, {key}, '+('campaign_name, ' if entity=='campaigns' else '')+metric
        sql=f'SELECT {cols} FROM {model} QUALIFY ROW_NUMBER() OVER (PARTITION BY reporting_month ORDER BY {metric} DESC NULLS LAST, {key}) <= {n} ORDER BY reporting_month, {metric} DESC, {key}'
        add(question,model,sql,project(ranked(rows,key,n,metric),cols+', monthly_rank'))
    cols='campaign_id, campaign_name, spend_gbp, attributed_orders'
    add('Which campaigns spent money without producing eligible conversions?','MarketingCampaignSummary',
        f'SELECT {cols} FROM MarketingCampaignSummary WHERE spend_gbp > 0 AND attributed_orders = 0 ORDER BY campaign_id',
        project([r for r in campaigns if r['spend_gbp']>0 and r['attributed_orders']==0],cols))
    cols='campaign_id, campaign_name, spend_gbp, lifetime_budget_gbp'
    add('Which campaigns exceeded their budgets?','MarketingCampaignSummary',
        f'SELECT {cols} FROM MarketingCampaignSummary WHERE spend_gbp > lifetime_budget_gbp ORDER BY campaign_id',
        project([r for r in campaigns if r['spend_gbp']>r['lifetime_budget_gbp']],cols))
    add('What percentage of eligible outcomes was unattributed?','MarketingMonthlyOverview',
        'SELECT 100.0 * SUM(unattributed_eligible_orders) / NULLIF(SUM(eligible_conversions), 0) AS unattributed_pct FROM MarketingMonthlyOverview ORDER BY unattributed_pct',
        [{'unattributed_pct':100.0*sum(r['unattributed_eligible_orders'] for r in overview)/sum(r['eligible_conversions'] for r in overview)}])
    add('How many first-observed acquisitions came from each channel?','MarketingChannelMonthly',
        'SELECT marketing_channel, SUM(first_observed_acquisitions) AS first_observed_acquisitions FROM MarketingChannelMonthly GROUP BY marketing_channel ORDER BY marketing_channel',
        [{'marketing_channel':key,'first_observed_acquisitions':sum(r['first_observed_acquisitions'] for r in channels if r['marketing_channel']==key)} for key in sorted({r['marketing_channel'] for r in channels})])
    groups=[]
    for key in sorted({r['marketing_channel'] for r in channels}):
        group=[r for r in channels if r['marketing_channel']==key]
        spend=sum(r['spend_gbp'] for r in group)
        revenue=sum(r['attributed_net_revenue_gbp'] for r in group)
        groups.append(dict(marketing_channel=key,spend_gbp=spend,attributed_net_revenue_gbp=revenue,net_roas=float(revenue/spend) if spend else None))
    add('Channel comparison and zero-denominator ROAS','MarketingChannelMonthly',
        'SELECT marketing_channel, SUM(spend_gbp) AS spend_gbp, SUM(attributed_net_revenue_gbp) AS attributed_net_revenue_gbp, SUM(attributed_net_revenue_gbp) / NULLIF(SUM(spend_gbp),0) AS net_roas FROM MarketingChannelMonthly GROUP BY marketing_channel ORDER BY marketing_channel',groups)
    scoped=[r for r in monthly if date(2025,3,1)<=r['reporting_month']<=date(2025,5,1) and r['marketing_channel']=='Meta Paid Social']
    add('Selected reporting months and channel before ranking','MarketingCampaignMonthly',
        "SELECT reporting_month, campaign_id, attributed_net_revenue_gbp FROM MarketingCampaignMonthly WHERE reporting_month >= DATE '2025-03-01' AND reporting_month <= DATE '2025-05-01' AND marketing_channel = 'Meta Paid Social' QUALIFY ROW_NUMBER() OVER (PARTITION BY reporting_month ORDER BY attributed_net_revenue_gbp DESC, campaign_id) <= 3 ORDER BY reporting_month, campaign_id",
        project(ranked(scoped,'campaign_id',3,'attributed_net_revenue_gbp'),'reporting_month, campaign_id, campaign_name, attributed_net_revenue_gbp, monthly_rank'))
    add('Empty aggregate retains NULL','MarketingMonthlyOverview',
        "SELECT SUM(spend_gbp) AS spend_gbp FROM MarketingMonthlyOverview WHERE reporting_month < DATE '2025-01-01' ORDER BY spend_gbp",[{'spend_gbp':None}])
    add('Empty result retains no invented values','MarketingCampaignMonthly',
        "SELECT campaign_id FROM MarketingCampaignMonthly WHERE spend_gbp < -999999 ORDER BY campaign_id",[])
    return result

def serial(value):
    if isinstance(value,(date,Decimal)):return str(value)
    raise TypeError(type(value).__name__)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    evidence=[]
    with duckdb.connect(str(ai.ROOT/'data/generated/fab_ent.duckdb'),read_only=True) as db:
        matrix=cases(db)
    if args.live:
        req=Request('http://127.0.0.1:4174/cache/clear',data=b'{}',headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:4173'})
        with urlopen(req,timeout=100) as response:json.load(response)
    for index,(q,model,sql,expected) in enumerate(matrix):
        item={'question':q,'model':model,'expected':expected}
        try:
            sql=ai.governed_sql(sql,model)
            actual=ai.wren(sql,time.monotonic()+90)
            ai.verify(sql,model,actual,time.monotonic()+90)
            # Normalize only DATE transport, according to independent oracle types.
            for a,e in zip(actual,expected):
                for k,v in e.items():
                    if isinstance(v,date):a[k]=date.fromisoformat(str(a[k])[:10])
            compare(actual,expected,q)
            if 'Top three' in q:
                assert len(actual)==36 and set(Counter(r['reporting_month'] for r in actual).values())=={3}
                assert max(r['monthly_rank'] for r in actual)==3
            item.update(status='PASS',semantic_status='PASS',semantic_sql=sql,actual=actual,row_count=len(actual))
            if args.live and index < 10:
                req=Request('http://127.0.0.1:4174/ask',data=json.dumps({'question':q}).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:4173'})
                with urlopen(req,timeout=100) as response:answer=json.load(response)
                item['live_actual']=answer['rows']
                item['live_semantic_sql']=answer['semantic_sql']
                # Deliberately strict contract: column order, grain and ordering too.
                live=answer['rows']
                for a,e in zip(live,expected):
                    for k,v in e.items():
                        if isinstance(v,date) and k in a:a[k]=date.fromisoformat(str(a[k])[:10])
                compare(live,expected,q+' live')
                item['live_status']='PASS'
        except Exception as exc:
            item.update(status='FAIL',error=str(exc))
        evidence.append(item)
        print(q,item['status'],item.get('error',''),flush=True)
    rejections=[]
    if args.live:
        for label,body in [('unsupported',json.dumps({'question':'What will the weather be tomorrow?'}).encode()),
                           ('empty question',b'{"question":""}'),('malformed JSON',b'{"question":')]:
            req=Request('http://127.0.0.1:4174/ask',data=body,headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:4173'})
            try:
                with urlopen(req,timeout=100) as response:code=response.status
            except HTTPError as exc:code=exc.code
            rejections.append({'case':label,'expected_http':400,'actual_http':code,'status':'PASS' if code==400 else 'FAIL'})
            print(label,code,flush=True)
    path=ai.ROOT/('target/acceptance-live.json' if args.live else 'target/acceptance-matrix.json')
    path.write_text(json.dumps({'mode':'live' if args.live else 'deterministic Wren (no NL generation)','cases':evidence,'rejections':rejections},default=serial,indent=2),encoding='utf-8')
    if any(r['status']!='PASS' for r in evidence+rejections):raise SystemExit(1)

if __name__=='__main__':main()
