const API_BASE = '/api';
const STORAGE_KEY = 'livingops.trackedCases.v1';

const $ = (id) => document.getElementById(id);

const PEOPLE = {
  '11111111-1111-4111-8111-111111111111': { name: 'Farhana Islam', role: 'HR Manager' },
  '22222222-2222-4222-8222-222222222222': { name: 'Nabil Chowdhury', role: 'Engineering Manager' },
  '33333333-3333-4333-8333-333333333333': { name: 'Tahmid Hasan', role: 'IT Security Owner' },
  '44444444-4444-4444-8444-444444444444': { name: 'Amina Rahman', role: 'AI Engineer' },
  '55555555-5555-4555-8555-555555555555': { name: 'Rafi Ahmed', role: 'AI Engineer' },
  '66666666-6666-4666-8666-666666666666': { name: 'Arif Hossain', role: 'Senior Software Engineer' },
};

const ONBOARDING_FACTS = {
  requires_email: true,
  requires_github: true,
  requires_laptop: true,
  requires_training: true,
  start_date: new Date().toISOString().slice(0, 10),
};

const OFFBOARDING_FACTS = {
  last_working_day: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
  successor_person_id: '22222222-2222-4222-8222-222222222222',
  manager_id: '22222222-2222-4222-8222-222222222222',
};

const state = {
  health: null,
  alerts: [],
  cases: [],
  selectedCase: null,
  filters: { search: '', type: '', status: '', priority: '' },
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

  const text = await response.text();
  let payload = null;
  if (text) {
    try { payload = JSON.parse(text); }
    catch { payload = { detail: text }; }
  }

  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
  }
  return payload;
}

function getTrackedIds() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function saveTrackedIds(ids) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...new Set(ids)]));
}

function personFor(caseItem) {
  return PEOPLE[String(caseItem.subject_person_id)] || { name: 'Unknown employee', role: 'Employee' };
}

function pretty(value) {
  return String(value || '').toLowerCase().split('_').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function shortId(id) {
  return `LO-${String(id || '').split('-')[0].toUpperCase()}`;
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));
}

function openModal(id) { $(id).classList.remove('hidden'); }
function closeModal(id) { $(id).classList.add('hidden'); }

function renderHealth() {
  const healthy = state.health?.status === 'ok';
  $('sidebarHealthDot').className = `dot ${healthy ? 'ok' : 'bad'}`;
  $('liveDot').className = `dot ${healthy ? 'ok' : 'bad'}`;
  $('sidebarHealthText').textContent = healthy ? 'System operational' : state.health ? 'System degraded' : 'Backend offline';
  $('sidebarEnv').textContent = state.health?.environment ? `${state.health.environment} environment` : 'LivingOps backend';
}

function renderNotifications() {
  const openAlerts = state.alerts.filter((alert) => alert.alert_status === 'OPEN');
  $('notificationBadge').textContent = openAlerts.length;
  $('notificationBadge').classList.toggle('hidden', openAlerts.length === 0);
}

function filteredCases() {
  const search = state.filters.search.trim().toLowerCase();
  return state.cases.filter((caseItem) => {
    const person = personFor(caseItem);
    const searchText = `${caseItem.id} ${shortId(caseItem.id)} ${person.name} ${caseItem.case_type} ${caseItem.status} ${caseItem.priority}`.toLowerCase();
    if (search && !searchText.includes(search)) return false;
    if (state.filters.type && caseItem.case_type !== state.filters.type) return false;
    if (state.filters.status && caseItem.status !== state.filters.status) return false;
    if (state.filters.priority && caseItem.priority !== state.filters.priority) return false;
    return true;
  });
}

