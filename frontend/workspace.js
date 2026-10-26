/* Case workspace: plan, "why" per step, manager revision, execution with a
   stopwatch, verification source, timeline and the evidence report. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, clock, actingAs, PEOPLE } = LO;
  const caseId = new URLSearchParams(location.search).get('case');
  const page = LO.shell({ active: 'cases.html', title: 'Case workspace', subtitle: caseId ? `Case ${caseId}` : 'No case selected' });
  if (!caseId) { page.innerHTML = '<div class="empty"><b>No case selected</b>Open one from <a href="cases.html">Cases</a> or the dashboard.</div>'; return; }

  page.innerHTML = `
    <section class="card" id="header"></section>
    <section class="split">
      <div class="stack">
        <div class="card" id="plan"></div>
        <div class="card hidden" id="editor"></div>
      </div>
      <div class="stack">
        <div class="card" id="actions"></div>
        <div class="card"><div class="card-head"><h2>Audit timeline</h2></div><div id="timeline" class="timeline"></div></div>
      </div>
    </section>`;

  const state = { data: null, explanations: {}, open: new Set(), busy: false, editing: false, seen: {} };
  const AGENT_OPTIONS = {
    AI_AGENT: ['REASSIGN', 'REVOKE'],
    AGENT_CREDENTIAL: ['REASSIGN', 'DOWNSCOPE', 'REVOKE'],
  };

  const latestPlan = () => state.data?.plans.at(-1);
  const executedPlan = () => [...(state.data?.plans || [])].reverse()
    .find((p) => p.actions.some((a) => a.status !== 'SKIPPED' && a.status !== 'PENDING')) || latestPlan();

  // ---------- Header with stopwatch ----------
  function renderHeader() {
    const c = state.data.case;
    const plan = executedPlan();
    const verified = (plan?.actions || []).map((a) => a.verified_at).filter(Boolean).map((t) => new Date(t).getTime());
    const done = c.status === 'COMPLETED' && verified.length;
    const end = done ? Math.max(...verified) : Date.now();
    const elapsed = end - new Date(c.created_at).getTime();
    const actions = (plan?.actions || []).filter((a) => a.status !== 'SKIPPED');
    const verifiedCount = actions.filter((a) => a.status === 'VERIFIED').length;
    const stage = c.status === 'COMPLETED' ? 4 : ['EXECUTING', 'RETRYING', 'FAILED'].includes(c.status) ? 3
      : plan?.status === 'APPROVED' ? 2 : plan ? 1 : 0;
    const stages = ['Readiness', 'AI plan', 'Approved', 'Executing', 'Verified'];
    document.getElementById('header').innerHTML = `
      <div class="card-head" style="margin-bottom:18px">
        <div style="flex:1;min-width:0">
          <h3 style="margin-bottom:6px">${esc(human(c.case_type))}${c.case_type === 'ACCESS_REQUEST' && c.case_facts.tier ? ' · tier ' + esc(c.case_facts.tier) : ''}</h3>
          <h1 style="font-size:24px">${esc(c.subject_name)}</h1>
          <div class="faint">opened by ${esc(c.created_by_name || '—')} ${timeAgo(c.created_at)}
            ${c.case_facts.last_working_day ? ` · last working day ${esc(c.case_facts.last_working_day)}` : ''}
            ${c.origin ? ` · ${esc(human(c.origin))}` : ''}</div>
        </div>
        <div style="text-align:right">
          <div class="faint">${done ? 'All access closed in' : 'Since case opened'}</div>
          <div class="stopwatch ${done ? 'done' : 'running'}">${clock(elapsed)}</div>
        </div>
      </div>
      <div class="stepper">${stages.map((label, i) => `<div class="${i < stage ? 'done' : i === stage ? 'now' : ''}"><i></i><span>${label}</span></div>`).join('')}</div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:14px">${badge(c.status)}
        ${actions.length ? `<div class="bar" style="flex:1"><i style="width:${(verifiedCount / actions.length) * 100}%;background:var(--ok);transition:width .6s var(--ease)"></i></div>
        <span class="faint num">${verifiedCount}/${actions.length} verified</span>` : '<span class="spacer"></span>'}</div>
      ${c.failure_reason ? `<div class="item highlight" style="margin-top:12px">${esc(c.failure_reason)}</div>` : ''}`;
  }

  // ---------- Plan and why panel ----------
  function renderPlan() {
    const plan = executedPlan();
    const el = document.getElementById('plan');
    if (!plan) {
      el.innerHTML = '<div class="card-head"><h2>Plan</h2></div><div class="empty">No plan yet.</div>';
      return;
    }
    const revised = plan.parent_plan_id;
    el.innerHTML = `
      <div class="card-head"><h2>Plan r${plan.revision}</h2>${badge(plan.status)}
        ${revised ? '<span class="badge pending">manager revision</span>' : '<span class="badge agent">AI plan</span>'}
        <span class="spacer"></span><span class="faint">${plan.actions.length} steps</span></div>
      <p class="muted" style="margin-top:0">${esc(plan.summary || '')}</p>
      ${plan.correction_summary ? `<div class="item"><b>Manager correction:</b> ${esc(plan.correction_summary)}</div>` : ''}
      <div class="stack" style="margin-top:12px">${plan.actions.map((a) => stepHtml(plan, a)).join('')}</div>
      ${plan.targeted_questions.length ? `<h3 style="margin-top:16px">Handover questions</h3>
        <ol class="muted">${plan.targeted_questions.map((q) => `<li>${esc(q)}</li>`).join('')}</ol>` : ''}`;
    el.querySelectorAll('[data-why]').forEach((b) => b.addEventListener('click', () => toggleWhy(plan.id, Number(b.dataset.why))));
  }

  function stepHtml(plan, a) {
    const key = `${plan.id}:${a.sequence}`;
    const open = state.open.has(key);
    const why = open ? whyHtml(plan.id, a.sequence) : '';
    const tone = a.status === 'VERIFIED' ? 'done' : ['DISPATCHED', 'EXECUTING', 'SUCCEEDED', 'RETRYING'].includes(a.status) ? 'running' : '';
    const fresh = a.status === 'VERIFIED' && state.seen[a.id] && state.seen[a.id] !== 'VERIFIED';
    state.seen[a.id] = a.status;
    return `<div class="item ${fresh ? 'flash' : ''}">
      <div class="step ${tone}">
        <div class="num">${a.sequence}</div>
        <div><div class="what">${esc(human(a.action_type))} · ${esc(human(a.resource_type))}</div>
          <div class="key">${esc(a.resource_key)}</div>
          <div class="faint">${esc(a.reason || '')}</div>
          ${a.verified_by ? `<div class="chips" style="margin-top:8px">
            ${a.verified_by === 'github' ? '<span class="badge ok">verified by GitHub API</span>' : '<span class="badge ok">verified in company records</span>'}
            ${a.n8n_execution_id ? `<span class="chip">n8n run ${esc(a.n8n_execution_id)}</span>` : ''}
            ${a.verified_at ? `<span class="chip">${new Date(a.verified_at).toLocaleTimeString()}</span>` : ''}</div>` : ''}
          ${a.error ? `<div class="faint" style="color:var(--bad)">${esc(a.error)}</div>` : ''}
        </div>
        <div class="btn-row">${badge(a.status)}<button class="btn small" data-why="${a.sequence}">${open ? 'Hide why' : 'Why?'}</button></div>
      </div>${why}</div>`;
  }

  async function toggleWhy(planId, sequence) {
    const key = `${planId}:${sequence}`;
    if (state.open.has(key)) { state.open.delete(key); renderPlan(); return; }
    state.open.add(key);
    if (!state.explanations[planId]) {
      try { state.explanations[planId] = await api(`/plans/${planId}/explanation`); }
      catch (error) { toast(error.message, 'error'); }
    }
    renderPlan();
  }

  function whyHtml(planId, sequence) {
    const exp = state.explanations[planId];
    const step = exp?.steps.find((s) => s.sequence === sequence);
    if (!step) return '<div class="why faint">Loading…</div>';
    const validation = exp.validation || {};
    const policies = step.policy_evidence.map((p) => `
      <div><div class="chips"><span class="chip">${esc(p.evidence_id)}</span>${badge(p.status || 'ARCHIVED', `${p.policy_code} V${p.version_number} ${human(p.status || '')}`)}</div>
        ${p.clauses.map((c) => `<div class="clause"><span class="n">${c.number}.</span>${esc(c.text)}</div>`).join('')}</div>`).join('');
    const lessons = step.lessons.map((l) => `<div class="ai-note"><b>Approved lesson</b><br>${esc(l.recommended_action || l.learning_id)} ${badge(l.status)}</div>`).join('');
    return `<div class="why">
      <div class="chips">
        ${badge('VERIFIED', `validation ${validation.deterministic_validation || 'passed'}`)}
        ${validation.repair_used === true ? badge('MEDIUM', 'needed one repair') : validation.repair_used === false ? badge('ACTIVE', 'valid first time') : ''}
        ${badge(exp.origin === 'AI_PLANNER' ? 'PENDING' : 'ACTIVE', human(exp.origin))}
      </div>
      <div><h3>Policy evidence</h3>${policies || '<div class="faint">No policy evidence cited.</div>'}</div>
      ${lessons ? `<div><h3>Lessons used</h3>${lessons}</div>` : ''}
      <div class="faint">Reason: ${esc(step.reason || '—')}</div>
    </div>`;
  }

  // ---------- Revision editor (manager correction) ----------
  function renderEditor() {
    const el = document.getElementById('editor');
    const plan = latestPlan();
    el.classList.toggle('hidden', !state.editing || !plan);
    if (!state.editing || !plan) { el.dataset.plan = ''; return; }
    // Polling re-renders the page every few seconds; build the editor once
    // per plan so the manager's typing and choices are not wiped.
    if (el.dataset.plan === plan.id) return;
    el.dataset.plan = plan.id;
    el.innerHTML = `
      <div class="card-head"><h2>Revise as manager</h2><span class="spacer"></span><span class="faint">Acting as ${esc(actingAs().name)}</span></div>
      <div class="stack">${plan.actions.map((a) => {
        const options = AGENT_OPTIONS[a.resource_type];
        return `<div class="step"><div class="num">${a.sequence}</div>
          <div><div class="key">${esc(a.resource_key)}</div><div class="faint">${esc(human(a.resource_type))}</div></div>
          <div>${options ? `<select data-seq="${a.sequence}">${options.map((o) => `<option ${o === a.action_type ? 'selected' : ''}>${o}</option>`).join('')}</select>` : `<span class="faint">${esc(human(a.action_type))}</span>`}</div></div>`;
      }).join('')}</div>
      <label class="faint" style="display:block;margin-top:12px">What you changed and why (this becomes the lesson)</label>
      <textarea id="correction" placeholder="e.g. Keep Aurora Release Bot with me, but read-only: it should not keep write access after its sponsor leaves."></textarea>
      <div class="btn-row" style="margin-top:10px">
        <button class="btn primary" id="save-revision">Save revision and send for approval</button>
        <button class="btn" id="cancel-revision">Cancel</button></div>`;
    el.querySelector('#cancel-revision').addEventListener('click', () => { state.editing = false; render(); });
    el.querySelector('#save-revision').addEventListener('click', saveRevision);
  }

  async function saveRevision() {
    const plan = latestPlan();
    const facts = state.data.case.case_facts;
    const successor = facts.successor_person_id || facts.manager_id;
    const choice = Object.fromEntries([...document.querySelectorAll('#editor select[data-seq]')].map((s) => [s.dataset.seq, s.value]));
    const actions = plan.actions.map((a) => {
      const type = choice[a.sequence] || a.action_type;
      let params = { ...a.parameters };
      if (AGENT_OPTIONS[a.resource_type]) {
        params = type === 'REVOKE' ? {} : { successor_person_id: successor };
        if (type === 'DOWNSCOPE') params.permission = 'read';
      }
      return {
        sequence: a.sequence, action_type: type, resource_type: a.resource_type, resource_key: a.resource_key,
        requested_data: params, evidence_ids: a.evidence_ids,
        reason: type === a.action_type ? a.reason : `${a.reason || ''} Manager correction: ${human(type)}.`.trim().slice(0, 500),
      };
    });
    const correction = document.getElementById('correction').value.trim();
    if (correction.length < 10) { toast('Describe the correction (at least 10 characters).', 'error'); return; }
    await act(async () => {
      await api(`/plans/${plan.id}/revise`, { method: 'POST', body: {
        plan_data: { summary: plan.summary || 'Manager revision', actions, warnings: [] },
        correction_summary: correction,
      } });
      state.editing = false;
      toast('Revision saved and sent to the manager for approval.');
    });
  }

  // ---------- Context actions ----------
  async function act(fn) {
    if (state.busy) return;
    state.busy = true; renderActions();
    try { await fn(); await load(); } catch (error) { toast(error.message, 'error'); }
    finally { state.busy = false; renderActions(); }
  }

  function renderActions() {
    const el = document.getElementById('actions');
    if (!state.data) return;
    const c = state.data.case;
    const plan = latestPlan();
    const pending = plan?.approvals.find((a) => a.status === 'PENDING');
    const me = actingAs();
    const buttons = [];
    if (['NEW', 'HUMAN_REVIEW'].includes(c.status) && !plan) buttons.push(['triage', 'Check readiness', 'primary']);
    if (c.status === 'PLANNING' && !plan && c.case_type !== 'ACCESS_REQUEST') buttons.push(['generate', 'Generate AI plan', 'primary']);
    if (plan?.status === 'DRAFT') { buttons.push(['submit', 'Send to manager for approval', 'primary']); buttons.push(['edit', 'Revise as manager', '']); }
    if (plan?.status === 'PENDING_APPROVAL' && !plan.parent_plan_id) buttons.push(['edit', 'Revise as manager', '']);
    if (pending && pending.assigned_to === me.id) { buttons.push(['approve', 'Approve plan', 'good']); buttons.push(['reject', 'Reject', 'danger']); }
    if (plan?.status === 'APPROVED' && ['APPROVED', 'FAILED'].includes(c.status)) buttons.push([c.status === 'FAILED' ? 'retry' : 'execute', c.status === 'FAILED' ? 'Retry failed actions' : 'Execute approved plan', 'primary']);
    if (c.status === 'COMPLETED' && state.data.plans.some((p) => p.parent_plan_id) && c.case_type === 'OFFBOARDING') buttons.push(['lesson', 'Turn the correction into a lesson', '']);

    el.innerHTML = `
      <div class="card-head"><h2>Next step</h2><span class="spacer"></span>${state.busy ? '<span class="faint">working…</span>' : ''}</div>
      ${pending ? `<div class="item">Waiting for <b>${esc(pending.assigned_to_name)}</b> to approve r${plan.revision}.</div>` : ''}
      <div class="btn-row" style="margin-top:10px">${buttons.map(([id, label, tone]) =>
        `<button class="btn ${tone}" data-act="${id}" ${state.busy ? 'disabled' : ''}>${esc(label)}</button>`).join('') || '<span class="faint">Nothing to do right now.</span>'}</div>
      ${c.status === 'COMPLETED' ? `<div class="btn-row" style="margin-top:12px">
        <a class="btn" href="/api/cases/${c.id}/evidence" target="_blank" rel="noopener">ISO 27001 evidence report</a></div>` : ''}`;
    el.querySelectorAll('[data-act]').forEach((b) => b.addEventListener('click', () => handle(b.dataset.act)));
  }

  function handle(action) {
    const c = state.data.case;
    const plan = latestPlan();
    const pending = plan?.approvals.find((a) => a.status === 'PENDING');
    const me = actingAs();
    const run = {
      triage: () => act(() => api(`/cases/${c.id}/triage`, { method: 'POST' })),
      generate: () => act(async () => {
        toast('The AI is drafting the plan from company policy…');
        await api(c.case_type === 'OFFBOARDING' ? `/cases/${c.id}/offboarding/plan` : `/cases/${c.id}/plan`, { method: 'POST' });
      }),
      submit: () => act(() => api(`/plans/${plan.id}/submit`, { method: 'POST', body: { assigned_to: c.case_facts.manager_id || PEOPLE.nabil.id } })),
      edit: () => { state.editing = true; renderEditor(); document.getElementById('editor').scrollIntoView({ behavior: 'smooth' }); },
      approve: () => act(() => api(`/approvals/${pending.id}/decision`, { method: 'POST', body: { decided_by: me.id, decision: 'APPROVED', comment: 'Approved in workspace.' } })),
      reject: () => {
        const comment = prompt('Why are you rejecting this plan?');
        if (comment) act(() => api(`/approvals/${pending.id}/decision`, { method: 'POST', body: { decided_by: me.id, decision: 'REJECTED', comment } }));
      },
      execute: () => act(async () => {
        toast('Executing: n8n runs each approved action, the backend verifies it.');
        await api(`/plans/${plan.id}/execute`, { method: 'POST' });
        toast('All actions verified.');
      }),
      retry: () => act(() => api(`/plans/${plan.id}/retry`, { method: 'POST' })),
      lesson: () => act(async () => {
        await api(`/cases/${c.id}/learning/candidate`, { method: 'POST', body: { assigned_to: PEOPLE.tahmid.id } });
        toast('Lesson drafted; Tahmid approves it on the Approvals page.');
      }),
    };
    run[action]?.();
  }

  // ---------- Timeline ----------
  async function loadTimeline() {
    try {
      const t = await api(`/audit/cases/${caseId}/timeline`);
      document.getElementById('timeline').innerHTML = t.events.slice(-14).reverse().map((e) => `
        <div class="tl ${e.actor_type === 'AGENT' || e.actor_type === 'AI' ? 'ai' : e.actor_type === 'HUMAN' || e.actor_type === 'USER' ? 'human' : ''}">
          <div class="tl-what">${esc(human(e.event_type))}</div>
          <div class="faint"><span class="mono">${esc(e.actor_type)}</span> · ${new Date(e.occurred_at).toLocaleTimeString()}</div></div>`).join('') || '<div class="empty"><b>No events yet</b>Every step lands here as it happens.</div>';
    } catch { /* timeline is optional */ }
  }

  function render() { renderHeader(); renderPlan(); renderEditor(); renderActions(); }

  async function load() {
    state.data = await api(`/cases/${caseId}/plans`);
    render();
  }

  document.addEventListener('persona', () => state.data && renderActions());
  poll(load, 2500);
  poll(loadTimeline, 5000);
  setInterval(() => state.data && renderHeader(), 1000);
})();
