const API_BASE = '/api';
const REVIEW_HISTORY_KEY = 'livingops.securityReviews.v1';
const $ = (id) => document.getElementById(id);

const PEOPLE = {
  '11111111-1111-4111-8111-111111111111': 'Farhana Islam',
  '22222222-2222-4222-8222-222222222222': 'Nabil Chowdhury',
  '33333333-3333-4333-8333-333333333333': 'Tahmid Hasan',
  '44444444-4444-4444-8444-444444444444': 'Amina Rahman',
  '55555555-5555-4555-8555-555555555555': 'Rafi Ahmed',
  '66666666-6666-4666-8666-666666666666': 'Arif Hossain',
};
const FEATURE_LABELS = {
  event_count: 'Events', failed_login_count: 'Failed logins', failed_login_ratio: 'Failed login ratio',
  command_count: 'Commands', file_event_count: 'File events', http_count: 'HTTP events', email_count: 'Email events',
  device_count: 'Device events', session_count: 'Sessions', unique_agents: 'Unique sources', unique_decoders: 'Unique destinations',
  unique_actions: 'Unique actions', high_severity_count: 'Failed events', high_severity_ratio: 'Failure ratio',
  off_hours_count: 'Off-hours events', off_hours_ratio: 'Off-hours ratio'
};
const state = { health: null, alerts: [], selected: null, filter: '', riskFilter: 'ALL', reviewHistory: loadReviewHistory() };

function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function shortId(value, n=8) { const s=String(value||''); return s.length>n ? `${s.slice(0,n)}…` : s; }
function formatDate(value) { if(!value) return '—'; const d=new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}); }
function formatNumber(value, digits=3) { const n=Number(value); return Number.isFinite(n) ? n.toFixed(digits) : '—'; }
function personName(id) { return PEOPLE[String(id)] || `Person ${shortId(id, 8)}`; }
function showToast(message, type='') { const t=$('toast'); t.textContent=message; t.className=`toast show ${type}`.trim(); clearTimeout(showToast.timer); showToast.timer=setTimeout(()=>t.className='toast',3200); }
async function api(path, options={}) { const r=await fetch(`${API_BASE}${path}`,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options}); const text=await r.text(); let body=null; if(text){try{body=JSON.parse(text)}catch{body={detail:text}}} if(!r.ok){const d=body?.detail;throw new Error(typeof d==='string'?d:`Request failed (${r.status})`)} return body; }
function openModal(id){$(id).classList.remove('hidden');}
function closeModal(id){$(id).classList.add('hidden');}
function loadReviewHistory(){try{const x=JSON.parse(localStorage.getItem(REVIEW_HISTORY_KEY)||'[]');return Array.isArray(x)?x:[]}catch{return[]}}
function saveReviewHistory(){localStorage.setItem(REVIEW_HISTORY_KEY,JSON.stringify(state.reviewHistory.slice(0,50)));}
function thresholdOf(alert){return Number(alert?.features_data?._ml?.threshold);}
function signalOf(alert){ const f=alert?.features_data||{}; if(Number(f.off_hours_count||0)>0)return 'OFF_HOURS'; if(alert?.success===false||Number(f.failed_login_count||0)>0)return 'FAILED'; return 'OTHER'; }
function signalLabel(alert){ const s=signalOf(alert); return s==='OFF_HOURS'?'Off-hours':s==='FAILED'?'Failed event':'Anomaly'; }

async function loadHealth(){try{state.health=await api('/health')}catch{state.health=null} const ok=state.health?.status==='ok'; $('sidebarHealthDot').className=`dot ${ok?'ok':'bad'}`; $('securityLiveDot').className=`dot ${ok?'ok':'bad'}`; $('sidebarHealthText').textContent=ok?'System operational':state.health?'System degraded':'Backend offline'; $('sidebarEnv').textContent=state.health?.environment?`${state.health.environment} environment`:'LivingOps backend';}

