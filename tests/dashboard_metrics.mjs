// Pure browser calculation and formatter checks; no DOM or network needed.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {select, totals, cash, count, pct, multiple, esc, ratio, month} from '../docs/metrics.mjs';
assert.equal(cash(null),'N/A');assert.equal(cash(0),'£0.00');assert.equal(cash(1234.5),'£1,234.50');assert.equal(cash(-2.5),'-£2.50');
assert.equal(pct(null),'N/A');assert.equal(pct(0),'0.00%');assert.equal(pct(64.587),'64.59%');assert.equal(multiple(null),'N/A');assert.equal(count(null),'N/A');
assert.equal(ratio(1,0),null);assert.equal(ratio(0,0),null);assert.equal(ratio(null,1),null);assert.equal(ratio(0,3),0);
assert.equal(totals([]).roas,null);assert.equal(totals([]).spend,null);assert.equal(month('2025-07'),'Jul 2025');
const payload='<img src=x onerror="alert(1)"> & \' injection';
assert(!esc(payload).includes('<'));assert(esc(payload).includes('&lt;img'));assert(esc(payload).includes('&quot;'));assert(esc(payload).includes('&#39;'));
const data=JSON.parse(readFileSync('target/dashboard/query-results.json','utf8'));
const cases=JSON.parse(readFileSync('target/dashboard/filter-cases.json','utf8'));
const result=cases.map(filters=>select(data,filters));
// Reconcile each filtered result from independent grains before oracle comparison.
for(const r of result){
  for(const key of ['spend','revenue','conversions','acquisitions','attributed_revenue','budget']){
    if(r.kpis[key]!==null)assert(Math.abs(r.monthly.reduce((n,m)=>n+m[key],0)-r.kpis[key])<1e-7,key);
  }
}
writeFileSync('target/dashboard/filter-results.json',JSON.stringify(result));
console.log(`PASS: formatting, NULL/zero denominators, HTML escaping, monthly KPI reconciliations; ${cases.length} filter results`);
