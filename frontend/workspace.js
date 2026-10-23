const API_BASE = '/api';
const STORAGE_KEY = 'livingops.trackedCases.v1';
const WORKSPACE_STORAGE_KEY = 'livingops.workspace.v1';

const $ = (id) => document.getElementById(id);

const PEOPLE = {
  '11111111-1111-4111-8111-111111111111': { name: 'Farhana Islam', role: 'HR Manager' },
  '22222222-2222-4222-8222-222222222222': { name: 'Nabil Chowdhury', role: 'Engineering Manager' },
  '33333333-3333-4333-8333-333333333333': { name: 'Tahmid Hasan', role: 'IT Security Owner' },
  '44444444-4444-4444-8444-444444444444': { name: 'Amina Rahman', role: 'AI Engineer' },
  '55555555-5555-4555-8555-555555555555': { name: 'Rafi Ahmed', role: 'AI Engineer' },
  '66666666-6666-4666-8666-666666666666': { name: 'Arif Hossain', role: 'Senior Software Engineer' },
};

const state = {
  caseId: new URLSearchParams(location.search).get('case'),
  caseItem: null,
  health: null,
  evidence: null,
  audit: null,
  coverage: null,
  local: { plan: null, approval: null, execution: null, evidence: null },
  activeTab: 'overview',
};

function showToast(message, type = '') {
  const toast = $('toast');
  toast.textContent = message;
  toast.className = `toast show ${type}`.trim();
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = 'toast'; }, 3400);
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

function pretty(value) {
  return String(value || '').toLowerCase().split('_').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));
}

function shortId(id) {
  return `LO-${String(id || '').split('-')[0].toUpperCase()}`;
}

function formatDate(value, includeTime = true) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], includeTime
    ? { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { month: 'short', day: 'numeric', year: 'numeric' });
}

function person(id) {
  return PEOPLE[String(id)] || { name: 'Unknown user', role: 'Employee' };
}

function getWorkspaceStore() {
  try {
    const value = JSON.parse(localStorage.getItem(WORKSPACE_STORAGE_KEY) || '{}');
    return value && typeof value === 'object' ? value : {};
  } catch {
    return {};
  }
}

function loadLocalState() {
  const store = getWorkspaceStore();
  state.local = store[state.caseId] || { plan: null, approval: null, execution: null, evidence: null };
  state.local.evidence = state.local.evidence || null;
}

function saveLocalState() {
  const store = getWorkspaceStore();
  store[state.caseId] = state.local;
  localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(store));
}

function ensureTrackedCase() {
  try {
    const ids = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const list = Array.isArray(ids) ? ids : [];
    if (!list.includes(state.caseId)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([state.caseId, ...list]));
    }
  } catch {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([state.caseId]));
  }
}

function openModal(id) { $(id).classList.remove('hidden'); }
function closeModal(id) { $(id).classList.add('hidden'); }

function setLoading(loading) {
  $('workspaceLoading').classList.toggle('hidden', !loading);
  $('workspaceApp').classList.toggle('hidden', loading || !state.caseItem);
}

function showWorkspaceError(message) {
  $('workspaceLoading').classList.add('hidden');
  $('workspaceApp').classList.add('hidden');
  $('workspaceError').classList.remove('hidden');
  $('workspaceErrorMessage').textContent = message;
}

function renderHealth() {
  const healthy = state.health?.status === 'ok';
  $('sidebarHealthDot').className = `dot ${healthy ? 'ok' : state.health ? 'bad' : 'neutral'}`;
  $('sidebarHealthText').textContent = healthy ? 'System operational' : state.health ? 'System degraded' : 'Backend offline';
  $('sidebarEnv').textContent = state.health?.environment ? `${state.health.environment} environment` : 'LivingOps backend';
}

function workflowIndex(status) {
  const map = {
    NEW: 0,
    PLANNING: 1,
    PENDING_APPROVAL: 2,
    APPROVED: 3,
    EXECUTING: 4,
    COMPLETED: 5,
    FAILED: 4,
    HUMAN_REVIEW: 2,
    PAUSED: 2,
    CANCELLED: 0,
  };
  return map[status] ?? 0;
}

