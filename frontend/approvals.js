const API_BASE = '/api';
const WORKSPACE_STORAGE_KEY = 'livingops.workspace.v1';
const SECURITY_HISTORY_KEY = 'livingops.securityReviews.v1';
const APPROVAL_HISTORY_KEY = 'livingops.approvalDecisions.v1';

const $ = (id) => document.getElementById(id);
const PEOPLE = {
  '11111111-1111-4111-8111-111111111111': { name: 'Farhana Islam', role: 'HR Manager' },
  '22222222-2222-4222-8222-222222222222': { name: 'Nabil Chowdhury', role: 'Engineering Manager' },
  '33333333-3333-4333-8333-333333333333': { name: 'Tahmid Hasan', role: 'IT Security Owner' },
  '44444444-4444-4444-8444-444444444444': { name: 'Amina Rahman', role: 'AI Engineer' },
  '55555555-5555-4555-8555-555555555555': { name: 'Rafi Ahmed', role: 'AI Engineer' },
  '66666666-6666-4666-8666-666666666666': { name: 'Arif Hossain', role: 'Senior Software Engineer' },
};

const state = { health: null, items: [], filter: 'ALL', search: '', selected: null, resolved: loadResolvedHistory() };

function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, (c) => ({ '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;' }[c])); }
function pretty(value) { return String(value || '').toLowerCase().split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' '); }
function shortId(id) { return String(id || '').split('-')[0].toUpperCase(); }
function person(id) { return PEOPLE[String(id)] || { name: 'Unknown user', role: 'Authorized reviewer' }; }
function formatDate(value) { if (!value) return '—'; const d = new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }); }
function initials(name) { return String(name || '?').split(' ').map((x) => x[0]).join('').slice(0,2).toUpperCase(); }

function showToast(message, type='') { const t=$('toast'); t.textContent=message; t.className=`toast show ${type}`.trim(); clearTimeout(showToast.timer); showToast.timer=setTimeout(()=>{t.className='toast';},3400); }
async function api(path, options={}) { const r=await fetch(`${API_BASE}${path}`, { headers:{'Content-Type':'application/json',...(options.headers||{})}, ...options }); const text=await r.text(); let data=null; if(text){try{data=JSON.parse(text)}catch{data={detail:text}}} if(!r.ok){throw new Error(typeof data?.detail==='string'?data.detail:`Request failed (${r.status})`)} return data; }

function loadJson(key, fallback) { try { const v=JSON.parse(localStorage.getItem(key)||'null'); return v ?? fallback; } catch { return fallback; } }
function loadResolvedHistory() {
  const planHistory = loadJson(APPROVAL_HISTORY_KEY, []);
  const securityHistory = loadJson(SECURITY_HISTORY_KEY, []);
  const normalizedSecurity = (Array.isArray(securityHistory)?securityHistory:[]).map((x) => ({
    kind:'SECURITY', id:x.id || x.event_id, subject:x.person_name || person(x.person_id).name,
    decision:x.decision || x.alert_status || 'RESOLVED', reviewer:x.reviewer_name || person(x.reviewed_by).name,
    comment:x.comment || x.review_comment || '', decided_at:x.decided_at || x.updated_at || new Date().toISOString(),
  }));
  return [...(Array.isArray(planHistory)?planHistory:[]), ...normalizedSecurity].sort((a,b)=>new Date(b.decided_at)-new Date(a.decided_at)).slice(0,80);
}
function savePlanResolved(item) {
  const history = loadJson(APPROVAL_HISTORY_KEY, []);
  const next=[item,...(Array.isArray(history)?history:[]).filter((x)=>x.id!==item.id)].slice(0,50);
  localStorage.setItem(APPROVAL_HISTORY_KEY,JSON.stringify(next));
  state.resolved=loadResolvedHistory();
}

function collectPlanApprovals() {
  const store=loadJson(WORKSPACE_STORAGE_KEY, {});
  const items=[];
  for (const [caseId, local] of Object.entries(store && typeof store==='object'?store:{})) {
    const approval=local?.approval;
    const plan=local?.plan;
    if (!approval || approval.status!=='PENDING' || !approval.id || !plan) continue;
    const planData=plan.plan_data || plan.plan || plan;
    items.push({
      key:`PLAN:${approval.id}`, kind:'PLAN', id:approval.id, case_id:caseId, target_id:approval.target_id || plan.id,
      requested_by:approval.requested_by, assigned_to:approval.assigned_to, requested_at:approval.requested_at || approval.created_at || plan.created_at,
      status:'PENDING', subject:`Case LO-${shortId(caseId)}`, context:planData.summary || 'Operational plan awaiting human approval',
      plan, approval,
    });
  }
  return items;
}

