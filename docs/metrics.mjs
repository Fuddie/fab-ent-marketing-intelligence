export const fields = ['spend','revenue','attributed_revenue','conversions','attributed_orders','acquisitions','paid_acquisitions','unmatched_orders','unmatched_revenue','budget','negative_inputs'];
export const ratio = (a,b,m=1) => a == null || b == null || b === 0 ? null : a / b * m;
export function totals(rows) {
  const t = Object.fromEntries(fields.map(f=>[f,rows.length ? rows.reduce((s,r)=>s+Number(r[f]),0) : null]));
  return {...t, rows:rows.length, roas:ratio(t.attributed_revenue,t.spend), cac:ratio(t.spend,t.paid_acquisitions), attribution:ratio(t.attributed_orders,t.conversions,100), utilisation:ratio(t.spend,t.budget,100)};
}
export function select(data,f={}) {
  const within = r => (!f.start || r.month.slice(0,7)>=f.start) && (!f.end || r.month.slice(0,7)<=f.end);
  const match = r => within(r) && (!f.channel || r.marketing_channel===f.channel) && (!f.campaign || r.campaign_id===f.campaign);
  const source = f.campaign ? data.campaigns : f.channel ? data.channels : data.overview;
  const rows = source.filter(match), campaigns=data.campaigns.filter(match);
  const group = (input,key) => [...new Set(input.map(r=>r[key]))].sort().map(value=>({[key]:value,...totals(input.filter(r=>r[key]===value))}));
  const performance = group(campaigns,'campaign_id').map(r=>({...r,campaign_name:campaigns.find(c=>c.campaign_id===r.campaign_id).campaign_name}));
  const channels = f.campaign ? group(campaigns,'marketing_channel') : group(data.channels.filter(match),'marketing_channel');
  const global = totals(data.overview.filter(within));
  return {kpis:totals(rows), monthly:group(rows,'month'), channels, performance,
    top:[...performance].sort((a,b)=>(b.roas??-Infinity)-(a.roas??-Infinity)||a.campaign_id.localeCompare(b.campaign_id)).slice(0,5),
    spendAlerts:performance.filter(r=>r.spend>0&&r.attributed_orders===0),
    budgetAlerts:performance.filter(r=>r.utilisation>100), global,
    lifetime:data.inventory.filter(r=>(!f.channel||r.marketing_channel===f.channel)&&(!f.campaign||r.campaign_id===f.campaign))};
}
const finite = value => value != null && Number.isFinite(Number(value));
export const cash = v => finite(v) ? new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP'}).format(Number(v)) : 'N/A';
export const count = v => finite(v) ? new Intl.NumberFormat('en-GB',{maximumFractionDigits:0}).format(Number(v)) : 'N/A';
export const pct = v => finite(v) ? `${Number(v).toFixed(2)}%` : 'N/A';
export const multiple = v => finite(v) ? `${Number(v).toFixed(2)}×` : 'N/A';
export const month = v => new Intl.DateTimeFormat('en-GB',{month:'short',year:'numeric',timeZone:'Europe/London'}).format(new Date(`${v.slice(0,7)}-01T12:00:00Z`));
export const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
