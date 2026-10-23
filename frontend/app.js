const API_BASE = '/api';
const STORAGE_KEY = 'livingops.trackedCases.v1';

const $ = (id) => document.getElementById(id);
const state = { health: null, alerts: [], spec: null, cases: [], filter: '' };

const ONBOARDING_FACTS = {
  requires_email: true,
  requires_github: true,
  requires_laptop: true,
  requires_training: true,
  start_date: new Date().toISOString().slice(0, 10)
};
const OFFBOARDING_FACTS = {
  last_working_day: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
  successor_person_id: '22222222-2222-4222-8222-222222222222',
  manager_id: '22222222-2222-4222-8222-222222222222'
};

function showToast(message, type = '') {
  const toast = $('toast');
  toast.textContent = message;
  toast.className = `toast show ${type}`.trim();
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = 'toast'; }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  let payload = null;
  const text = await response.text();
  if (text) {
    try { payload = JSON.parse(text); } catch { payload = { detail: text }; }
  }
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
  }
  return payload;
}

function setServiceState(el, value) {
  el.classList.remove('ok', 'bad', 'neutral');
  if (value === 'ok') { el.classList.add('ok'); el.innerHTML = '<i></i>Operational'; }
  else if (value === 'failed') { el.classList.add('bad'); el.innerHTML = '<i></i>Degraded'; }
  else { el.classList.add('neutral'); el.innerHTML = '<i></i>Unknown'; }
}

function renderHealth() {
  const h = state.health;
  const ok = h?.status === 'ok';
  $('systemMetric').textContent = ok ? 'Operational' : h ? 'Degraded' : 'Offline';
  $('systemMetricNote').textContent = h ? `${h.database === 'ok' ? 'Database connected' : 'Database issue'} · ${h.qdrant === 'ok' ? 'Qdrant connected' : 'Qdrant issue'}` : 'Backend could not be reached';
  $('healthBadge').textContent = ok ? 'Healthy' : h ? 'Attention' : 'Offline';
  $('healthBadge').className = `status-pill ${ok ? 'ok' : 'bad'}`;
  $('sidebarHealthDot').className = `dot ${ok ? 'ok' : 'bad'}`;
  $('liveDot').className = `dot ${ok ? 'ok' : 'bad'}`;
  $('sidebarHealthText').textContent = ok ? 'System operational' : h ? 'System degraded' : 'Backend offline';
  $('sidebarEnv').textContent = h?.environment ? `${h.environment} environment` : 'LivingOps backend';
  $('environmentValue').textContent = h?.environment || 'Unavailable';
  setServiceState($('apiHealth'), h ? (ok ? 'ok' : 'failed') : 'failed');
  setServiceState($('dbHealth'), h?.database || 'failed');
  setServiceState($('qdrantHealth'), h?.qdrant || 'failed');
}

function renderAlerts() {
  const alerts = state.alerts || [];
  $('alertCount').textContent = alerts.length;
  $('alertMetricNote').textContent = alerts.length ? `${alerts.filter(a => a.alert_status === 'OPEN').length} currently awaiting review` : 'No open anomaly alerts';
  $('notificationBadge').textContent = alerts.length;
  $('notificationBadge').classList.toggle('hidden', alerts.length === 0);

  const holder = $('securityActivity');
  if (!alerts.length) {
    holder.innerHTML = '<div class="security-empty">No security alerts require attention.</div>';
    return;
  }
  const sorted = [...alerts].sort((a,b) => Number(b.anomaly_score || 0) - Number(a.anomaly_score || 0)).slice(0, 4);
  holder.innerHTML = sorted.map(a => {
    const score = Math.round(Number(a.anomaly_score || 0) * 100);
    return `<div class="security-item">
      <div class="score-ring">${score}</div>
      <div class="security-copy"><strong>${escapeHtml(a.event_type || 'Access event')} · ${escapeHtml(a.source || 'Unknown source')}</strong><span>${escapeHtml(a.destination || 'Unknown destination')} · ${formatDate(a.event_time)}</span></div>
      <span class="security-state">${escapeHtml(a.alert_status || 'OPEN')}</span>
    </div>`;
  }).join('');
}

