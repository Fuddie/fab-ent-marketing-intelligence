import {renderAnswer} from './answer.mjs';
const $=id=>document.getElementById(id), URL='http://127.0.0.1:4174';
const suggestions=[
 'Which five campaigns generated the highest net revenue?',
 'Which channel had the strongest net ROAS?',
 'Which campaigns spent money without producing eligible conversions?',
 'Which campaigns exceeded their budgets?',
 'How did spend and net revenue change by month?',
 'Which month had the lowest paid CAC?',
 'What percentage of eligible outcomes was unattributed?',
 'Compare Meta Paid Social, Google Paid Search and TikTok Paid Social.',
 'Which campaigns should a marketing manager investigate first?',
 'How many first-observed acquisitions came from each channel?'];
let running=false;
const local=()=>document.querySelector('input[name="answer-mode"]:checked').value==='local';
function filter(){
 const term=$('question-search').value.toLowerCase();
 $('suggestions').replaceChildren(...suggestions.filter(q=>q.toLowerCase().includes(term)).map(q=>{
   const b=document.createElement('button'); b.type='button';b.textContent=q;
   b.onclick=()=>{$('ai-question').value=q;$('ai-question').focus();counter();};return b;
 }));
 document.querySelectorAll('#questions > details').forEach(d=>d.hidden=!d.querySelector('summary').textContent.toLowerCase().includes(term));
}
function mode(){
 $('local-questions').hidden=!local();$('verified').hidden=local();
 $('answer-kind').textContent=local()?'LOCAL QUESTIONS · NEW GOVERNED ANSWER':'VERIFIED EXAMPLES · SAVED ANSWERS';
 filter();
}
function counter(){$('character-count').textContent=`${$('ai-question').value.length}/500 characters`;}
async function health(){
 try{const r=await fetch(URL+'/health',{signal:AbortSignal.timeout(2500)});if(!r.ok)throw Error();const h=await r.json();
 $('ai-connection').textContent=`${h.ready?'Connected':'Starting'} · ${URL} · Model: ${h.model} · Reasoning: ${h.reasoning} · ${h.running?'Request running':'Idle'}`;
 }catch{$('ai-connection').textContent=`Local service unavailable · ${URL} · Model/reasoning unavailable · ${running?'Request running':'Idle'}. Start the local service for new questions; verified examples remain available.`;}
}
async function post(path,body){
 const r=await fetch(URL+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(95000)});
 const v=await r.json();if(!r.ok)throw Error(v.error||'Local execution failed.');return v;
}
$('ai-form').onsubmit=async e=>{
 e.preventDefault();if(running)return;
 const question=$('ai-question').value.trim();
 if(!question||question.length>500){$('ai-result').textContent='Enter a marketing question of 1–500 characters.';return;}
 let filters=null;
 if($('use-filters').checked){
   if(!window.dashboardState?.ready){$('ai-result').textContent='Dashboard filters are unavailable until the snapshot loads.';return;}
   filters={...window.dashboardState.filters};
 }
 running=true;$('ask-submit').disabled=true;$('clear-cache').disabled=true;
 $('ai-result').textContent='Generating and validating a governed answer… (90-second limit)';
 $('ai-result').setAttribute('aria-busy','true');health();
 try{const a=await post('/ask',{question,filters});
 $('ai-result').innerHTML=renderAnswer(a);
 }catch(e){$('ai-result').textContent=e.name==='TimeoutError'?'Request timed out. Try a simpler question.':e.message==='Failed to fetch'?'Local service unavailable. Start it or select Verified examples.':e.message;}
 finally{running=false;$('ask-submit').disabled=false;$('clear-cache').disabled=false;$('ai-result').setAttribute('aria-busy','false');health();}
};
$('clear-cache').onclick=async()=>{try{$('ai-result').textContent=(await post('/cache/clear',{})).message;}catch(e){$('ai-result').textContent=`Cannot clear local cache: ${e.message}`;}};
document.querySelectorAll('input[name="answer-mode"]').forEach(r=>r.onchange=mode);
$('question-search').oninput=filter;$('ai-question').oninput=counter;
// Saved examples are loaded by the existing dashboard independently of this module.
new MutationObserver(filter).observe($('questions'),{childList:true});
mode();counter();health();setInterval(health,10000);