function renderWorkflow() {
  const labels = ['Created', 'Planning', 'Approval', 'Approved', 'Execution', 'Completed'];
  const current = workflowIndex(state.caseItem.status);
  $('workflowSteps').innerHTML = labels.map((label, index) => {
    const complete = index < current || state.caseItem.status === 'COMPLETED';
    const active = index === current && state.caseItem.status !== 'COMPLETED';
    return `<div class="workflow-step ${complete ? 'complete' : ''} ${active ? 'active' : ''}">
      <div class="workflow-node">${complete ? '✓' : index + 1}</div>
      <span>${escapeHtml(label)}</span>
      ${index < labels.length - 1 ? '<i></i>' : ''}
    </div>`;
  }).join('');

  const captions = {
    NEW: 'Case intake created',
    PLANNING: 'Ready for policy-grounded planning',
    PENDING_APPROVAL: 'Waiting for a human decision',
    APPROVED: 'Approved and ready for execution',
    EXECUTING: 'Actions are being dispatched and verified',
    COMPLETED: 'All required actions are verified',
    FAILED: 'Execution requires attention',
    HUMAN_REVIEW: 'Human review is required',
    PAUSED: 'Case paused by governance controls',
    CANCELLED: 'Case cancelled',
  };
  $('workflowCaption').textContent = captions[state.caseItem.status] || 'Operational workflow';
}

function renderHeader() {
  const c = state.caseItem;
  const p = person(c.subject_person_id);
  $('headerCaseId').textContent = shortId(c.id);
  $('headerCaseType').textContent = pretty(c.case_type);
  $('headerPerson').textContent = p.name;
  $('headerRole').textContent = p.role;
  $('headerStatus').textContent = pretty(c.status);
  $('headerStatus').className = `case-status ${c.status}`;
  $('headerPriority').textContent = pretty(c.priority);
  $('headerUpdated').textContent = formatDate(c.updated_at);
  document.title = `${shortId(c.id)} · LivingOps AI`;
}

function renderFacts() {
  const facts = state.caseItem.case_facts || {};
  const entries = Object.entries(facts);
  $('factsGrid').innerHTML = entries.length
    ? entries.map(([key, value]) => `<div class="fact-item"><span>${escapeHtml(pretty(key))}</span><strong>${escapeHtml(typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value)}</strong></div>`).join('')
    : '<div class="workspace-empty-inline">No structured case facts were recorded.</div>';
}

function renderOverview() {
  const c = state.caseItem;
  const subject = person(c.subject_person_id);
  const creator = person(c.created_by_id);
  $('employeeInitials').textContent = subject.name.split(' ').map((part) => part[0]).join('').slice(0, 2);
  $('employeeName').textContent = subject.name;
  $('employeeRole').textContent = subject.role;
  $('employeeId').textContent = c.subject_person_id;
  $('overviewType').textContent = pretty(c.case_type);
  $('createdByName').textContent = creator.name;
  $('overviewCreated').textContent = formatDate(c.created_at);
  renderFacts();
  renderNextStep();
  renderRecentActivity();
}

function renderNextStep() {
  const c = state.caseItem;
  let title = 'Review case state';
  let text = 'Use the workspace tabs to inspect the current case context.';
  let action = '';
  if (c.status === 'PLANNING' && !state.local.plan) {
    title = 'Generate the operational plan';
    text = 'Retrieve current policy evidence and create a deterministically validated plan.';
    action = '<button class="primary-button" data-next-action="generate">Generate Plan</button>';
  } else if (c.status === 'PLANNING' && state.local.plan) {
    title = 'Submit the plan for approval';
    text = 'The plan is available and can now enter the human approval checkpoint.';
    action = '<button class="primary-button" data-next-action="submit">Submit for Approval</button>';
  } else if (c.status === 'PENDING_APPROVAL') {
    title = 'Human approval is pending';
    text = 'The assigned manager must approve or reject the plan before execution.';
    action = state.local.approval ? '<button class="primary-button" data-next-action="decision">Review Approval</button>' : '';
  } else if (c.status === 'APPROVED') {
    title = 'Execute the approved plan';
    text = 'Dispatch approved actions through automation and independently verify the resulting resources.';
    action = '<button class="primary-button" data-next-action="execute">Execute Plan</button>';
  } else if (c.status === 'FAILED') {
    title = 'Retry failed execution';
    text = 'Retry is bounded by the backend reliability policy and action attempt limit.';
    action = '<button class="primary-button" data-next-action="retry">Retry Failed Actions</button>';
  } else if (c.status === 'COMPLETED') {
    title = 'Operation completed';
    text = 'The case reached a verified terminal state. Review the audit tab for the complete trace.';
    action = '<button class="secondary-button" data-open-tab="audit">View Audit Trail</button>';
  } else if (['HUMAN_REVIEW', 'PAUSED'].includes(c.status)) {
    title = 'Human attention required';
    text = c.failure_reason || 'Governance controls require a human review before the workflow can continue.';
  }
  $('nextStepCard').innerHTML = `<div class="next-step-icon">→</div><div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(text)}</p></div>${action}`;
  document.querySelectorAll('[data-next-action]').forEach((button) => button.addEventListener('click', () => runNamedAction(button.dataset.nextAction)));
  document.querySelectorAll('[data-open-tab]').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.openTab)));
}