function renderCapabilities() {
  const paths = state.spec?.paths || {};
  const capabilities = [
    ['CA', 'Case Automation', 'Intake, triage and AI planning', ['/cases', '/cases/{case_id}/plan']],
    ['AP', 'Human Approval', 'Controlled decision checkpoints', ['/plans/{plan_id}/submit', '/approvals/{approval_id}/decision']],
    ['PG', 'Policy Guardian', 'Change impact and remediation', ['/policy-guardian/activate', '/policy-guardian/impacts/{impact_id}/regenerate']],
    ['SE', 'Security Monitoring', 'Anomaly scoring and review', ['/access-events', '/security/alerts']],
    ['AU', 'Auditability', 'Timeline and coverage checks', ['/audit/cases/{case_id}/timeline', '/audit/cases/{case_id}/coverage']],
    ['LE', 'Approved Learning', 'Reusable reviewed memory', ['/cases/{case_id}/learning/candidate', '/learning/search']],
  ];
  $('capabilityGrid').innerHTML = capabilities.map(([icon,name,desc,required]) => {
    const ready = required.every(p => Boolean(paths[p]));
    return `<div class="capability"><span class="capability-icon">${icon}</span><div class="capability-copy"><strong>${name}</strong><span>${desc}</span></div><i class="ready-dot ${ready ? '' : 'off'}" title="${ready ? 'Available' : 'Unavailable'}"></i></div>`;
  }).join('');
  const count = Object.keys(paths).filter(p => !['/','/health','/openapi.json','/docs','/redoc'].includes(p)).length;
  $('endpointCount').textContent = count;
}

function getTrackedIds() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; }
}
function saveTrackedIds(ids) { localStorage.setItem(STORAGE_KEY, JSON.stringify([...new Set(ids)])); }

async function loadTrackedCases() {
  const ids = getTrackedIds();
  const cases = [];
  const validIds = [];
  for (const id of ids) {
    try { const item = await api(`/cases/${id}`); cases.push(item); validIds.push(id); } catch (_) { /* stale local id */ }
  }
  saveTrackedIds(validIds);
  state.cases = cases;
  renderCases();
}

function renderCases() {
  const body = $('caseTableBody');
  const filtered = state.cases.filter(c => {
    if (!state.filter) return true;
    const haystack = `${c.id} ${c.case_type} ${c.status} ${c.priority}`.toLowerCase();
    return haystack.includes(state.filter.toLowerCase());
  });
  $('trackedCaseCount').textContent = state.cases.length;
  if (!filtered.length) {
    body.innerHTML = `<tr class="empty-row"><td colspan="6"><div class="empty-state"><div class="empty-icon">▤</div><strong>${state.filter ? 'No matching cases' : 'No tracked cases yet'}</strong><span>${state.filter ? 'Try a different search.' : 'Create a case or track an existing case ID to see live status here.'}</span></div></td></tr>`;
    return;
  }
  body.innerHTML = filtered.map(c => `<tr class="dashboard-case-row" data-open-workspace="${escapeHtml(c.id)}">
    <td><span class="case-id">${escapeHtml(shortId(c.id))}</span></td>
    <td><span class="case-type">${pretty(c.case_type)}</span></td>
    <td><span class="case-status ${escapeHtml(c.status)}">${pretty(c.status)}</span></td>
    <td><span class="priority-${String(c.priority).toLowerCase()}">${pretty(c.priority)}</span></td>
    <td>${formatDate(c.updated_at)}</td>
    <td><button class="table-open-button" data-open-workspace="${escapeHtml(c.id)}">Open</button></td>
  </tr>`).join('');
  body.querySelectorAll('[data-open-workspace]').forEach(el => el.addEventListener('click', (event) => {
    event.stopPropagation();
    window.location.href = `workspace.html?case=${encodeURIComponent(el.dataset.openWorkspace)}`;
  }));
}

function renderAttention() {
  const items = [];
  if (!state.health) items.push(['red','Backend unavailable','Start FastAPI on 127.0.0.1:8000 to enable live operations.','Now']);
  else {
    if (state.health.database !== 'ok') items.push(['red','PostgreSQL requires attention','Database health check is failing.','Live']);
    if (state.health.qdrant !== 'ok') items.push(['amber','Qdrant requires attention','Vector retrieval dependency is degraded.','Live']);
  }
  const openAlerts = state.alerts.filter(a => a.alert_status === 'OPEN');
  if (openAlerts.length) items.push(['red',`${openAlerts.length} security alert${openAlerts.length === 1 ? '' : 's'} awaiting review`,'Anomalous access activity needs a human decision.','Live']);
  const reviewCases = state.cases.filter(c => ['HUMAN_REVIEW','PAUSED','FAILED'].includes(c.status));
  if (reviewCases.length) items.push(['amber',`${reviewCases.length} tracked case${reviewCases.length === 1 ? '' : 's'} need intervention`,'Paused, failed or human-review state detected.','Session']);
  if (!items.length) items.push(['green','No urgent operational issues','Live services and tracked cases show no immediate blockers.','Now']);

  $('attentionCount').textContent = items.filter(i => i[0] !== 'green').length;
  $('attentionList').innerHTML = items.map(([color,title,desc,time]) => `<div class="attention-item"><span class="attention-bullet ${color}"></span><div class="attention-copy"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(desc)}</span></div><span class="attention-time">${time}</span></div>`).join('');
}

