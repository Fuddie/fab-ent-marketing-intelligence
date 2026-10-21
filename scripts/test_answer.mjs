import assert from 'node:assert/strict';
import {test} from 'node:test';
import {format,label,renderAnswer,unit} from '../docs/answer.mjs';

test('monthly rank displays as an integer',()=>{
 assert.equal(label('monthly_rank'),'Monthly rank');
 assert.equal(unit('monthly_rank'),'integer');
 assert.equal(format(3,unit('monthly_rank')),'3');
});

test('business units handle decimals, zero, negative, NULL and dates',()=>{
 for (const [value,type,expected] of [
  ['1234567.8','currency','£1,234,567.80'],[0,'currency','£0.00'],[-12.5,'currency','-£12.50'],
  [12.5,'percent','12.50%'],[2.5,'multiple','2.50x'],[12000,'integer','12,000'],
  [null,'currency','N/A'],['2025-03-01','date','Mar 2025'],['2025-03-15','date','15 Mar 2025'],
  ['2025-03','date','Mar 2025'],['CAM-0001','text','CAM-0001']]) assert.equal(format(value,type),expected);
 assert.equal(label('net_revenue_gbp'),'Net revenue GBP');
 assert.equal(label('net_roas'),'Net ROAS');
});
const base={rows:[{total:'1234.5'}],columns:[{key:'total',unit:'currency'}],assumptions:['Snapshot'],semantic_sql:'SELECT <unsafe>',duration_ms:42};
test('saved examples share presentation and identify their source',()=>{
 const html=renderAnswer({...base,source:'saved'});
 assert.match(html,/Saved verified example/);
 assert.match(html,/dashboard filters do not apply/);
 assert.doesNotMatch(html,/New answer|Codex model|Reasoning|Duration/);
 assert.doesNotMatch(html,/<table/);
});
test('scalar is a single KPI with collapsed provenance and no raw table',()=>{
 const html=renderAnswer(base);
 assert.match(html,/£1,234.50/);assert.doesNotMatch(html,/<table/);
 assert.match(html,/Verified by Wren/);assert.match(html,/<summary>Technical details/);
 assert.doesNotMatch(html,/<details[^>]*open/);assert.match(html,/SELECT &lt;unsafe&gt;/);
 assert.match(html,/1 returned/);
});
test('multi-row results and hostile values are escaped, NULL and empty are explicit',()=>{
 const html=renderAnswer({...base,rows:[{marketing_channel:'<img src=x>',spend_gbp:12.5},{marketing_channel:'Direct',spend_gbp:null}]});
 assert.match(html,/<table/);assert.match(html,/Marketing channel/);assert.match(html,/£12.50/);
 assert.match(html,/N\/A/);assert.doesNotMatch(html,/<img/);
 assert.match(renderAnswer({...base,rows:[]}),/No matching data/);
 assert.doesNotMatch(renderAnswer({...base,rows:[]}),/<table/);
});

test('monthly results display Reporting month',()=>{const html=renderAnswer({...base,rows:[{reporting_month:'2025-01-01',campaign_id:'CAM-0001',attributed_net_revenue_gbp:50}]});assert.match(html,/Reporting month/);assert.doesNotMatch(html,/Reporting date/);});
