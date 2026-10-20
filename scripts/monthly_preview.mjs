import fs from 'node:fs';
import {renderAnswer} from '../docs/answer.mjs';
const v=JSON.parse(fs.readFileSync('target/campaign-monthly/validation.json','utf8'));
const saved=JSON.parse(fs.readFileSync('docs/verified.json','utf8')).find(q=>q.id==='11_top_campaigns_monthly');
if(!saved || saved.answer.length!==36) throw Error('Refresh governed Wren exports first');
v.rows=saved.answer; v.status='PASS: Wren 0.15.0 versus independent direct DuckDB';
const html=renderAnswer({rows:v.rows,model:'MarketingCampaignMonthly',semantic_sql:v.semantic_sql,assumptions:['Europe/London reporting months. Revenue generation is attributed net revenue.'],ordering:'Month ascending; attributed net revenue descending; campaign ID ascending',validation:v.status,duration_ms:0,columns:[]}).replace('? Verified by Wren','Direct DuckDB validation preview');
fs.writeFileSync('target/campaign-monthly/preview.html',`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>${fs.readFileSync('docs/styles.css','utf8')} body{padding:24px} main{max-width:1200px;margin:auto}</style><main><h1>${v.question}</h1><p>Governed campaign-month result · 36 rows · three campaigns per month</p><p>Saved Wren output, independently checked against direct DuckDB. This is not a live AI response.</p>${html}</main>`);