function renderRecentActivity() {
  const events = state.audit?.events || [];
  if (!events.length) {
    $('recentActivity').innerHTML = '<div class="workspace-empty-inline">No audit events available yet.</div>';
    return;
  }
  $('recentActivity').innerHTML = [...events].slice(-4).reverse().map((event) => `<div class="mini-timeline-row"><span class="timeline-dot"></span><div><strong>${escapeHtml(pretty(event.event_type))}</strong><span>${escapeHtml(formatDate(event.occurred_at))}</span></div></div>`).join('');
}

function normalizePlanActions(plan) {
  const data = plan?.plan_data || {};
  if (Array.isArray(data.actions)) return data.actions;
  const groups = ['revocations', 'asset_returns', 'reassignments'];
  return groups.flatMap((key) => Array.isArray(data[key]) ? data[key] : []);
}

function renderPlan() {
  const plan = state.local.plan;
  $('planTabDot').classList.toggle('hidden', !plan);
  if (!plan) {
    $('planEmpty').classList.remove('hidden');
    $('planContent').classList.add('hidden');
    renderApprovalState();
    return;
  }
  $('planEmpty').classList.add('hidden');
  $('planContent').classList.remove('hidden');
  $('planSummary').textContent = plan.summary || plan.plan_data?.summary || 'Generated operational plan';
  $('planRevision').textContent = plan.revision ?? '—';
  $('planIdShort').textContent = String(plan.id || '').slice(0, 8) || '—';
  $('planCreated').textContent = formatDate(plan.created_at);
  $('planStateBadge').textContent = pretty(plan.status || 'DRAFT');
  $('planStateBadge').className = `plan-state-badge ${plan.status || 'DRAFT'}`;

  const actions = normalizePlanActions(plan);
  $('actionCountLabel').textContent = `${actions.length} action${actions.length === 1 ? '' : 's'}`;
  $('planActions').innerHTML = actions.length ? actions.map((action, index) => {
    const execution = (state.local.execution?.actions || []).find((item) => item.action_type === action.action_type && item.resource_type === action.resource_type) || null;
    const actionStatus = execution?.status || 'PENDING';
    return `<article class="plan-action-card">
      <div class="action-sequence">${action.sequence || index + 1}</div>
      <div class="action-main">
        <div class="action-title-row"><strong>${escapeHtml(pretty(action.action_type))} ${escapeHtml(pretty(action.resource_type))}</strong><span class="action-state ${escapeHtml(actionStatus)}">${escapeHtml(pretty(actionStatus))}</span></div>
        <span class="action-resource">${escapeHtml(action.resource_key || 'Resource')}</span>
        <p>${escapeHtml(action.reason || 'Validated operational action.')}</p>
        <div class="evidence-chip-row">${(action.evidence_ids || []).map((id) => `<span class="evidence-chip">${escapeHtml(id)}</span>`).join('')}</div>
      </div>
      <div class="action-data"><span>Requested data</span><pre>${escapeHtml(JSON.stringify(action.requested_data || {}, null, 2))}</pre></div>
    </article>`;
  }).join('') : '<div class="workspace-empty-inline roomy">No executable actions were included in this plan.</div>';

  const data = plan.plan_data || {};
  const extras = $('offboardingExtras');
  if (state.caseItem.case_type === 'OFFBOARDING' && ((data.targeted_questions || []).length || (data.handover_topics || []).length)) {
    extras.classList.remove('hidden');
    $('offboardingExtraContent').innerHTML = `<div class="offboarding-extra-grid">
      <div><span class="section-label">TARGETED QUESTIONS</span>${(data.targeted_questions || []).map((q) => `<div class="question-item">${escapeHtml(q)}</div>`).join('') || '<div class="workspace-empty-inline">No targeted questions.</div>'}</div>
      <div><span class="section-label">HANDOVER TOPICS</span>${(data.handover_topics || []).map((q) => `<div class="topic-item">${escapeHtml(q)}</div>`).join('') || '<div class="workspace-empty-inline">No handover topics.</div>'}</div>
    </div>`;
  } else {
    extras.classList.add('hidden');
  }
  renderApprovalState();
}

