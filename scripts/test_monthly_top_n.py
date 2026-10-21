"""Monthly ranking regression against independently sorted governed rows."""
from collections import Counter
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import sys
import duckdb
import marketing_ai as ai
from validate_wren import reference

WREN = '--wren' in sys.argv
if WREN:
    sys.argv.remove('--wren')


def plan(entity, n=3, where=''):
    model = 'MarketingCampaignMonthly' if entity == 'campaigns' else 'MarketingChannelMonthly'
    key = 'campaign_id' if entity == 'campaigns' else 'marketing_channel'
    columns = f'reporting_month, {key}, attributed_net_revenue_gbp'
    sql = (f'SELECT {columns} FROM {model} {where} '
           f'QUALIFY ROW_NUMBER() OVER (PARTITION BY reporting_month '
           f'ORDER BY attributed_net_revenue_gbp DESC, {key} ASC) <= {n} '
           f'ORDER BY reporting_month, attributed_net_revenue_gbp DESC, {key}')
    return dict(model=model, sql=sql, assumptions=[], ordering='month, revenue, entity', rejection='')


class MonthlyTopTests(unittest.TestCase):
    def test_acquisition_scope_retains_unattributed_unless_explicit(self):
        wrong='SELECT marketing_channel, SUM(attributed_first_observed_acquisitions) AS attributed_first_observed_acquisitions FROM MarketingChannelMonthly GROUP BY marketing_channel ORDER BY marketing_channel'
        with self.assertRaisesRegex(ai.Invalid,'retaining Unattributed'):
            ai.validate_question_intent(wrong,'How many first-observed acquisitions came from each channel?')
        ai.validate_question_intent(wrong,'Show attributed first-observed acquisitions per channel')
        ai.validate_question_intent(wrong.replace('attributed_first_observed','first_observed'),'How many first-observed acquisitions came from each channel?')

    def test_missing_or_wrong_monthly_bound_is_repaired_once(self):
        self.assertEqual(ai.monthly_rank_intent('Top five channels each month'),5)
        self.assertEqual(ai.monthly_rank_intent('Which channel is strongest per month?'),1)
        self.assertIsNone(ai.monthly_rank_intent('How did spend change by month?'))
        bad=plan('channels',3)
        fixed=plan('channels',1)
        with tempfile.TemporaryDirectory() as tmp, patch.object(ai,'RUNTIME',Path(tmp)), patch.object(ai,'ensure_current_snapshot'), patch.object(ai,'codex',side_effect=[bad,fixed]) as generate, patch.object(ai,'wren',return_value=[]) as execute, patch.object(ai,'verify',return_value='verified'):
            ai.answer({'question':'Which channel had the strongest revenue per month?'})
            self.assertEqual(generate.call_count,2)
            self.assertEqual(execute.call_count,1)
            self.assertIn('PLAN CORRECTION',generate.call_args.args[0])
        with self.assertRaises(ai.Invalid):
            ai.validate_rank_intent(ai.governed_sql(bad['sql'],bad['model']),1)

    def test_ties_rank_exposure_and_global_limit(self):
        p=plan('channels')
        sql=ai.governed_sql(p['sql'].replace('ROW_NUMBER()', 'DENSE_RANK()').replace(', marketing_channel ASC',''),p['model'])
        self.assertIn('AS monthly_rank',sql)
        self.assertIn('ORDER BY reporting_month ASC, monthly_rank ASC',sql)
        with duckdb.connect() as db:
            db.execute("CREATE TABLE MarketingChannelMonthly AS SELECT DATE '2025-01-01' AS reporting_month, channel AS marketing_channel, 10 AS attributed_net_revenue_gbp FROM (VALUES ('D'),('B'),('C'),('A')) t(channel)")
            rows=reference(db,sql)
            self.assertEqual([r['marketing_channel'] for r in rows],['A','B','C'])
            self.assertEqual([r['monthly_rank'] for r in rows],[1,2,3])
        with self.assertRaises(ai.Invalid):
            ai.governed_sql(p['sql']+' LIMIT 3',p['model'])
        strongest=ai.governed_sql(plan('channels',1)['sql'].replace('<= 1','= 1'),p['model'])
        self.assertIn('<= 1',strongest)

    @unittest.skipUnless(WREN, 'requires --wren')
    def test_service_pipeline_with_real_snapshot_wren_and_oracle(self):
        p=plan('channels')
        with tempfile.TemporaryDirectory() as tmp, patch.object(ai,'RUNTIME',Path(tmp)), \
             patch.object(ai,'codex',return_value=p) as generate:
            payload={'question':'Top three channels by revenue each month'}
            result=ai.answer(payload)
            self.assertEqual(len(result['rows']),36)
            self.assertEqual(set(Counter(r['reporting_month'] for r in result['rows']).values()),{3})
            self.assertIn('PASS:',result['validation'])
            self.assertFalse(result['cached'])
            self.assertTrue(ai.answer(payload)['cached'])
            generate.assert_called_once()

    def test_partition_scope_and_large_results(self):
        with duckdb.connect(str(ai.ROOT/'data/generated/fab_ent.duckdb'),read_only=True) as db:
            for entity in ['campaigns','channels']:
                for n in [1,3,5,100]:
                    p = plan(entity,n)
                    key = 'campaign_id' if entity == 'campaigns' else 'marketing_channel'
                    physical = 'raw_marts.mart_marketing__'+ai.MODELS[p['model']][0]
                    for filters in [None,dict(start='2025-03',end='2025-05',channel='Meta Paid Social',campaign='')]:
                        sql=ai.governed_sql(p['sql'],p['model'],filters)
                        rows=reference(db,sql.replace(p['model'],physical))
                        campaign_name = ', campaign_name' if entity == 'campaigns' else ''
                        source=reference(db,f'SELECT reporting_month, {key}{campaign_name}, attributed_net_revenue_gbp FROM {physical}')
                        if filters:
                            # Independent scope oracle, before Python ranking.
                            source=reference(db,f"SELECT reporting_month, {key}{campaign_name}, attributed_net_revenue_gbp FROM {physical} WHERE reporting_month >= DATE '2025-03-01' AND reporting_month < DATE '2025-06-01' AND marketing_channel = 'Meta Paid Social'")
                        expected=[]
                        for month in sorted({r['reporting_month'] for r in source}):
                            ranked=sorted([r for r in source if r['reporting_month']==month],key=lambda r:(-r['attributed_net_revenue_gbp'],r[key]))[:n]
                            expected.extend(dict(r, monthly_rank=i) for i,r in enumerate(ranked,1))
                        self.assertEqual(rows,expected)
                        if entity=='campaigns' and n==100 and not filters:
                            self.assertEqual(len(rows),112)
                        if WREN and n==3 and not filters:
                            deadline=time.monotonic()+90
                            actual=ai.wren(sql,deadline)
                            ai.verify(sql,p['model'],actual,deadline)
                            self.assertEqual(len(actual),36)

    def test_question_constraints_reach_planner(self):
        q='Top three channels by revenue each month in March excluding Google Paid Search'
        p=plan('channels',3,"WHERE reporting_month = DATE '2025-03-01' AND marketing_channel <> 'Google Paid Search'")
        with tempfile.TemporaryDirectory() as tmp, patch.object(ai,'RUNTIME',Path(tmp)), patch.object(ai,'ensure_current_snapshot'), patch.object(ai,'codex',return_value=p) as generate, patch.object(ai,'wren',return_value=[]), patch.object(ai,'verify',return_value='verified'):
            result=ai.answer({'question':q})
            generate.assert_called_once()
            self.assertIn(q,generate.call_args.args[0])
            self.assertIn("marketing_channel <> 'Google Paid Search'",result['semantic_sql'])
            self.assertIn('2025-03-01',result['semantic_sql'])


if __name__=='__main__':
    unittest.main()
