const API = "/api";
const CHANGE_IDS_KEY = "livingops.guardian.changeIds.v1";
const SNAPSHOTS_KEY = "livingops.guardian.snapshots.v1";
const $ = (id) => document.getElementById(id);

const state = { changes: [], selectedId: null, selected: null, remediation: null, diffExpanded: true };

function escapeHtml(value) { return String(value ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }
function shortId(value, n=8) { const s = String(value || ""); return s ? `${s.slice(0,n)}…` : "—"; }
function fmtDate(value) { if (!value) return "—"; const d = new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}); }
function showToast(message, kind="info") { const el=$("toast"); el.textContent=message; el.className=`toast show ${kind}`; clearTimeout(showToast.t); showToast.t=setTimeout(()=>{el.className="toast";},3400); }
function openModal(id){ $(id).classList.remove("hidden"); }
function closeModal(id){ $(id).classList.add("hidden"); }

async function api(path, options={}) {
  const response = await fetch(`${API}${path}`, {headers:{"Accept":"application/json",...(options.body?{"Content-Type":"application/json"}:{}),...(options.headers||{})}, ...options});
  const text = await response.text();
  let data = null; try { data = text ? JSON.parse(text) : null; } catch { data = {detail:text}; }
  if (!response.ok) { const detail = data?.detail || `Request failed (${response.status})`; throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail)); }
  return data;
}

function readIds(){ try { const v=JSON.parse(localStorage.getItem(CHANGE_IDS_KEY)||"[]"); return Array.isArray(v)?v:[]; } catch { return []; } }
function saveIds(ids){ localStorage.setItem(CHANGE_IDS_KEY, JSON.stringify([...new Set(ids)])); }
function readSnapshots(){ try { const v=JSON.parse(localStorage.getItem(SNAPSHOTS_KEY)||"{}"); return v && typeof v === "object" ? v : {}; } catch { return {}; } }
function saveSnapshot(response){ const map=readSnapshots(); const id=response?.policy_change?.id; if(id){ map[id]=response; localStorage.setItem(SNAPSHOTS_KEY,JSON.stringify(map)); } }
function trackId(id){ const ids=readIds(); if(!ids.includes(id)){ ids.unshift(id); saveIds(ids); } }

function riskClass(risk){ return String(risk||"").toLowerCase(); }
function impactStateClass(status){ return String(status||"").toLowerCase(); }
function versionLabel(item){ const snap=item.snapshot; if(snap?.old_version && snap?.new_version) return `V${snap.old_version.version_number} → V${snap.new_version.version_number}`; return `${shortId(item.change.old_version_id,6)} → ${shortId(item.change.new_version_id,6)}`; }

async function loadHealth(){
  try { const h=await api('/health'); const ok=h.status==='ok'; $('sidebarHealthDot').className=`dot ${ok?'ok':'bad'}`; $('guardianLiveDot').className=`dot ${ok?'ok':'bad'}`; $('sidebarHealthText').textContent=ok?'System operational':'System degraded'; $('sidebarEnv').textContent=h.environment||'LivingOps backend'; $('guardianUpdated').textContent=`Updated ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`; }
  catch { $('sidebarHealthDot').className='dot bad'; $('guardianLiveDot').className='dot bad'; $('sidebarHealthText').textContent='Backend unavailable'; $('guardianUpdated').textContent='Backend unavailable'; }
  try { const alerts=await api('/security/alerts'); const list=Array.isArray(alerts)?alerts:(alerts?.alerts||alerts?.results||[]); const open=list.filter(a=>['OPEN','CONFIRMED'].includes(String(a.alert_status||'').toUpperCase())).length; $('notificationBadge').textContent=open; $('notificationBadge').classList.toggle('hidden', open===0); } catch { $('notificationBadge').classList.add('hidden'); }
}

async function fetchChange(id){ const detail=await api(`/policy-guardian/changes/${encodeURIComponent(id)}`); const snapshot=readSnapshots()[id]||null; return {id, change:detail.change, impacts:detail.impacts||[], snapshot}; }

async function loadChanges({selectFirst=false}={}){
  const ids=readIds(); const results=[];
  for(const id of ids){ try { results.push(await fetchChange(id)); } catch(e){ console.warn('Could not load change',id,e); } }
  state.changes=results;
  renderMetrics(); renderChangeTable();
  const queryId=new URLSearchParams(location.search).get('change');
  const wanted=state.selectedId || queryId || (selectFirst && results[0]?.id);
  if(wanted && results.some(x=>x.id===wanted)) selectChange(wanted,false);
  else if(!results.length){ state.selectedId=null; state.selected=null; renderEmptyDetail(); }
}