function renderSummary() {
  const activeStatuses = new Set(['NEW', 'TRIAGE', 'PLANNING', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING', 'RETRYING']);
  const reviewStatuses = new Set(['HUMAN_REVIEW', 'PAUSED', 'FAILED']);
  $('summaryAll').textContent = state.cases.length;
  $('summaryActive').textContent = state.cases.filter((item) => activeStatuses.has(item.status)).length;
  $('summaryReview').textContent = state.cases.filter((item) => reviewStatuses.has(item.status)).length;
  $('summaryCompleted').textContent = state.cases.filter((item) => item.status === 'COMPLETED').length;
}

function populateStatusFilter() {
  const current = $('statusFilter').value;
  const statuses = [...new Set(state.cases.map((item) => item.status).filter(Boolean))].sort();
  $('statusFilter').innerHTML = '<option value="">All statuses</option>' + statuses.map((status) => `<option value="${escapeHtml(status)}">${escapeHtml(pretty(status))}</option>`).join('');
  if (statuses.includes(current)) $('statusFilter').value = current;
}

function renderCases() {
  renderSummary();
  populateStatusFilter();

  const cases = filteredCases();
  $('caseResultCount').textContent = `${cases.length} case${cases.length === 1 ? '' : 's'}`;
  const body = $('casesTableBody');

  if (!cases.length) {
    const hasCases = state.cases.length > 0;
    body.innerHTML = `<tr class="empty-row"><td colspan="7"><div class="empty-state"><div class="empty-icon">▤</div><strong>${hasCases ? 'No cases match these filters' : 'No tracked cases yet'}</strong><span>${hasCases ? 'Clear or adjust filters to see more cases.' : 'Create a case or track an existing UUID to begin.'}</span>${hasCases ? '<button class="secondary-button empty-action" id="emptyResetFilters">Clear Filters</button>' : '<button class="primary-button empty-action" id="emptyNewCaseButton">＋ New Case</button>'}</div></td></tr>`;
    const emptyNew = $('emptyNewCaseButton');
    if (emptyNew) emptyNew.addEventListener('click', () => { updateCaseFactsTemplate(); openModal('newCaseModal'); });
    const emptyReset = $('emptyResetFilters');
    if (emptyReset) emptyReset.addEventListener('click', resetFilters);
    return;
  }

  body.innerHTML = cases.map((caseItem) => {
    const person = personFor(caseItem);
    return `<tr class="case-row" data-case-id="${escapeHtml(caseItem.id)}">
      <td><div class="case-primary"><span class="case-id">${escapeHtml(shortId(caseItem.id))}</span><span class="case-uuid-mini">${escapeHtml(String(caseItem.id).slice(0, 8))}</span></div></td>
      <td><div class="person-cell"><span class="person-avatar">${escapeHtml(person.name.split(' ').map((part) => part[0]).join('').slice(0, 2))}</span><div><strong>${escapeHtml(person.name)}</strong><span>${escapeHtml(person.role)}</span></div></div></td>
      <td><span class="type-badge ${String(caseItem.case_type).toLowerCase()}">${escapeHtml(pretty(caseItem.case_type))}</span></td>
      <td><span class="case-status ${escapeHtml(caseItem.status)}">${escapeHtml(pretty(caseItem.status))}</span></td>
      <td><span class="priority-${String(caseItem.priority).toLowerCase()}">${escapeHtml(pretty(caseItem.priority))}</span></td>
      <td>${escapeHtml(formatDate(caseItem.updated_at))}</td>
      <td><button class="table-open-button" data-open-case="${escapeHtml(caseItem.id)}">View</button></td>
    </tr>`;
  }).join('');

  body.querySelectorAll('[data-open-case]').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      window.location.href = `workspace.html?case=${encodeURIComponent(button.dataset.openCase)}`;
    });
  });
  body.querySelectorAll('.case-row').forEach((row) => row.addEventListener('click', () => { window.location.href = `workspace.html?case=${encodeURIComponent(row.dataset.caseId)}`; }));
}

function openCaseDetails(caseId) {
  const caseItem = state.cases.find((item) => String(item.id) === String(caseId));
  if (!caseItem) return;
  state.selectedCase = caseItem;
  const person = personFor(caseItem);

  $('detailsCaseId').textContent = shortId(caseItem.id);
  $('detailsPerson').textContent = person.name;
  $('detailsRole').textContent = person.role;
  $('detailsStatus').textContent = pretty(caseItem.status);
  $('detailsStatus').className = `case-status ${caseItem.status}`;
  $('detailsType').textContent = pretty(caseItem.case_type);
  $('detailsPriority').textContent = pretty(caseItem.priority);
  $('detailsCreated').textContent = formatDate(caseItem.created_at);
  $('detailsUpdated').textContent = formatDate(caseItem.updated_at);
  $('detailsUuid').textContent = caseItem.id;
  $('detailsFacts').textContent = JSON.stringify(caseItem.case_facts || {}, null, 2);

  const failure = $('detailsFailure');
  if (caseItem.failure_reason) {
    failure.textContent = `Failure reason: ${caseItem.failure_reason}`;
    failure.classList.remove('hidden');
  } else {
    failure.classList.add('hidden');
    failure.textContent = '';
  }

  openModal('caseDetailsModal');
}

async function loadTrackedCases() {
  const ids = getTrackedIds();
  const loaded = [];
  const validIds = [];

  await Promise.all(ids.map(async (id) => {
    try {
      const item = await api(`/cases/${id}`);
      loaded.push(item);
      validIds.push(id);
    } catch (_) {
      // Ignore stale locally tracked IDs after backend reset.
    }
  }));

  loaded.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
  state.cases = loaded;
  saveTrackedIds(validIds);
  renderCases();
}