function renderApprovalState() {
  const approval = state.local.approval;
  const box = $('approvalStateBox');
  if (!state.local.plan) {
    box.innerHTML = '<div class="approval-empty"><span class="approval-icon">○</span><div><strong>No plan yet</strong><p>Generate a plan before requesting human approval.</p></div></div>';
    return;
  }
  if (!approval) {
    box.innerHTML = '<div class="approval-empty"><span class="approval-icon">○</span><div><strong>Not submitted</strong><p>The current draft has not entered the approval checkpoint.</p></div></div>';
    return;
  }
  const approver = person(approval.assigned_to);
  box.innerHTML = `<div class="approval-state-row"><span class="approval-icon ${approval.status}">${approval.status === 'APPROVED' ? '✓' : approval.status === 'REJECTED' ? '×' : '…'}</span><div><strong>${escapeHtml(pretty(approval.status))}</strong><p>Assigned to ${escapeHtml(approver.name)}</p>${approval.comment ? `<span class="approval-comment">${escapeHtml(approval.comment)}</span>` : ''}</div></div>${approval.status === 'PENDING' ? '<button class="secondary-button approval-review-button" id="reviewApprovalButton">Review Decision</button>' : ''}`;
  $('reviewApprovalButton')?.addEventListener('click', () => openModal('decisionModal'));
}

function renderEvidence() {
  const evidence = state.evidence?.evidence || [];
  $('evidenceCountBadge').textContent = evidence.length;
  $('evidenceQuery').textContent = state.evidence?.search_query ? `Search query: ${state.evidence.search_query}` : 'Retrieved policy context for this case.';
  $('evidenceList').innerHTML = evidence.length ? evidence.map((item, index) => `<article class="evidence-card">
    <div class="evidence-card-top"><div><span class="evidence-number">${index + 1}</span><strong>${escapeHtml(item.policy_code)} · V${escapeHtml(item.version_number)}</strong></div><span class="evidence-score">${Math.round(Number(item.score || 0) * 100)}% match</span></div>
    <p>${escapeHtml(item.text)}</p>
    <div class="evidence-footer"><span>Evidence ID</span><code>${escapeHtml(item.evidence_id)}</code></div>
  </article>`).join('') : '<div class="workspace-empty roomy"><div class="workspace-empty-icon">EV</div><strong>No policy evidence available</strong><span>Evidence is available while the case is in a planning-compatible state.</span></div>';
}