async function loadAlerts(){
  try { const result=await api('/security/alerts'); state.alerts=Array.isArray(result)?result:[]; }
  catch(e){ state.alerts=[]; showToast(e.message,'error'); }
  renderAll();
}
function renderAll(){renderMetrics();renderTable();renderReviewHistory();renderModelMetadata();$('securityUpdated').textContent=`Updated ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`;}
function renderMetrics(){
  const open=state.alerts.length; const high=state.alerts.filter(a=>signalOf(a)==='OFF_HOURS').length; const reviewed=state.reviewHistory.filter(x=>['CONFIRMED','FALSE_POSITIVE','CLOSED'].includes(x.alert_status)).length;
  $('openAlertMetric').textContent=open; $('highRiskMetric').textContent=high; $('reviewedMetric').textContent=reviewed; $('notificationBadge').textContent=open; $('notificationBadge').classList.toggle('hidden',open===0);
  $('openAlertNote').textContent=open?`${open} alert${open===1?'':'s'} awaiting human decision`:'No open anomalies require review';
  const threshold=firstFinite(state.alerts.map(thresholdOf)); $('thresholdMetric').textContent=threshold==null?'—':threshold.toFixed(3);
}
function firstFinite(values){for(const v of values)if(Number.isFinite(v))return v;return null;}
function renderModelMetadata(){ const a=state.alerts.find(x=>x.features_data?._ml)||state.reviewHistory.find(x=>x.features_data?._ml); const ml=a?.features_data?._ml||{}; $('modelDataset').textContent=ml.dataset_name||'SPEDIA'; $('modelThreshold').textContent=Number.isFinite(Number(ml.threshold))?Number(ml.threshold).toFixed(6):'Available after first scored alert'; }
function matchesAlert(a){ const q=state.filter.trim().toLowerCase(); const hay=`${a.id} ${personName(a.person_id)} ${a.event_type} ${a.source} ${a.destination} ${a.alert_status}`.toLowerCase(); if(q && !hay.includes(q))return false; if(state.riskFilter!=='ALL'&&signalOf(a)!==state.riskFilter)return false; return true; }
function renderTable(){
  const body=$('securityTableBody'); const rows=state.alerts.filter(matchesAlert).sort((a,b)=>Number(b.anomaly_score||0)-Number(a.anomaly_score||0));
  if(!rows.length){body.innerHTML=`<tr class="empty-row"><td colspan="8"><div class="empty-state"><div class="empty-icon">◇</div><strong>${state.alerts.length?'No alerts match your filters':'No open security alerts'}</strong><span>${state.alerts.length?'Change the search or risk filter.':'The backend currently has no anomaly alerts awaiting review.'}</span></div></td></tr>`;return;}
  body.innerHTML=rows.map(a=>`<tr class="security-alert-row" data-alert-id="${escapeHtml(a.id)}"><td><div class="person-cell"><span class="mini-avatar">${escapeHtml(initials(personName(a.person_id)))}</span><div><strong>${escapeHtml(personName(a.person_id))}</strong><small>${escapeHtml(shortId(a.person_id,10))}</small></div></div></td><td><strong class="event-type">${escapeHtml(a.event_type)}</strong><small class="event-result ${a.success?'success':'failed'}">${a.success?'Success':'Failed'}</small></td><td><div class="route-cell"><span>${escapeHtml(a.source)}</span><b>→</b><span>${escapeHtml(a.destination)}</span></div></td><td><div class="security-score-cell"><strong>${formatNumber(a.anomaly_score,3)}</strong><span class="score-bar"><i style="width:${Math.min(100,Math.max(4,Number(a.anomaly_score||0)*100))}%"></i></span></div></td><td><span class="security-risk-badge ${signalOf(a).toLowerCase()}">${signalLabel(a)}</span></td><td><span class="guardian-state open">${escapeHtml(a.alert_status)}</span></td><td>${escapeHtml(formatDate(a.event_time))}</td><td><button class="row-open-button" data-alert-id="${escapeHtml(a.id)}">Review</button></td></tr>`).join('');
  body.querySelectorAll('[data-alert-id]').forEach(el=>el.addEventListener('click',e=>{e.stopPropagation();openAlert(el.dataset.alertId)}));
}
function initials(name){return name.split(/\s+/).map(x=>x[0]).join('').slice(0,2).toUpperCase();}
function openAlert(id){const a=state.alerts.find(x=>String(x.id)===String(id));if(!a)return;state.selected=a;renderDrawer(a);$('alertDrawerBackdrop').classList.remove('hidden');$('alertDrawer').classList.remove('hidden');$('alertDrawer').setAttribute('aria-hidden','false');}
function closeDrawer(){$('alertDrawerBackdrop').classList.add('hidden');$('alertDrawer').classList.add('hidden');$('alertDrawer').setAttribute('aria-hidden','true');state.selected=null;}
function renderDrawer(a){
  $('drawerTitle').textContent=`${a.event_type} anomaly`; $('drawerSubtitle').textContent=`${personName(a.person_id)} · ${shortId(a.id,12)}`; $('drawerStatus').textContent=a.alert_status; $('drawerPerson').textContent=personName(a.person_id); $('drawerEventType').textContent=a.event_type; $('drawerSource').textContent=a.source; $('drawerDestination').textContent=a.destination; $('drawerTime').textContent=formatDate(a.event_time); $('drawerSuccess').textContent=a.success?'Yes':'No'; $('drawerScore').textContent=formatNumber(a.anomaly_score,6); $('drawerThreshold').textContent=Number.isFinite(thresholdOf(a))?thresholdOf(a).toFixed(6):'—'; $('drawerRisk').textContent='Above threshold'; $('drawerRisk').className='security-risk-badge threshold';
  const features=a.features_data||{}; const keys=Object.keys(FEATURE_LABELS).filter(k=>features[k]!=null); $('featureGrid').innerHTML=keys.length?keys.map(k=>`<div class="feature-item"><span>${escapeHtml(FEATURE_LABELS[k])}</span><strong>${typeof features[k]==='number'&&String(k).includes('ratio')?formatNumber(features[k],2):escapeHtml(features[k])}</strong></div>`).join(''):'<div class="security-empty">No feature vector was returned.</div>';
}
function renderReviewHistory(){
  const items=state.reviewHistory.slice(0,5); const renderItem=r=>`<div class="review-history-item"><span class="review-state ${String(r.alert_status).toLowerCase()}">${escapeHtml(r.alert_status.replaceAll('_',' '))}</span><div><strong>${escapeHtml(personName(r.person_id))} · ${escapeHtml(r.event_type)}</strong><span>${escapeHtml(r.review_comment||'No reviewer comment')} · ${escapeHtml(formatDate(r.updated_at||r.event_time))}</span></div></div>`;
  $('reviewHistory').innerHTML=items.length?items.map(renderItem).join(''):'<div class="security-empty">No locally recorded reviews yet.</div>';
  $('reviewHistoryModalBody').innerHTML=state.reviewHistory.length?state.reviewHistory.map(renderItem).join(''):'<div class="security-empty">No locally recorded reviews yet.</div>';
}
async function submitReview(e){
  e.preventDefault(); if(!state.selected)return; $('reviewSubmitButton').disabled=true;
  try{const reviewed=await api(`/access-events/${encodeURIComponent(state.selected.id)}/review`,{method:'POST',body:JSON.stringify({reviewed_by:$('reviewerId').value,decision:$('reviewDecision').value,comment:$('reviewComment').value.trim()||null})}); state.reviewHistory=[reviewed,...state.reviewHistory.filter(x=>x.id!==reviewed.id)];saveReviewHistory();showToast(`Alert marked ${reviewed.alert_status.replaceAll('_',' ').toLowerCase()}.`,'success');closeDrawer();$('reviewComment').value='';await loadAlerts();}
  catch(err){showToast(err.message,'error')}finally{$('reviewSubmitButton').disabled=false;}
}
function localDateTimeValue(d=new Date()){const off=d.getTimezoneOffset();const local=new Date(d.getTime()-off*60000);return local.toISOString().slice(0,16);}
async function submitEvent(e){
  e.preventDefault(); $('eventSubmitButton').disabled=true; $('eventResultPreview').classList.add('hidden');
  const raw=$('eventTime').value; const eventDate=new Date(raw); if(Number.isNaN(eventDate.getTime())){showToast('Choose a valid event time.','error');$('eventSubmitButton').disabled=false;return;}
  const payload={person_id:$('eventPersonId').value,event_time:eventDate.toISOString(),source:$('eventSource').value.trim(),destination:$('eventDestination').value.trim(),event_type:$('eventType').value.trim(),success:$('eventSuccess').value==='true'};
  try{const result=await api('/access-events',{method:'POST',body:JSON.stringify(payload)}); const alerted=result.alert_status==='OPEN'; $('eventResultPreview').innerHTML=`<strong>${alerted?'Anomaly alert opened':'Event recorded without alert'}</strong><span>Score ${formatNumber(result.anomaly_score,6)} · threshold ${Number.isFinite(thresholdOf(result))?thresholdOf(result).toFixed(6):'—'}</span>`; $('eventResultPreview').classList.remove('hidden'); showToast(alerted?'Anomaly detected and added to the review queue.':'Access event scored successfully.','success'); await loadAlerts(); if(alerted){setTimeout(()=>{closeModal('recordEventModal');openAlert(result.id)},450);} }
  catch(err){showToast(err.message,'error')}finally{$('eventSubmitButton').disabled=false;}
}
async function refresh(){await Promise.all([loadHealth(),loadAlerts()]);}