function filteredChanges(){ const q=$('guardianSearch').value.trim().toLowerCase(); const risk=$('riskFilter').value; return state.changes.filter(item=>{ const hay=[item.change.policy_code,item.id,versionLabel(item),item.change.status].join(' ').toLowerCase(); return (!q||hay.includes(q)) && (risk==='ALL'||item.change.overall_risk===risk); }); }

function renderMetrics(){ const impacts=state.changes.flatMap(c=>c.impacts||[]); $('trackedChangesMetric').textContent=state.changes.length; $('openImpactsMetric').textContent=impacts.filter(i=>i.status==='OPEN').length; $('highRiskMetric').textContent=impacts.filter(i=>i.risk_level==='HIGH'&&i.status==='OPEN').length; $('regenerateMetric').textContent=impacts.filter(i=>i.recommended_action==='REGENERATE'&&i.status==='OPEN').length; }

function renderChangeTable(){ const body=$('guardianChangeRows'); const list=filteredChanges(); if(!list.length){ body.innerHTML=`<tr class="empty-row"><td colspan="7"><div class="empty-state"><div class="empty-icon">◈</div><strong>${state.changes.length?'No changes match the filter':'No tracked policy changes'}</strong><span>${state.changes.length?'Clear the search or risk filter.':'Activate a new policy version or track a known change UUID.'}</span></div></td></tr>`; return; }
  body.innerHTML=list.map(item=>{ const c=item.change, snap=item.snapshot; const title=snap?.new_version?.title||c.policy_code; return `<tr class="guardian-change-row ${item.id===state.selectedId?'selected':''}" data-change-id="${escapeHtml(item.id)}"><td><div class="policy-cell"><strong>${escapeHtml(c.policy_code)}</strong><span>${escapeHtml(title)}</span></div></td><td><span class="version-chip">${escapeHtml(versionLabel(item))}</span></td><td><span class="guardian-risk ${riskClass(c.overall_risk)}">${escapeHtml(c.overall_risk)}</span></td><td><strong class="impact-number">${item.impacts.length}</strong></td><td><span class="guardian-state ${impactStateClass(c.status)}">${escapeHtml(c.status)}</span></td><td>${escapeHtml(fmtDate(c.created_at))}</td><td><button class="row-open-button" data-open-change="${escapeHtml(item.id)}">Open</button></td></tr>`; }).join('');
  body.querySelectorAll('[data-open-change]').forEach(b=>b.addEventListener('click',(e)=>{e.stopPropagation();selectChange(b.dataset.openChange);}));
  body.querySelectorAll('.guardian-change-row').forEach(r=>r.addEventListener('click',()=>selectChange(r.dataset.changeId)));
}

function renderEmptyDetail(){ $('guardianEmptyDetail').classList.remove('hidden'); $('guardianDetail').classList.add('hidden'); }
function selectChange(id,push=true){ const item=state.changes.find(x=>x.id===id); if(!item)return; state.selectedId=id; state.selected=item; if(push) history.replaceState(null,'',`guardian.html?change=${encodeURIComponent(id)}`); renderChangeTable(); renderDetail(); }