function renderExecution() {
  const execution = state.local.execution;
  const actions = execution?.actions || [];
  const verified = actions.filter((item) => item.status === 'VERIFIED').length;
  const attention = actions.filter((item) => ['FAILED', 'HUMAN_REVIEW'].includes(item.status)).length;
  $('execTotal').textContent = actions.length || normalizePlanActions(state.local.plan).length;
  $('execVerified').textContent = verified;
  $('execAttention').textContent = attention;
  $('executionCountBadge').textContent = actions.length;
  $('executionCaseState').textContent = pretty(execution?.case_status || state.caseItem.status);
  $('executionCaseState').className = `case-status ${execution?.case_status || state.caseItem.status}`;

  if (!actions.length) {
    const planned = normalizePlanActions(state.local.plan);
    if (!planned.length) {
      $('executionList').innerHTML = '<div class="workspace-empty roomy"><div class="workspace-empty-icon">EX</div><strong>No execution data yet</strong><span>Generate and approve a plan before execution.</span></div>';
      return;
    }
    $('executionList').innerHTML = planned.map((action, index) => `<div class="execution-row"><span class="execution-index">${index + 1}</span><div class="execution-copy"><strong>${escapeHtml(pretty(action.action_type))} ${escapeHtml(pretty(action.resource_type))}</strong><span>${escapeHtml(action.resource_key || 'Resource')}</span></div><span class="action-state PENDING">Pending</span><span class="execution-attempts">0 attempts</span></div>`).join('');
    return;
  }

  $('executionList').innerHTML = actions.map((action, index) => `<div class="execution-row ${['FAILED','HUMAN_REVIEW'].includes(action.status) ? 'needs-attention' : ''}">
    <span class="execution-index">${index + 1}</span>
    <div class="execution-copy"><strong>${escapeHtml(pretty(action.action_type))} ${escapeHtml(pretty(action.resource_type))}</strong><span>${action.error_message ? escapeHtml(action.error_message) : action.verification_data ? 'Independent verification recorded' : 'Automation result recorded'}</span></div>
    <span class="action-state ${escapeHtml(action.status)}">${escapeHtml(pretty(action.status))}</span>
    <span class="execution-attempts">${Number(action.attempt_count || 0)} attempt${Number(action.attempt_count || 0) === 1 ? '' : 's'}</span>
  </div>`).join('');
}

function renderAudit() {
  const events = state.audit?.events || [];
  $('auditCountBadge').textContent = events.length;
  $('auditTimeline').innerHTML = events.length ? [...events].reverse().map((event) => `<article class="audit-event">
    <div class="audit-rail"><span></span></div>
    <div class="audit-event-body"><div class="audit-event-head"><strong>${escapeHtml(pretty(event.event_type))}</strong><time>${escapeHtml(formatDate(event.occurred_at))}</time></div><div class="audit-event-meta"><span>${escapeHtml(pretty(event.actor_type))}</span><span>${escapeHtml(pretty(event.entity_type))}</span></div>${event.evidence_data ? `<details><summary>Evidence</summary><pre>${escapeHtml(JSON.stringify(event.evidence_data, null, 2))}</pre></details>` : ''}</div>
  </article>`).join('') : '<div class="workspace-empty roomy"><div class="workspace-empty-icon">AU</div><strong>No audit events found</strong><span>The audit trail will populate as this case progresses.</span></div>';

  const coverage = state.coverage;
  if (!coverage) {
    $('auditCoverage').innerHTML = '<div class="workspace-empty-inline roomy">Coverage could not be loaded.</div>';
    return;
  }
  const groups = Object.entries(coverage.present_groups || {});
  $('auditCoverage').innerHTML = `<div class="coverage-status ${coverage.complete_for_current_case_state ? 'complete' : 'partial'}"><span>${coverage.complete_for_current_case_state ? '✓' : '!'}</span><div><strong>${coverage.complete_for_current_case_state ? 'Coverage complete' : 'Coverage in progress'}</strong><p>${coverage.total_events} audit event${coverage.total_events === 1 ? '' : 's'} recorded</p></div></div><div class="coverage-groups">${groups.map(([name, present]) => `<div class="coverage-row"><span>${escapeHtml(pretty(name))}</span><strong class="${present ? 'yes' : 'no'}">${present ? '✓' : '—'}</strong></div>`).join('')}</div>${(coverage.missing_groups || []).length ? `<div class="missing-coverage"><span>Expected later</span>${coverage.missing_groups.map((name) => `<strong>${escapeHtml(pretty(name))}</strong>`).join('')}</div>` : ''}`;
}

function renderButtons() {
  const c = state.caseItem;
  const plan = state.local.plan;
  const approval = state.local.approval;
  const generate = $('generatePlanButton');
  const submit = $('submitPlanButton');
  const execute = $('executePlanButton');
  const retry = $('retryPlanButton');

  generate.classList.toggle('hidden', c.status !== 'PLANNING' || Boolean(plan));
  submit.classList.toggle('hidden', c.status !== 'PLANNING' || !plan || Boolean(approval));
  execute.classList.toggle('hidden', c.status !== 'APPROVED' || !plan);
  retry.classList.toggle('hidden', c.status !== 'FAILED' || !plan);
}