$('securitySearch').addEventListener('input',e=>{state.filter=e.target.value;renderTable();});
$('riskFilter').addEventListener('change',e=>{state.riskFilter=e.target.value;renderTable();});
$('refreshSecurity').addEventListener('click',async()=>{await refresh();showToast('Security data refreshed.','success');});
$('recordEventButton').addEventListener('click',()=>{ $('eventTime').value=localDateTimeValue(); $('eventResultPreview').classList.add('hidden'); openModal('recordEventModal'); });
$('trackReviewedButton').addEventListener('click',()=>{renderReviewHistory();openModal('reviewHistoryModal');});
$('reviewForm').addEventListener('submit',submitReview); $('recordEventForm').addEventListener('submit',submitEvent);
$('closeAlertDrawer').addEventListener('click',closeDrawer); $('alertDrawerBackdrop').addEventListener('click',closeDrawer);
$('clearReviewHistory').addEventListener('click',()=>{state.reviewHistory=[];saveReviewHistory();renderAll();showToast('Local review history cleared.','success');});
document.querySelectorAll('[data-close-modal]').forEach(b=>b.addEventListener('click',()=>closeModal(b.dataset.closeModal)));
document.querySelectorAll('.modal-backdrop').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)closeModal(m.id)}));
window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('securitySearch').focus()}if(e.key==='Escape'){closeDrawer();document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(m=>closeModal(m.id));}});
$('eventTime').value=localDateTimeValue();
refresh().catch(console.error);