async function refreshDashboard(silent = false) {
  if (!silent) $('lastUpdated').textContent = 'Refreshing…';
  const [healthResult, alertsResult, specResult] = await Promise.allSettled([
    api('/health'), api('/security/alerts'), api('/openapi.json')
  ]);
  state.health = healthResult.status === 'fulfilled' ? healthResult.value : null;
  state.alerts = alertsResult.status === 'fulfilled' && Array.isArray(alertsResult.value) ? alertsResult.value : [];
  state.spec = specResult.status === 'fulfilled' ? specResult.value : null;
  await loadTrackedCases();
  renderHealth(); renderAlerts(); renderCapabilities(); renderAttention();
  $('lastUpdated').textContent = `Updated ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`;
  if (!silent && !state.health) showToast('Backend is unreachable. Start FastAPI, then refresh.', 'error');
}

function openModal(id) { $(id).classList.remove('hidden'); }
function closeModal(id) { $(id).classList.add('hidden'); }

function updateCaseFactsTemplate() {
  const onboarding = $('caseType').value === 'ONBOARDING';
  $('caseFacts').value = JSON.stringify(onboarding ? ONBOARDING_FACTS : OFFBOARDING_FACTS, null, 2);
  $('factsHelp').textContent = onboarding ? 'Onboarding requirements are explicit so deterministic validation can enforce them.' : 'Offboarding uses the demo engineering manager as successor fallback.';
  $('subjectPerson').value = onboarding ? '44444444-4444-4444-8444-444444444444' : '66666666-6666-4666-8666-666666666666';
}

async function createCase(event) {
  event.preventDefault();
  const submit = $('createCaseSubmit');
  submit.disabled = true; submit.textContent = 'Creating…';
  try {
    let facts;
    try { facts = JSON.parse($('caseFacts').value || '{}'); } catch { throw new Error('Case facts must be valid JSON.'); }
    const payload = {
      case_type: $('caseType').value,
      subject_person_id: $('subjectPerson').value,
      created_by_id: $('createdBy').value,
      priority: $('casePriority').value,
      case_facts: facts,
    };
    const created = await api('/cases', { method: 'POST', body: JSON.stringify(payload) });
    const triaged = await api(`/cases/${created.id}/triage`, { method: 'POST', body: '{}' });
    saveTrackedIds([created.id, ...getTrackedIds()]);
    closeModal('newCaseModal');
    await refreshDashboard(true);
    showToast(`Case created and triaged to ${pretty(triaged.current_status)}.`, 'success');
  } catch (err) { showToast(err.message || 'Could not create case.', 'error'); }
  finally { submit.disabled = false; submit.innerHTML = 'Create & Triage'; }
}

async function trackCase(event) {
  event.preventDefault();
  const id = $('trackCaseId').value.trim();
  try {
    await api(`/cases/${id}`);
    saveTrackedIds([id, ...getTrackedIds()]);
    closeModal('trackCaseModal'); $('trackCaseId').value = '';
    await loadTrackedCases(); renderAttention();
    showToast('Case added to the dashboard.', 'success');
  } catch (err) { showToast(err.message || 'Case could not be found.', 'error'); }
}

function pretty(value) { return String(value || '').toLowerCase().split('_').map(w => w.charAt(0).toUpperCase()+w.slice(1)).join(' '); }
function shortId(id) { return `LO-${String(id).split('-')[0].toUpperCase()}`; }
function formatDate(value) { if (!value) return '—'; const d = new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}); }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

$('newCaseButton').addEventListener('click', () => { updateCaseFactsTemplate(); openModal('newCaseModal'); });
$('trackCaseButton').addEventListener('click', () => openModal('trackCaseModal'));
$('newCaseForm').addEventListener('submit', createCase);
$('trackCaseForm').addEventListener('submit', trackCase);
$('caseType').addEventListener('change', updateCaseFactsTemplate);
$('refreshButton').addEventListener('click', () => refreshDashboard());
$('viewAllAlertsButton').addEventListener('click', () => refreshDashboard());
$('notificationButton').addEventListener('click', () => { document.querySelector('.security-panel').scrollIntoView({behavior:'smooth',block:'center'}); });
$('searchInput').addEventListener('input', e => { state.filter = e.target.value; renderCases(); });

document.querySelectorAll('[data-close-modal]').forEach(b => b.addEventListener('click', () => closeModal(b.dataset.closeModal)));
document.querySelectorAll('.modal-backdrop').forEach(m => m.addEventListener('click', e => { if (e.target === m) closeModal(m.id); }));
document.querySelectorAll('[data-coming-soon]').forEach(b => b.addEventListener('click', () => showToast(`${b.dataset.comingSoon} will be built as the next page.`)));
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') { e.preventDefault(); $('searchInput').focus(); }
  if (e.key === 'Escape') document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(m => closeModal(m.id));
});

updateCaseFactsTemplate();
refreshDashboard(true);
setInterval(() => refreshDashboard(true), 45000);