async function collectSecurityAlerts() {
  const alerts=await api('/security/alerts');
  const list=Array.isArray(alerts)?alerts:(Array.isArray(alerts?.items)?alerts.items:[]);
  return list.filter((x)=>String(x.alert_status||'OPEN').toUpperCase()==='OPEN').map((x)=>({
    key:`SECURITY:${x.id}`, kind:'SECURITY', id:x.id, target_id:x.id, requested_at:x.event_time || x.created_at, status:'OPEN',
    assigned_to:'33333333-3333-4333-8333-333333333333', requested_by:x.person_id,
    subject:person(x.person_id).name, context:`${pretty(x.event_type)} · ${x.source} → ${x.destination}`, alert:x,
  }));
}

async function loadQueue(showMessage=false) {
  $('approvalLiveDot').className='dot neutral'; $('approvalUpdated').textContent='Refreshing…';
  try {
    const [health, security] = await Promise.all([api('/health').catch(()=>null), collectSecurityAlerts().catch((e)=>{console.warn(e);return[];})]);
    state.health=health;
    state.items=[...collectPlanApprovals(), ...security].sort((a,b)=>new Date(a.requested_at||0)-new Date(b.requested_at||0));
    renderHealth(); renderMetrics(); renderQueue(); renderResolved();
    $('approvalLiveDot').className=`dot ${health?.status==='ok'?'ok':'bad'}`;
    $('approvalUpdated').textContent=`Updated ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`;
    if(showMessage) showToast('Review queue refreshed.','success');
  } catch (e) {
    renderHealth(); $('approvalLiveDot').className='dot bad'; $('approvalUpdated').textContent='Refresh failed'; showToast(e.message||'Could not refresh queue.','error');
  }
}
function renderHealth(){const ok=state.health?.status==='ok'; $('sidebarHealthDot').className=`dot ${ok?'ok':state.health?'bad':'neutral'}`; $('sidebarHealthText').textContent=ok?'System operational':state.health?'System degraded':'Backend offline'; $('sidebarEnv').textContent=state.health?.environment?`${state.health.environment} environment`:'LivingOps backend';}
function renderMetrics(){const plan=state.items.filter(x=>x.kind==='PLAN').length; const sec=state.items.filter(x=>x.kind==='SECURITY').length; $('pendingMetric').textContent=state.items.length; $('planMetric').textContent=plan; $('securityMetric').textContent=sec; $('resolvedMetric').textContent=state.resolved.length; $('allCount').textContent=state.items.length; $('planCount').textContent=plan; $('securityCount').textContent=sec; $('notificationBadge').textContent=state.items.length; $('notificationBadge').classList.toggle('hidden',state.items.length===0);}

function filteredItems(){const q=state.search.trim().toLowerCase(); return state.items.filter((x)=>(state.filter==='ALL'||x.kind===state.filter) && (!q || `${x.subject} ${x.context} ${x.id}`.toLowerCase().includes(q)));}
function reviewBadge(kind){return kind==='PLAN'?'<span class="approval-kind plan">PLAN</span>':'<span class="approval-kind security">SECURITY</span>';}
function renderQueue(){const rows=filteredItems(); const body=$('approvalTableBody'); if(!rows.length){body.innerHTML='<tr class="empty-row"><td colspan="7"><div class="empty-state"><div class="empty-icon">✓</div><strong>No reviews need attention</strong><span>The current filtered queue is clear.</span></div></td></tr>'; return;} body.innerHTML=rows.map((x)=>{const assignee=person(x.assigned_to); return `<tr class="approval-row" data-key="${escapeHtml(x.key)}"><td>${reviewBadge(x.kind)}</td><td><div class="approval-subject"><span class="mini-avatar">${escapeHtml(initials(x.subject))}</span><div><strong>${escapeHtml(x.subject)}</strong><small>${escapeHtml(x.kind==='PLAN'?'Operational plan':'Access anomaly')}</small></div></div></td><td><strong class="table-primary">${escapeHtml(assignee.name)}</strong><span class="table-secondary">${escapeHtml(assignee.role)}</span></td><td><span class="approval-context-text">${escapeHtml(x.context)}</span></td><td><span class="guardian-state open">${escapeHtml(x.status)}</span></td><td>${escapeHtml(formatDate(x.requested_at))}</td><td><button class="table-action review-button" data-key="${escapeHtml(x.key)}">Review</button></td></tr>`;}).join(''); body.querySelectorAll('.review-button').forEach((b)=>b.addEventListener('click',(e)=>{e.stopPropagation();openReview(b.dataset.key);})); body.querySelectorAll('.approval-row').forEach((r)=>r.addEventListener('click',()=>openReview(r.dataset.key)));}

