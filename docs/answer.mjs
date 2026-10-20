import {esc} from './metrics.mjs';

export function label(field) {
 const acronyms={gbp:'GBP',roas:'ROAS',cac:'CAC',ctr:'CTR',cpc:'CPC',cpm:'CPM',id:'ID'};
 const words=field.replace(/_/g,' ').split(/\s+/).map(w=>acronyms[w.toLowerCase()]||w.toLowerCase());
 const text=words.join(' ');
 return text.charAt(0).toUpperCase()+text.slice(1);
}
export function unit(field) {
 if (/roas/i.test(field)) return 'multiple';
 if (/pct|percent|ctr|rate|utilisation|coverage/i.test(field)) return 'percent';
 if (/gbp|spend|revenue|budget|cac|cpc|cpm/i.test(field)) return 'currency';
 if (/month|date/i.test(field)) return 'date';
 if (/count|orders|clicks|impressions|sessions|conversions|acquisitions/i.test(field)) return 'integer';
 return 'text';
}
export function format(value, type) {
 if (value==null) return 'N/A';
 if (type==='date') {
   const raw=String(value), d=new Date(/^\d{4}-\d{2}$/.test(raw)?raw+'-01T12:00:00Z':raw);
   return Number.isNaN(d.getTime())?raw:new Intl.DateTimeFormat('en-GB',{...( /^\d{4}-\d{2}(-01)?$/.test(raw)?{}:{day:'numeric'}),month:'short',year:'numeric',timeZone:'UTC'}).format(d);
 }
 if (type==='text') return String(value);
 if (value==='' || !Number.isFinite(Number(value))) return String(value);
 const n=Number(value);
 if (type==='currency') return new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
 if (type==='percent') return n.toFixed(2)+'%';
 if (type==='multiple') return n.toFixed(2)+'x';
 return new Intl.NumberFormat('en-GB',{maximumFractionDigits:type==='integer'?0:2}).format(n);
}
export function renderAnswer(a) {
 const rows=a.rows||[], headers=Object.keys(rows[0]||{});
 const columns=headers.map(key=>({key,label:label(key),unit:a.columns?.find(c=>c.key===key)?.unit||unit(key)}));
 const scalar=rows.length===1 && headers.length===1;
 const scope=a.filters?'For the selected dashboard scope.':'Across the scope defined by your question.';
 const names=items=>new Intl.ListFormat('en-GB',{style:'long',type:'conjunction'}).format(items.map(c=>c.label.replace(/ GBP$/, '')));
 const dimensions=columns.filter(c=>['text','date'].includes(c.unit));
 const measures=columns.filter(c=>!['text','date'].includes(c.unit));
 const summary=rows.length?`${names(measures.length?measures:columns)}${dimensions.length && measures.length?' by '+names(dimensions).toLowerCase():''} for the requested scope.`:'No matching data in this scope.';
 const content=scalar?`<article class="answer-kpi"><h3>${esc(columns[0].label.replace(/ GBP$/, ''))}</h3><div class="answer-value">${esc(format(rows[0][headers[0]],columns[0].unit))}</div><p>${rows[0][headers[0]]==null?'This metric is unavailable in the requested scope.':scope}</p></article>`:
 `<p class="answer-summary">${esc(summary)}</p>${rows.length?`<div class="table-wrap answer-table" tabindex="0" role="region" aria-label="Marketing answer results"><table><caption>Marketing performance</caption><thead><tr>${columns.map(c=>`<th scope="col">${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(c=>`<td>${esc(format(row[c.key],c.unit))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:''}`;
 const details=[['Wren model',a.model],['Codex model',a.codex_model],['Reasoning',a.reasoning],['Duration',`${a.duration_ms} ms`],['Dashboard filters',a.filters?JSON.stringify(a.filters):'Not applied. Complete snapshot unless the question explicitly filters it.'],['Validation',a.validation],['Assumptions',(a.assumptions||[]).join(' ')||'None supplied.'],['Ordering',a.ordering],['Row count',`${rows.length} returned · maximum 100 rows`]];
 return `<div class="answer-heading"><span class="answer-verified">✓ Verified by Wren</span><span class="answer-source">${a.cached?'Cached':'New'} answer</span></div>${content}<details class="answer-technical"><summary>Technical details</summary><dl>${details.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl><h4>Generated semantic SQL</h4><pre>${esc(a.semantic_sql)}</pre>${a.verification_sql?`<h4>Independent verification SQL</h4><pre>${esc(a.verification_sql)}</pre>`:''}</details>`;
}
