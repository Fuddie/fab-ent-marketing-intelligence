import {select, cash, count, pct, multiple, month, esc} from './metrics.mjs';
import {renderAnswer} from './answer.mjs';

const $ = id => document.getElementById(id);
const VERSION='1.29.0';
const CDN=`https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${VERSION}/dist/`;
let connection, data, report, startupFailed=false;
const controls=['start','end','channel','campaign','reset'];
function busy(value){controls.forEach(id=>$(id).disabled=value);$('dashboard').setAttribute('aria-busy',String(value));}
async function json(path){const r=await fetch(path);if(!r.ok)throw new Error(`Missing snapshot or manifest: ${path} (HTTP ${r.status})`);return r.json();}
function failure(e){startupFailed=true;$('dashboard').hidden=true;window.dashboardState={ready:false};$('error').hidden=false;$('error-message').textContent=`${e.message || e}. Check internet access to the pinned public CDN and ensure all docs/data snapshot files are served. No substitute KPI values are shown.`;$('status').textContent='Snapshot unavailable';busy(true);}
export function table(headers,rows,caption){
  const row=(values,head=false)=>`<tr>${values.map((v,i)=>`<${head?'th scope="col"':i===0?'th scope="row"':'td'}>${esc(v)}</${head||i===0?'th':'td'}>`).join('')}</tr>`;
  return `<div class="table-wrap" tabindex="0" role="region" aria-label="${esc(caption)}; scroll horizontally if needed"><table><caption>${esc(caption)}</caption><thead>${row(headers,true)}</thead><tbody>${rows.length?rows.map(r=>row(r)).join(''):`<tr><td colspan="${headers.length}" class="empty">No matching data.</td></tr>`}</tbody></table></div>`;
}
function barRows(rows,label,value,format,note){const max=Math.max(...rows.map(value).filter(v=>v!=null),1);return rows.length?rows.map(r=>`<div class="bar-row"><div class="bar-head"><span>${esc(label(r))}<small>${esc(note(r))}</small></span><strong>${esc(format(value(r)))}</strong></div><div class="track" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,Number(value(r)??0)/max*100))}%"></i></div></div>`).join(''):'<p class="empty">No matching data.</p>';}
function chart(rows,kind){
  if(!rows.length)return '<p class="empty">No matching data.</p>';
  const w=660,h=260,l=62,r=15,top=24,bottom=220,slot=(w-l-r)/rows.length;
  const vals=rows.flatMap(d=>kind==='money'?[d.spend,d.revenue]:[d.roas]).filter(v=>v!=null);
  const max=Math.max(...vals,1)*1.15,min=Math.min(0,...vals)*1.15, y=v=>bottom-(v-min)/(max-min)*(bottom-top);
  const label=v=>kind==='money'?`£${Math.round(v/1000)}k`:`${v.toFixed(1)}×`;
  let svg='';for(let i=0;i<=4;i++){const v=min+(max-min)*i/4;svg+=`<line class="grid" x1="${l}" y1="${y(v)}" x2="${w-r}" y2="${y(v)}"/><text x="${l-8}" y="${y(v)+4}" text-anchor="end">${label(v)}</text>`;}
  let previous=null;
  rows.forEach((d,i)=>{const x=l+slot*(i+.5),bw=Math.min(14,slot*.27),tip=`${month(d.month)}: ${kind==='money'?`Spend ${cash(d.spend)}, net revenue ${cash(d.revenue)}`:`Net ROAS ${multiple(d.roas)}`}`;
    if(kind==='roas'&&d.roas!=null){if(previous)svg+=`<line x1="${previous.x}" y1="${previous.y}" x2="${x}" y2="${y(d.roas)}" stroke="#247566" stroke-width="2.5"/>`;previous={x,y:y(d.roas)};}else previous=null;
    svg+=`<g tabindex="0" role="img" aria-label="${esc(tip)}"><title>${esc(tip)}</title><rect class="focus" x="${l+i*slot}" y="${top-5}" width="${slot}" height="${bottom-top+31}" rx="3"/>`;
    if(kind==='money')for(const [j,key,color] of [[-1,'spend','#247566'],[1,'revenue','#889c3a']]){const v=d[key];if(v!=null)svg+=`<rect x="${x+(j<0?-bw-1:1)}" y="${Math.min(y(v),y(0))}" width="${bw}" height="${Math.abs(y(v)-y(0))}" rx="2" fill="${color}"/>`;}
    else if(d.roas!=null)svg+=`<circle cx="${x}" cy="${y(d.roas)}" r="4" fill="#247566"/><text x="${x}" y="${y(d.roas)-12}" text-anchor="middle">${d.roas.toFixed(2)}×</text>`;
    svg+=`<text x="${x}" y="244" text-anchor="middle">${esc(month(d.month).split(' ')[0])}</text></g>`;
  });
  return `<svg viewBox="0 0 ${w} ${h}" role="group" aria-label="${kind==='money'?'Monthly spend and net revenue in GBP':'Monthly net ROAS in multiples'}. Focus each month for values.">${svg}</svg>`;
}
function update(){
  try{busy(true);const f=Object.fromEntries(['start','end','channel','campaign'].map(id=>[id,$(id).value]));const result=select(data,f),k=result.kpis;
    $('error').hidden=true;$('dashboard').hidden=false;
    const scope=f.campaign?'Campaign-attributed outcomes':f.channel?'Selected channel outcomes':'All website outcomes';
    $('scope').textContent=scope;$('scope-description').textContent=`${month(f.start)} – ${month(f.end)} · GBP`;
    const cards=[['Marketing spend',cash(k.spend),'Recorded platform media only'],['Net revenue',cash(k.revenue),f.campaign?'Attributed merchandise revenue':'Includes unmatched sales at selected scope'],['Net ROAS',multiple(k.roas),'Attributed net revenue ÷ media spend'],['Paid CAC',cash(k.cac),'Media spend ÷ paid first-observed acquisitions'],['Eligible conversions',count(k.conversions),'Positive-net completed / partially refunded'],['First-observed acquisitions',count(k.acquisitions),'First eligible purchase in 2025 history'],['Attribution rate',pct(k.attribution),f.campaign?'Campaign scope; see date-only context below':'Attributed ÷ eligible conversions'],['Budget utilisation',pct(k.utilisation),'Selected spend ÷ active-day allocation']];
    $('kpis').innerHTML=cards.map(([name,value,note])=>`<article class="kpi"><div class="kpi-label">${esc(name)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note)}</div></article>`).join('');
    $('money-chart').innerHTML=chart(result.monthly,'money');$('roas-chart').innerHTML=chart(result.monthly,'roas');
    $('monthly-table').innerHTML=table(['London month','Spend','Net revenue','Net ROAS'],result.monthly.map(r=>[month(r.month),cash(r.spend),cash(r.revenue),multiple(r.roas)]),'Monthly performance · selected scope');
    $('channel-chart').innerHTML=barRows(result.channels,r=>r.marketing_channel,r=>r.spend,cash,r=>`Net revenue ${cash(r.revenue)} · ROAS ${multiple(r.roas)}`);
    $('channel-table').innerHTML=table(['Channel','Spend','Net revenue','Net ROAS','Paid CAC'],result.channels.map(r=>[r.marketing_channel,cash(r.spend),cash(r.revenue),multiple(r.roas),cash(r.cac)]),'Channel performance · selected scope');
    $('top-chart').innerHTML=barRows(result.top,r=>r.campaign_name,r=>r.roas,multiple,r=>`${r.campaign_id} · ${cash(r.spend)} spend`);
    $('campaign-table').innerHTML=table(['Campaign','Spend','Allocated budget','Utilisation','Net revenue','Net ROAS','Paid CAC','Eligible orders'],result.performance.map(r=>[`${r.campaign_id} · ${r.campaign_name}`,cash(r.spend),cash(r.budget),pct(r.utilisation),cash(r.revenue),multiple(r.roas),cash(r.cac),count(r.conversions)]),'Campaign spend versus allocated budget · selected months');
    $('lifetime-table').innerHTML=table(['Campaign','Full-snapshot spend','Lifetime budget','Overspend'],result.lifetime.map(r=>[r.campaign_id,cash(r.spend_gbp),cash(r.lifetime_budget_gbp),r.flag_budget_overspend?'Yes':'No']),'Lifetime campaign context · date filters do not apply');
    const alerts=(id,rows,text)=>$(id).innerHTML=rows.length?rows.map(r=>`<div class="alert"><strong>${esc(r.campaign_id)} · ${esc(r.campaign_name)}</strong>${esc(text(r))}</div>`).join(''):'<p class="muted">No alerts in the selected scope.</p>';
    alerts('spend-alerts',result.spendAlerts,r=>`${cash(r.spend)} spend · 0 eligible attributed orders`);alerts('budget-alerts',result.budgetAlerts,r=>`${cash(r.spend)} spend / ${cash(r.budget)} allocation · ${pct(r.utilisation)}`);
    const g=result.global,share=g.attribution??0;
    $('attribution').innerHTML=`<div class="coverage"><div>Attributed eligible orders<strong>${count(g.attributed_orders)}</strong></div><div>Unattributed eligible orders<strong>${count(g.unmatched_orders)}</strong></div></div><div class="coverage-track" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,share))}%"></i></div><div class="coverage"><div>Attributed net revenue<strong>${cash(g.attributed_revenue)}</strong></div><div>Unattributed net revenue<strong>${cash(g.unmatched_revenue)}</strong></div></div><p class="muted">${pct(g.attribution)} of eligible orders attributed. Date-only website scope.</p>`;
    $('quality').innerHTML=`<article><strong>Snapshot integrity verified</strong>${report.models.reduce((n,m)=>n+m.rows,0).toLocaleString('en-GB')} rows across ${report.models.length} governed models. SHA-256 checked on load.</article><article><strong>Negative source indicators</strong>${count(k.negative_inputs)} in selected scope. Zero does not prove complete feeds.</article><article><strong>Acquisition history limited</strong>First observed in 2025 only. No verified lifetime customer history.</article>`;
    $('status').textContent=k.rows?`Snapshot ready · ${month(f.start)} – ${month(f.end)} · ${count(k.conversions)} eligible conversions`:'No matching data. Adjust the filters or reset.';
    window.dashboardState={ready:true,filters:f,results:result};busy(false);
  }catch(e){failure(e);}
}
async function verified(){
  try{const items=await json('verified.json');$('questions').innerHTML=items.map((q,i)=>`<details><summary>${i+1}. ${esc(q.question)}</summary>${renderAnswer({source:'saved',rows:q.answer,model:q.model,semantic_sql:q.semantic_sql,verification_sql:q.direct_sql,validation:'Saved Wren execution independently checked against DuckDB',assumptions:['Full fixed 2025 snapshot; dashboard filters do not apply.']})}</details>`).join('');}catch(e){$('questions').textContent=`Saved verified examples unavailable: ${e.message}`;}
}
async function boot(){
  busy(true);verified();
  try{
    const [duckdb,snapshot,manifest]=await Promise.all([import(`https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${VERSION}/+esm`),json('snapshot.json'),json('queries.json')]);report=snapshot;
    const bundles={mvp:{mainModule:`${CDN}duckdb-mvp.wasm`,mainWorker:`${CDN}duckdb-browser-mvp.worker.js`},eh:{mainModule:`${CDN}duckdb-eh.wasm`,mainWorker:`${CDN}duckdb-browser-eh.worker.js`}};
    const bundle=await duckdb.selectBundle(bundles),workerURL=URL.createObjectURL(new Blob([`importScripts(${JSON.stringify(bundle.mainWorker)});`],{type:'text/javascript'}));
    const worker=new Worker(workerURL),engine=new duckdb.AsyncDuckDB(new duckdb.VoidLogger(),worker);
    await engine.instantiate(bundle.mainModule);URL.revokeObjectURL(workerURL);
    await engine.open({query:{castBigIntToDouble:true,castDecimalToDouble:true}});
    connection=await engine.connect();
    // Registration DDL is a fixed template recorded in snapshot metadata. Model names
    // are restricted to this allowlist, never interpolated from a control or feed.
    const models=['MarketingCampaignDaily','MarketingCampaignSummary','MarketingChannelMonthly','MarketingMonthlyOverview'];
    if(report.models.some(m=>m.model==='MarketingCampaignMonthly'))models.push('MarketingCampaignMonthly');
    if(JSON.stringify(report.models.map(m=>m.model).sort())!==JSON.stringify([...models].sort()))throw new Error('Snapshot model inventory differs');
    for(const model of models){
      const response=await fetch(`data/${model}.parquet`);if(!response.ok)throw new Error(`Missing snapshot ${model} (HTTP ${response.status})`);
      const buffer=await response.arrayBuffer(),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),n=>n.toString(16).padStart(2,'0')).join('');
      if(digest!==report.models.find(m=>m.model===model).sha256)throw new Error(`Snapshot integrity mismatch: ${model}`);
      await engine.registerFileBuffer(`${model}.parquet`,new Uint8Array(buffer));
      await connection.query(manifest.registration_ddl.replaceAll('{allowlisted_model}',model));
    }
    const result={};for(const query of manifest.queries){const rows=await connection.query(query.sql);result[query.id]=rows.toArray().map(r=>Object.fromEntries(Object.entries(r.toJSON()).map(([k,v])=>[k,typeof v==='bigint'?Number(v):v])));}
    data=result;
    const months=[...new Set(data.overview.map(r=>r.month.slice(0,7)))].sort();
    for(const id of ['start','end'])for(const value of months)$(id).add(new Option(month(value),value));
    $('start').value=months[0];$('end').value=months.at(-1);
    for(const value of [...new Set(data.channels.map(r=>r.marketing_channel))].sort())$('channel').add(new Option(value,value));
    for(const r of data.inventory)$('campaign').add(new Option(`${r.campaign_id} · ${r.campaign_name}`,r.campaign_id));
    const validation=await json('validation.json');$('validation-note').textContent=`${validation.filter_combinations.toLocaleString('en-GB')} filter combinations tested against independent direct DuckDB SQL. Exact counts and NULLs; numeric tolerance: absolute 1e-8, relative 1e-10. Full ordering and test details are in the validation record.`;
    if(startupFailed)return;
    window.dashboardData=data;
    update();
  }catch(e){failure(e);}
}
for(const id of controls.slice(0,4))$(id).addEventListener('change',update);
$('filters').addEventListener('submit',e=>e.preventDefault());
$('reset').addEventListener('click',()=>{$('start').selectedIndex=0;$('end').selectedIndex=$('end').options.length-1;$('channel').value='';$('campaign').value='';update();});
$('retry').addEventListener('click',()=>location.reload());
Promise.race([boot(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Loading timed out after 60 seconds')),60000))]).catch(failure);