function renderAll() {
  if (!state.caseItem) return;
  renderHealth();
  renderHeader();
  renderWorkflow();
  renderOverview();
  renderPlan();
  renderEvidence();
  renderExecution();
  renderAudit();
  renderButtons();
}

async function loadEvidence() {
  try {
    state.evidence = await api(`/cases/${state.caseId}/policy-context`);
    state.local.evidence = state.evidence;
    saveLocalState();
  } catch {
    state.evidence = state.local.evidence || null;
  }
  renderEvidence();
}

async function loadAudit() {
  const [timelineResult, coverageResult] = await Promise.allSettled([
    api(`/audit/cases/${state.caseId}/timeline`),
    api(`/audit/cases/${state.caseId}/coverage`),
  ]);
  state.audit = timelineResult.status === 'fulfilled' ? timelineResult.value : null;
  state.coverage = coverageResult.status === 'fulfilled' ? coverageResult.value : null;
  renderAudit();
  renderRecentActivity();
}

async function refreshCase() {
  state.caseItem = await api(`/cases/${state.caseId}`);
  ensureTrackedCase();
}

async function refreshWorkspace(silent = false) {
  if (!state.caseId) {
    showWorkspaceError('No case ID was supplied. Open a case from the Cases page.');
    return;
  }
  if (!silent) setLoading(true);
  try {
    const [healthResult] = await Promise.allSettled([api('/health')]);
    state.health = healthResult.status === 'fulfilled' ? healthResult.value : null;
    await refreshCase();
    await Promise.all([loadEvidence(), loadAudit()]);
    renderAll();
    $('workspaceError').classList.add('hidden');
    setLoading(false);
  } catch (error) {
    showWorkspaceError(error.message || 'The case could not be loaded.');
  }
}

async function generatePlan() {
  const button = $('generatePlanButton');
  const emptyButton = $('emptyGeneratePlanButton');
  [button, emptyButton].forEach((item) => { item.disabled = true; item.textContent = 'Generating…'; });
  try {
    const path = state.caseItem.case_type === 'OFFBOARDING'
      ? `/cases/${state.caseId}/offboarding/plan`
      : `/cases/${state.caseId}/plan`;
    const plan = await api(path, { method: 'POST', body: '{}' });
    state.local.plan = plan;
    state.local.approval = null;
    state.local.execution = null;
    saveLocalState();
    await refreshCase();
    await Promise.all([loadEvidence(), loadAudit()]);
    renderAll();
    setActiveTab('plan');
    showToast('Policy-grounded plan generated and validated.', 'success');
  } catch (error) {
    showToast(error.message || 'Plan generation failed.', 'error');
  } finally {
    button.disabled = false; button.textContent = state.caseItem?.case_type === 'OFFBOARDING' ? 'Generate Offboarding Plan' : 'Generate Plan';
    emptyButton.disabled = false; emptyButton.textContent = 'Generate Plan';
  }
}

async function submitApproval(event) {
  event.preventDefault();
  if (!state.local.plan?.id) return showToast('Generate a plan first.', 'error');
  const button = $('approvalSubmitButton');
  button.disabled = true; button.textContent = 'Submitting…';
  try {
    const approval = await api(`/plans/${state.local.plan.id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ assigned_to: $('assignedApprover').value }),
    });
    state.local.approval = approval;
    if (state.local.plan) state.local.plan.status = 'PENDING_APPROVAL';
    saveLocalState();
    closeModal('approvalModal');
    await refreshCase();
    await loadAudit();
    renderAll();
    showToast('Plan submitted for human approval.', 'success');
  } catch (error) {
    showToast(error.message || 'Could not submit the plan.', 'error');
  } finally {
    button.disabled = false; button.textContent = 'Submit Plan';
  }
}

async function decideApproval(event) {
  event.preventDefault();
  const approval = state.local.approval;
  if (!approval?.id) return showToast('No pending approval is loaded.', 'error');
  const decision = $('approvalDecision').value;
  const comment = $('approvalComment').value.trim();
  if (decision === 'REJECTED' && !comment) return showToast('A rejection comment is required.', 'error');
  const button = $('decisionSubmitButton');
  button.disabled = true; button.textContent = 'Saving…';
  try {
    const updated = await api(`/approvals/${approval.id}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: approval.assigned_to, decision, comment: comment || null }),
    });
    state.local.approval = updated;
    if (state.local.plan) state.local.plan.status = decision === 'APPROVED' ? 'APPROVED' : 'REJECTED';
    saveLocalState();
    closeModal('decisionModal');
    await refreshCase();
    await loadAudit();
    renderAll();
    showToast(decision === 'APPROVED' ? 'Plan approved.' : 'Plan rejected and routed to human review.', decision === 'APPROVED' ? 'success' : 'error');
  } catch (error) {
    showToast(error.message || 'Could not save the approval decision.', 'error');
  } finally {
    button.disabled = false; button.textContent = 'Save Decision';
  }
}