async function refreshPage(silent = false) {
  if (!silent) $('lastUpdated').textContent = 'Refreshing…';
  const [healthResult, alertsResult] = await Promise.allSettled([
    api('/health'),
    api('/security/alerts'),
  ]);
  state.health = healthResult.status === 'fulfilled' ? healthResult.value : null;
  state.alerts = alertsResult.status === 'fulfilled' && Array.isArray(alertsResult.value) ? alertsResult.value : [];
  await loadTrackedCases();
  renderHealth();
  renderNotifications();
  $('lastUpdated').textContent = `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  if (!silent && !state.health) showToast('Backend is unreachable. Start FastAPI, then refresh.', 'error');
}

function updateCaseFactsTemplate() {
  const onboarding = $('caseType').value === 'ONBOARDING';
  $('caseFacts').value = JSON.stringify(onboarding ? ONBOARDING_FACTS : OFFBOARDING_FACTS, null, 2);
  $('factsHelp').textContent = onboarding
    ? 'Onboarding requirements are explicit so deterministic validation can enforce them.'
    : 'Offboarding uses the demo engineering manager as successor fallback.';
  $('subjectPerson').value = onboarding
    ? '44444444-4444-4444-8444-444444444444'
    : '66666666-6666-4666-8666-666666666666';
}

async function createCase(event) {
  event.preventDefault();
  const submit = $('createCaseSubmit');
  submit.disabled = true;
  submit.textContent = 'Creating…';
  try {
    let facts;
    try { facts = JSON.parse($('caseFacts').value || '{}'); }
    catch { throw new Error('Case facts must be valid JSON.'); }

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
    await refreshPage(true);
    showToast(`Case created and triaged to ${pretty(triaged.current_status)}.`, 'success');
  } catch (error) {
    showToast(error.message || 'Could not create case.', 'error');
  } finally {
    submit.disabled = false;
    submit.textContent = 'Create & Triage';
  }
}

async function trackCase(event) {
  event.preventDefault();
  const id = $('trackCaseId').value.trim();
  try {
    await api(`/cases/${id}`);
    saveTrackedIds([id, ...getTrackedIds()]);
    closeModal('trackCaseModal');
    $('trackCaseId').value = '';
    await loadTrackedCases();
    showToast('Case added to your operational case list.', 'success');
  } catch (error) {
    showToast(error.message || 'Case could not be found.', 'error');
  }
}

function resetFilters() {
  state.filters = { search: '', type: '', status: '', priority: '' };
  $('caseSearch').value = '';
  $('globalCaseSearch').value = '';
  $('typeFilter').value = '';
  $('statusFilter').value = '';
  $('priorityFilter').value = '';
  renderCases();
}

function syncSearch(value) {
  state.filters.search = value;
  if ($('caseSearch').value !== value) $('caseSearch').value = value;
  if ($('globalCaseSearch').value !== value) $('globalCaseSearch').value = value;
  renderCases();
}

$('newCaseButton').addEventListener('click', () => { updateCaseFactsTemplate(); openModal('newCaseModal'); });
$('emptyNewCaseButton')?.addEventListener('click', () => { updateCaseFactsTemplate(); openModal('newCaseModal'); });
$('trackCaseButton').addEventListener('click', () => openModal('trackCaseModal'));
$('newCaseForm').addEventListener('submit', createCase);
$('trackCaseForm').addEventListener('submit', trackCase);
$('caseType').addEventListener('change', updateCaseFactsTemplate);
$('refreshButton').addEventListener('click', () => refreshPage());
$('notificationButton').addEventListener('click', () => showToast(state.alerts.length ? `${state.alerts.filter((alert) => alert.alert_status === 'OPEN').length} open security alerts.` : 'No security alerts require attention.'));
$('caseSearch').addEventListener('input', (event) => syncSearch(event.target.value));
$('globalCaseSearch').addEventListener('input', (event) => syncSearch(event.target.value));
$('typeFilter').addEventListener('change', (event) => { state.filters.type = event.target.value; renderCases(); });
$('statusFilter').addEventListener('change', (event) => { state.filters.status = event.target.value; renderCases(); });
$('priorityFilter').addEventListener('change', (event) => { state.filters.priority = event.target.value; renderCases(); });
$('resetFilters').addEventListener('click', resetFilters);
$('copyCaseIdButton').addEventListener('click', async () => {
  if (!state.selectedCase) return;
  try {
    await navigator.clipboard.writeText(state.selectedCase.id);
    showToast('Case ID copied.', 'success');
  } catch {
    showToast('Could not access the clipboard.', 'error');
  }
});
$('workspaceButton').addEventListener('click', () => { if (state.selectedCase) window.location.href = `workspace.html?case=${encodeURIComponent(state.selectedCase.id)}`; });

document.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', () => closeModal(button.dataset.closeModal)));
document.querySelectorAll('.modal-backdrop').forEach((modal) => modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(modal.id); }));
document.querySelectorAll('[data-coming-soon]').forEach((button) => button.addEventListener('click', () => showToast(`${button.dataset.comingSoon} will be built in a later page.`)));
document.addEventListener('keydown', (event) => {
  if (event.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA' && document.activeElement?.tagName !== 'SELECT') {
    event.preventDefault();
    $('globalCaseSearch').focus();
  }
  if (event.key === 'Escape') document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach((modal) => closeModal(modal.id));
});

updateCaseFactsTemplate();
refreshPage(true);
setInterval(() => refreshPage(true), 45000);