function openReview(key){const item=state.items.find((x)=>x.key===key); if(!item)return; state.selected=item; $('drawerTitle').textContent=item.kind==='PLAN'?'Plan Approval':'Security Review'; $('drawerSubtitle').textContent=item.subject; $('drawerTypeBadge').textContent=item.kind==='PLAN'?'Operational plan':'Access anomaly'; $('planDetailSection').classList.toggle('hidden',item.kind!=='PLAN'); $('securityDetailSection').classList.toggle('hidden',item.kind!=='SECURITY');
  const assigned=person(item.assigned_to); $('drawerContext').innerHTML=`<div><span>Review ID</span><strong class="mono">${escapeHtml(shortId(item.id))}</strong></div><div><span>Assigned to</span><strong>${escapeHtml(assigned.name)}</strong></div><div><span>Status</span><strong>${escapeHtml(item.status)}</strong></div><div><span>Requested</span><strong>${escapeHtml(formatDate(item.requested_at))}</strong></div>`;
  if(item.kind==='PLAN') renderPlanDrawer(item); else renderSecurityDrawer(item);
  configureDecisionForm(item); $('approvalDrawer').classList.remove('hidden'); $('approvalDrawerBackdrop').classList.remove('hidden'); $('approvalDrawer').setAttribute('aria-hidden','false');
}
function closeReview(){state.selected=null;$('approvalDrawer').classList.add('hidden');$('approvalDrawerBackdrop').classList.add('hidden');$('approvalDrawer').setAttribute('aria-hidden','true');}
function renderPlanDrawer(item){const plan=item.plan||{}; const data=plan.plan_data||plan.plan||plan; $('drawerPlanSummary').textContent=data.summary || 'Policy-grounded operational plan awaiting approval.'; const actions=Array.isArray(data.actions)?data.actions:[]; $('drawerPlanActions').innerHTML=actions.length?actions.map((a,i)=>`<div class="approval-action"><span>${i+1}</span><div><strong>${escapeHtml(pretty(a.action_type||a.action||'Action'))}</strong><p>${escapeHtml(a.resource_type||a.resource_key||a.description||'Operational resource action')}</p></div></div>`).join(''):'<div class="security-empty">No structured action details are cached for this plan.</div>'; $('openCaseLink').href=`workspace.html?case=${encodeURIComponent(item.case_id)}`;}
function renderSecurityDrawer(item){const a=item.alert||{}; const score=Number(a.anomaly_score); $('drawerSecurityAssessment').innerHTML=`<div><span>Event</span><strong>${escapeHtml(pretty(a.event_type))}</strong></div><div><span>Anomaly score</span><strong>${Number.isFinite(score)?score.toFixed(4):'—'}</strong></div><div><span>Source</span><strong>${escapeHtml(a.source||'—')}</strong></div><div><span>Destination</span><strong>${escapeHtml(a.destination||'—')}</strong></div><div><span>Successful</span><strong>${a.success===true?'Yes':a.success===false?'No':'—'}</strong></div><div><span>Event time</span><strong>${escapeHtml(formatDate(a.event_time))}</strong></div>`;}
function configureDecisionForm(item){const reviewer=$('drawerReviewer'), decision=$('drawerDecision'); if(item.kind==='PLAN'){const p=person(item.assigned_to); reviewer.innerHTML=`<option value="${escapeHtml(item.assigned_to)}">${escapeHtml(p.name)} · ${escapeHtml(p.role)}</option>`; decision.innerHTML='<option value="APPROVED">Approve plan</option><option value="REJECTED">Reject plan</option>'; $('drawerReviewerRole').textContent='Assigned approver';} else {reviewer.innerHTML='<option value="33333333-3333-4333-8333-333333333333">Tahmid Hasan · IT Security Owner</option>'; decision.innerHTML='<option value="CONFIRMED">Confirm anomaly</option><option value="FALSE_POSITIVE">Mark false positive</option>'; $('drawerReviewerRole').textContent='IT owner';} $('drawerComment').value='';}

