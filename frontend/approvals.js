/* Approvals queue for the person you are acting as: plans, manager
   revisions, agent access requests (with tier), remediations and lessons. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, actingAs } = LO;
  const page = LO.shell({
    active: 'approvals.html',
    title: 'Approvals',
    subtitle: 'Low-risk agent requests never reach this queue: the rules approve them, with an expiry',
  });
  page.innerHTML = `
    <section class="card">
      <div class="card-head"><h2 id="queue-title">Waiting for you</h2><span class="spacer"></span>
        <select id="scope"><option value="mine">Assigned to me</option><option value="all">All pending</option><option value="decided">Recently decided</option></select></div>
      <div id="queue" class="stack"></div>
    </section>`;

  const state = { busy: new Set() };

  function kindOf(a) {
    if (a.target_type === 'LEARNING') return ['Lesson to approve', 'agent'];
    if (a.origin === 'MCP_ACCESS_REQUEST') return ['Agent access request', 'agent'];
    if (a.origin === 'POLICY_GUARDIAN_REMEDIATION') return ['Policy remediation', 'bad'];
    if (a.correction_summary) return ['Manager revision', 'pending'];
    return [`${human(a.case_type || 'plan')} plan`, 'pending'];
  }

  function card(a) {
    const [kind, tone] = kindOf(a);
    const r = a.request || {};
    const lesson = a.lesson || {};
    const decided = a.status !== 'PENDING';
    const mine = a.assigned_to === actingAs().id;
    return `<div class="item ${a.tier === 'HIGH' || a.origin === 'POLICY_GUARDIAN_REMEDIATION' ? 'highlight' : ''}">
      <div class="card-head" style="margin-bottom:8px">
        <span class="badge ${tone}">${esc(kind)}</span>
        ${a.tier ? badge(a.tier, `${a.tier} risk`) : ''}
        <b>${esc(a.subject_name || '')}</b>
        <span class="spacer"></span><span class="faint">for ${esc(a.assigned_to_name || '—')} · ${timeAgo(a.requested_at)}</span>
      </div>
      ${a.origin === 'MCP_ACCESS_REQUEST' ? `
        <dl class="kv">
          <dt>Agent</dt><dd class="mono">${esc(a.agent_key || '')}</dd>
          <dt>Asks for</dt><dd><b>${esc(r.permission)}</b> on <b>${esc(r.resource)}</b> for ${esc(r.duration_minutes)} min</dd>
          <dt>Why</dt><dd>${esc(r.reason || '')}</dd>
          <dt>Rules</dt><dd>${(a.tier_reasons || []).map((t) => `<span class="chip">${esc(t)}</span>`).join(' ')}</dd>
        </dl>
        ${a.approver_note ? `<div class="ai-note" style="margin-top:8px"><b>AI summary for the approver</b><br>${esc(a.approver_note)}</div>` : ''}` : ''}
      ${a.target_type === 'LEARNING' ? `
        <dl class="kv">
          <dt>Situation</dt><dd>${esc(lesson.situation || '')}</dd>
          <dt>Lesson</dt><dd><b>${esc(lesson.recommended_action || '')}</b></dd>
          <dt>Rationale</dt><dd>${esc(lesson.rationale || '')}</dd>
        </dl>` : ''}
      ${a.plan_summary && a.origin !== 'MCP_ACCESS_REQUEST' ? `<p style="margin:6px 0">${esc(a.plan_summary)}</p>` : ''}
      ${a.correction_summary ? `<div class="item"><b>Correction:</b> ${esc(a.correction_summary)}</div>` : ''}
      <div class="btn-row" style="margin-top:10px">
        ${a.case_id ? `<a class="btn small" href="workspace.html?case=${a.case_id}">Open case</a>` : ''}
        ${a.lesson_case_id ? `<a class="btn small" href="workspace.html?case=${a.lesson_case_id}">Source case</a>` : ''}
        <span class="spacer"></span>
        ${decided ? badge(a.status) : mine ? `
          <button class="btn danger" data-reject="${a.id}" ${state.busy.has(a.id) ? 'disabled' : ''}>Reject</button>
          <button class="btn good" data-approve="${a.id}" ${state.busy.has(a.id) ? 'disabled' : ''}>${state.busy.has(a.id) ? 'Working…' : 'Approve'}</button>`
          : `<span class="faint">Only ${esc(a.assigned_to_name)} can decide</span>`}
      </div></div>`;
  }

  async function decide(id, decision, comment) {
    const a = state.rows.find((row) => row.id === id);
    state.busy.add(id); render();
    try {
      const me = actingAs().id;
      if (a.target_type === 'LEARNING') {
        await api(`/learning-approvals/${id}/decision`, { method: 'POST', body: { decided_by: me, decision, comment } });
        if (decision === 'APPROVED') await api(`/learning/${a.target_id}/index`, { method: 'POST' });
        toast(decision === 'APPROVED' ? 'Lesson approved and added to memory.' : 'Lesson rejected.');
      } else {
        await api(`/approvals/${id}/decision`, { method: 'POST', body: { decided_by: me, decision, comment } });
        toast(decision === 'APPROVED'
          ? (a.case_type === 'ACCESS_REQUEST' ? 'Approved: executing and verifying now.' : 'Approved.')
          : 'Rejected.');
      }
    } catch (error) { toast(error.message, 'error'); }
    finally { state.busy.delete(id); await load(); }
  }

  function render() {
    const rows = state.rows || [];
    document.getElementById('queue').innerHTML = rows.length ? rows.map(card).join('') : '<div class="empty">Nothing is waiting here.</div>';
    document.querySelectorAll('[data-approve]').forEach((b) => b.addEventListener('click', () => decide(b.dataset.approve, 'APPROVED', 'Approved.')));
    document.querySelectorAll('[data-reject]').forEach((b) => b.addEventListener('click', () => {
      const comment = prompt('Why are you rejecting this?');
      if (comment) decide(b.dataset.reject, 'REJECTED', comment);
    }));
  }

  async function load() {
    const scope = document.getElementById('scope').value;
    const query = scope === 'decided' ? '?status=ALL' : scope === 'mine' ? `?assigned_to=${actingAs().id}` : '';
    let rows = await api(`/approvals${query}`);
    if (scope === 'decided') rows = rows.filter((r) => r.status !== 'PENDING').slice(0, 20);
    state.rows = rows;
    document.getElementById('queue-title').textContent = scope === 'mine' ? `Waiting for ${actingAs().name}` : scope === 'all' ? 'All pending approvals' : 'Recently decided';
    render();
  }

  document.getElementById('scope').addEventListener('change', load);
  document.addEventListener('persona', load);
  poll(load, 3000);
})();