function listBlock(title, items, tone=''){ const arr=Array.isArray(items)?items:[]; return `<section class="analysis-block ${tone}"><div class="analysis-block-title"><span>${escapeHtml(title)}</span><strong>${arr.length}</strong></div>${arr.length?`<ul>${arr.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>`:'<p>No items reported.</p>'}</section>`; }
function renderDetail(){ const item=state.selected; if(!item)return renderEmptyDetail(); $('guardianEmptyDetail').classList.add('hidden'); $('guardianDetail').classList.remove('hidden'); const c=item.change, snap=item.snapshot; const diff=c.diff_data||{}; const summary=diff.guardian_summary||{}; const det=diff.deterministic||{};
  $('detailPolicyTitle').textContent=snap?.new_version?.title||c.policy_code; $('detailRiskBadge').textContent=c.overall_risk||'—'; $('detailRiskBadge').className=`guardian-risk ${riskClass(c.overall_risk)}`; $('detailStatusBadge').textContent=c.status||'—'; $('detailStatusBadge').className=`guardian-state ${impactStateClass(c.status)}`; $('detailVersionLine').textContent=`${c.policy_code} · ${versionLabel(item)} · Change ${shortId(c.id,12)}`;
  $('guardianAnalysis').innerHTML=`<div class="analysis-grid">${listBlock('Added rules',summary.added_rules,'added')}${listBlock('Removed rules',summary.removed_rules,'removed')}${listBlock('Modified rules',summary.modified_rules,'modified')}${listBlock('Affected areas',summary.affected_areas,'areas')}</div><div class="analysis-rationale"><span>RATIONALE</span><p>${escapeHtml(summary.rationale||'No Guardian rationale stored for this change.')}</p></div>`;
  const impacts=item.impacts||[]; const open=impacts.filter(i=>i.status==='OPEN').length; const high=impacts.filter(i=>i.risk_level==='HIGH').length; const plans=impacts.filter(i=>i.target_type==='PLAN').length; const learn=impacts.filter(i=>i.target_type==='LEARNING').length;
  $('impactSummary').innerHTML=[['Affected targets',impacts.length],['Open impacts',open],['Plan impacts',plans],['Learning impacts',learn],['High risk',high],['Indexed chunks',snap?.indexed_chunks??'—']].map(([l,v])=>`<div class="impact-summary-item"><span>${escapeHtml(l)}</span><strong>${escapeHtml(v)}</strong></div>`).join('');
  $('policyDiff').textContent=det.unified_diff||'Deterministic diff is not available in the stored change payload.'; $('policyDiff').classList.toggle('hidden',!state.diffExpanded); $('toggleDiffButton').textContent=state.diffExpanded?'Collapse diff':'Expand diff';
  renderImpactTable();
}

function renderImpactTable(){ const impacts=state.selected?.impacts||[]; $('impactCountLabel').textContent=`${impacts.length} IMPACT${impacts.length===1?'':'S'}`; const body=$('impactRows'); if(!impacts.length){ body.innerHTML='<tr class="empty-row"><td colspan="6"><div class="empty-state compact-empty"><strong>No linked impacts</strong><span>This policy change did not affect any currently linked plan or learning record.</span></div></td></tr>'; return; }
  body.innerHTML=impacts.map(i=>{ const canRegen=i.target_type==='PLAN'&&i.recommended_action==='REGENERATE'&&i.status==='OPEN'; const action=canRegen?`<button class="primary-mini" data-regenerate="${escapeHtml(i.id)}">Regenerate</button>`:`<span class="no-action">${i.recommended_action==='NO_ACTION'?'Preserve':'Review'}</span>`; return `<tr><td><div class="impact-target"><strong>${escapeHtml(shortId(i.target_id,12))}</strong><button class="copy-mini" data-copy="${escapeHtml(i.target_id)}" title="Copy target ID">⧉</button></div><small>${escapeHtml(i.explanation)}</small></td><td><span class="target-type ${String(i.target_type).toLowerCase()}">${escapeHtml(i.target_type)}</span></td><td><span class="guardian-risk ${riskClass(i.risk_level)}">${escapeHtml(i.risk_level)}</span></td><td><span class="recommendation-chip">${escapeHtml(i.recommended_action.replaceAll('_',' '))}</span></td><td><span class="guardian-state ${impactStateClass(i.status)}">${escapeHtml(i.status)}</span></td><td>${action}</td></tr>`; }).join('');
  body.querySelectorAll('[data-regenerate]').forEach(b=>b.addEventListener('click',()=>{ $('regenerateImpactId').value=b.dataset.regenerate; $('regenerateComment').value=''; openModal('regenerateModal'); }));
  body.querySelectorAll('[data-copy]').forEach(b=>b.addEventListener('click',async()=>{ await navigator.clipboard.writeText(b.dataset.copy); showToast('Target ID copied.','success'); }));
}

async function activatePolicy(event){ event.preventDefault(); const payload={policy_code:$('policyCode').value.trim(),title:$('policyTitle').value.trim(),version_number:Number($('policyVersion').value),department:$('policyDepartment').value.trim(),effective_from:$('policyEffectiveDate').value,uploaded_by:$('policyUploadedBy').value,content_text:$('policyContent').value.trim()};
  if(payload.content_text.length<40){showToast('Policy content must contain at least 40 characters.','error');return;}
  $('activateSubmitButton').disabled=true; $('activationProgress').classList.remove('hidden');
  try{ const response=await api('/policy-guardian/activate',{method:'POST',body:JSON.stringify(payload)}); saveSnapshot(response); trackId(response.policy_change.id); closeModal('activatePolicyModal'); $('activatePolicyForm').reset(); setDefaultDate(); showToast(`Policy ${response.new_version.policy_code} V${response.new_version.version_number} activated.`,'success'); await loadChanges(); selectChange(response.policy_change.id); }
  catch(e){ showToast(e.message,'error'); }
  finally{ $('activateSubmitButton').disabled=false; $('activationProgress').classList.add('hidden'); }
}

async function trackChange(event){ event.preventDefault(); const id=$('trackChangeId').value.trim(); if(!id)return; try{ const item=await fetchChange(id); trackId(id); closeModal('trackChangeModal'); $('trackChangeForm').reset(); await loadChanges(); selectChange(id); showToast(`Tracking ${item.change.policy_code} change.`,'success'); }catch(e){showToast(e.message,'error');} }

async function regenerateImpact(event){ event.preventDefault(); const impactId=$('regenerateImpactId').value; $('regenerateSubmitButton').disabled=true; try{ const result=await api(`/policy-guardian/impacts/${encodeURIComponent(impactId)}/regenerate`,{method:'POST',body:JSON.stringify({resolved_by:$('resolvedBy').value,comment:$('regenerateComment').value.trim()})}); state.remediation=result; closeModal('regenerateModal'); $('remediationResult').innerHTML=`<div class="success-mark">✓</div><div class="remediation-result-grid"><div><span>New revision</span><strong>${escapeHtml(result.new_revision)}</strong></div><div><span>Plan status</span><strong>${escapeHtml(result.new_plan_status)}</strong></div><div><span>Approval</span><strong>${escapeHtml(result.approval_status)}</strong></div><div><span>Case status</span><strong>${escapeHtml(result.case_status)}</strong></div></div><p>Stale plan <code>${escapeHtml(shortId(result.stale_plan_id,12))}</code> was preserved and a new plan revision was created under the current policy.</p>`; openModal('remediationResultModal'); await loadChanges(); if(state.selectedId) selectChange(state.selectedId,false); showToast('Impacted plan regenerated.','success'); }catch(e){showToast(e.message,'error');}finally{$('regenerateSubmitButton').disabled=false;} }

function setDefaultDate(){ const d=new Date(); const yyyy=d.getFullYear(), mm=String(d.getMonth()+1).padStart(2,'0'), dd=String(d.getDate()).padStart(2,'0'); $('policyEffectiveDate').value=`${yyyy}-${mm}-${dd}`; $('policyVersion').value='2'; }

$('activatePolicyButton').addEventListener('click',()=>openModal('activatePolicyModal'));
$('trackChangeButton').addEventListener('click',()=>openModal('trackChangeModal'));
$('activatePolicyForm').addEventListener('submit',activatePolicy);
$('trackChangeForm').addEventListener('submit',trackChange);
$('regenerateForm').addEventListener('submit',regenerateImpact);
$('refreshGuardian').addEventListener('click',async()=>{await Promise.all([loadHealth(),loadChanges()]);showToast('Policy Guardian refreshed.','success');});
$('refreshSelectedButton').addEventListener('click',async()=>{if(!state.selectedId)return; const refreshed=await fetchChange(state.selectedId); state.changes=state.changes.map(x=>x.id===state.selectedId?refreshed:x); state.selected=refreshed; renderMetrics();renderChangeTable();renderDetail();showToast('Selected change refreshed.','success');});
$('guardianSearch').addEventListener('input',renderChangeTable); $('riskFilter').addEventListener('change',renderChangeTable);
$('toggleDiffButton').addEventListener('click',()=>{state.diffExpanded=!state.diffExpanded;renderDetail();});
$('copyChangeIdButton').addEventListener('click',async()=>{if(!state.selectedId)return;await navigator.clipboard.writeText(state.selectedId);showToast('Change ID copied.','success');});
$('openRemediatedCaseButton').addEventListener('click',()=>{if(state.remediation?.case_id) location.href=`workspace.html?case=${encodeURIComponent(state.remediation.case_id)}`;});
$('notificationButton').addEventListener('click',()=>location.href='security.html');
document.querySelectorAll('[data-close-modal]').forEach(b=>b.addEventListener('click',()=>closeModal(b.dataset.closeModal)));
document.querySelectorAll('.modal-backdrop').forEach(m=>m.addEventListener('click',(e)=>{if(e.target===m)closeModal(m.id);}));
document.querySelectorAll('[data-coming-soon]').forEach(b=>b.addEventListener('click',()=>showToast(`${b.dataset.comingSoon} will be built in the next frontend step.`)));
window.addEventListener('keydown',(e)=>{ if(e.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('guardianSearch').focus();} if(e.key==='Escape')document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(m=>closeModal(m.id)); });

setDefaultDate();
Promise.all([loadHealth(), loadChanges({selectFirst:true})]).catch(console.error);