async function executePlan(retry = false) {
  if (!state.local.plan?.id) return showToast('No plan is loaded for this case.', 'error');
  const button = retry ? $('retryPlanButton') : $('executePlanButton');
  const original = button.textContent;
  button.disabled = true; button.textContent = retry ? 'Retrying…' : 'Executing…';
  try {
    const execution = await api(`/plans/${state.local.plan.id}/${retry ? 'retry' : 'execute'}`, { method: 'POST', body: '{}' });
    state.local.execution = execution;
    saveLocalState();
    await refreshCase();
    await loadAudit();
    renderAll();
    setActiveTab('execution');
    showToast(execution.case_status === 'COMPLETED' ? 'Plan executed and all actions verified.' : 'Execution state updated.', 'success');
  } catch (error) {
    try { await refreshCase(); } catch (_) {}
    await loadAudit();
    renderAll();
    setActiveTab('execution');
    showToast(error.message || 'Execution failed.', 'error');
  } finally {
    button.disabled = false; button.textContent = original;
  }
}

function runNamedAction(action) {
  if (action === 'generate') return generatePlan();
  if (action === 'submit') return openModal('approvalModal');
  if (action === 'decision') return openModal('decisionModal');
  if (action === 'execute') return executePlan(false);
  if (action === 'retry') return executePlan(true);
}

function setActiveTab(name) {
  state.activeTab = name;
  document.querySelectorAll('.workspace-tab').forEach((button) => button.classList.toggle('active', button.dataset.tab === name));
  document.querySelectorAll('.workspace-tab-panel').forEach((panel) => panel.classList.toggle('active', panel.id === `tab-${name}`));
}

$('refreshButton').addEventListener('click', () => refreshWorkspace());
$('copyCaseIdButton').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(state.caseId); showToast('Case ID copied.', 'success'); }
  catch { showToast('Could not access the clipboard.', 'error'); }
});
$('generatePlanButton').addEventListener('click', generatePlan);
$('emptyGeneratePlanButton').addEventListener('click', generatePlan);
$('submitPlanButton').addEventListener('click', () => openModal('approvalModal'));
$('executePlanButton').addEventListener('click', () => executePlan(false));
$('retryPlanButton').addEventListener('click', () => executePlan(true));
$('approvalForm').addEventListener('submit', submitApproval);
$('decisionForm').addEventListener('submit', decideApproval);
$('refreshEvidenceButton').addEventListener('click', async () => { await loadEvidence(); showToast('Policy evidence refreshed.', 'success'); });
$('refreshAuditButton').addEventListener('click', async () => { await loadAudit(); showToast('Audit data refreshed.', 'success'); });

document.querySelectorAll('.workspace-tab').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.tab)));
document.querySelectorAll('[data-open-tab]').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.openTab)));
document.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', () => closeModal(button.dataset.closeModal)));
document.querySelectorAll('.modal-backdrop').forEach((modal) => modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(modal.id); }));
document.querySelectorAll('[data-coming-soon]').forEach((button) => button.addEventListener('click', () => showToast(`${button.dataset.comingSoon} will be built in a later page.`)));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach((modal) => closeModal(modal.id));
});

loadLocalState();
refreshWorkspace();
setInterval(() => refreshWorkspace(true), 45000);