async function submitDecision(event){event.preventDefault(); const item=state.selected; if(!item)return; const button=$('approvalDecisionSubmit'); const decision=$('drawerDecision').value; const reviewer=$('drawerReviewer').value; const comment=$('drawerComment').value.trim(); if((decision==='REJECTED'||decision==='CONFIRMED')&&!comment){showToast('Add a short comment for this decision.','error');return;} button.disabled=true; button.textContent='Saving…'; try { if(item.kind==='PLAN'){const updated=await api(`/approvals/${encodeURIComponent(item.id)}/decision`,{method:'POST',body:JSON.stringify({decided_by:reviewer,decision,comment:comment||null})}); updateCachedPlanApproval(item.case_id,updated); savePlanResolved({kind:'PLAN',id:item.id,subject:item.subject,decision:updated.status||decision,reviewer:person(reviewer).name,comment:updated.comment||comment,decided_at:updated.decided_at||new Date().toISOString(),case_id:item.case_id});} else {const updated=await api(`/access-events/${encodeURIComponent(item.id)}/review`,{method:'POST',body:JSON.stringify({reviewed_by:reviewer,decision,comment:comment||null})}); appendSecurityHistory(item,updated,reviewer,decision,comment);} closeReview(); state.resolved=loadResolvedHistory(); await loadQueue(false); showToast('Human review decision saved.','success'); } catch(e){showToast(e.message||'Could not save decision.','error');} finally {button.disabled=false;button.textContent='Submit Decision';}}
function updateCachedPlanApproval(caseId,updated){const store=loadJson(WORKSPACE_STORAGE_KEY,{}); if(store?.[caseId]){store[caseId].approval=updated;localStorage.setItem(WORKSPACE_STORAGE_KEY,JSON.stringify(store));}}
function appendSecurityHistory(item,updated,reviewer,decision,comment){const current=loadJson(SECURITY_HISTORY_KEY,[]); const row={...(item.alert||{}),...(updated||{}),id:item.id,person_id:updated?.person_id||item.alert?.person_id,reviewed_by:updated?.reviewed_by||reviewer,review_comment:updated?.review_comment||comment||null,alert_status:updated?.alert_status||decision,updated_at:updated?.updated_at||new Date().toISOString()}; const next=[row,...(Array.isArray(current)?current:[]).filter((x)=>String(x.id)!==String(item.id))].slice(0,50); localStorage.setItem(SECURITY_HISTORY_KEY,JSON.stringify(next));}

function renderResolved(){const list=$('resolvedList'); if(!state.resolved.length){list.innerHTML='<div class="security-empty">No decisions have been completed from this browser yet.</div>';return;} list.innerHTML=state.resolved.slice(0,6).map((x)=>`<div class="resolved-item"><span class="resolved-mark ${String(x.decision).toLowerCase()}">${String(x.decision).toUpperCase().includes('APPROV')||String(x.decision).toUpperCase().includes('FALSE')?'✓':'!'}</span><div><strong>${escapeHtml(x.subject||'Review')}</strong><span>${escapeHtml(pretty(x.decision))} · ${escapeHtml(x.reviewer||'Reviewer')}</span></div><time>${escapeHtml(formatDate(x.decided_at))}</time></div>`).join('');}
function showResolvedModal(){$('resolvedModalBody').innerHTML=state.resolved.length?state.resolved.map((x)=>`<div class="resolved-modal-row"><div>${reviewBadge(x.kind||'PLAN')}<strong>${escapeHtml(x.subject||'Review')}</strong></div><div><span>${escapeHtml(pretty(x.decision))}</span><small>${escapeHtml(x.reviewer||'Reviewer')} · ${escapeHtml(formatDate(x.decided_at))}</small>${x.comment?`<p>${escapeHtml(x.comment)}</p>`:''}</div></div>`).join(''):'<div class="security-empty">No resolved reviews in local history.</div>'; $('resolvedModal').classList.remove('hidden');}
function closeModal(id){$(id).classList.add('hidden');}

$('approvalSearch').addEventListener('input',(e)=>{state.search=e.target.value;renderQueue();});
$('refreshApprovals').addEventListener('click',()=>loadQueue(true)); $('refreshQueueButton').addEventListener('click',()=>loadQueue(true));
document.querySelectorAll('.approval-tab').forEach((b)=>b.addEventListener('click',()=>{document.querySelectorAll('.approval-tab').forEach((x)=>x.classList.remove('active'));b.classList.add('active');state.filter=b.dataset.filter;renderQueue();}));
$('closeApprovalDrawer').addEventListener('click',closeReview); $('approvalDrawerBackdrop').addEventListener('click',closeReview); $('approvalDecisionForm').addEventListener('submit',submitDecision);
$('showResolvedButton').addEventListener('click',showResolvedModal); document.querySelectorAll('[data-close-modal]').forEach((b)=>b.addEventListener('click',()=>closeModal(b.dataset.closeModal)));
$('clearResolvedHistory').addEventListener('click',()=>{localStorage.removeItem(APPROVAL_HISTORY_KEY);localStorage.removeItem(SECURITY_HISTORY_KEY);state.resolved=[];renderResolved();renderMetrics();showToast('Local decision history cleared.');});
document.addEventListener('keydown',(e)=>{if(e.key==='Escape'){closeReview();closeModal('resolvedModal');} if(e.key==='/'&&document.activeElement?.tagName!=='INPUT'&&document.activeElement?.tagName!=='TEXTAREA'){e.preventDefault();$('approvalSearch').focus();}});
loadQueue(false);
