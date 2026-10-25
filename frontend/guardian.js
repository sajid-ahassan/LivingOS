/* Policy Guardian: activate a new policy version, see old and new rules side
   by side, and fix every plan, lesson and live agent access it affects. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, actingAs, PEOPLE } = LO;
  const page = LO.shell({
    active: 'guardian.html',
    title: 'Policy Guardian',
    subtitle: 'When a policy changes, past decisions and live access are checked again',
  });
  page.innerHTML = `
    <section class="split">
      <div class="stack" id="change"></div>
      <div class="stack">
        <div class="card" id="activate"></div>
        <div class="card"><div class="card-head"><h2>Policy changes</h2></div><div id="changes" class="stack"></div></div>
      </div>
    </section>`;

  const state = { selected: new URLSearchParams(location.search).get('change'), view: null, busy: false, draft: null };

  // ---------- Activate Access Policy V2 ----------
  async function renderActivate() {
    const el = document.getElementById('activate');
    if (!state.draft) {
      try { state.draft = await api('/demo/policies/access/v2'); } catch { state.draft = null; }
    }
    const isTahmid = actingAs().id === PEOPLE.tahmid.id;
    el.innerHTML = `
      <div class="card-head"><h2>New policy version</h2></div>
      ${state.draft ? `
        <p class="muted" style="margin-top:0">Access Policy V2 adds two rules about AI agents (7 and 8).</p>
        <details><summary class="faint">Show text</summary><pre class="mono" style="white-space:pre-wrap">${esc(state.draft.content_text)}</pre></details>
        <div class="btn-row" style="margin-top:10px">
          <button class="btn primary" id="activate-btn" ${!isTahmid || state.busy ? 'disabled' : ''}>${state.busy ? 'Analysing…' : 'Activate Access Policy V2'}</button>
        </div>
        ${isTahmid ? '' : '<p class="faint">Switch "Acting as" to Tahmid Hasan (IT Owner) to activate.</p>'}` : '<div class="empty">Seed policy not found.</div>'}`;
    el.querySelector('#activate-btn')?.addEventListener('click', activate);
  }

  async function activate() {
    state.busy = true; renderActivate();
    try {
      const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Dhaka' });
      const result = await api('/policy-guardian/activate', { method: 'POST', body: {
        policy_code: 'ACCESS', title: 'Access Policy', version_number: state.draft.version,
        department: 'GLOBAL', effective_from: today, uploaded_by: PEOPLE.tahmid.id,
        content_text: state.draft.content_text,
      } });
      state.selected = result.policy_change.id;
      toast(`Guardian found ${result.impacts.length} impact(s).`);
      await loadChanges();
    } catch (error) { toast(error.message, 'error'); }
    finally { state.busy = false; renderActivate(); }
  }

  // ---------- Change list ----------
  async function loadChanges() {
    const changes = await api('/policy-guardian/changes');
    if (!state.selected && changes.length) state.selected = changes[0].id;
    document.getElementById('changes').innerHTML = changes.length ? changes.map((c) => `
      <a class="item" href="?change=${c.id}" data-change="${c.id}" style="color:inherit;display:block">
        <div class="card-head" style="margin:0"><b>${esc(c.policy_code)} V${c.old_version} → V${c.new_version}</b>
          <span class="spacer"></span>${badge(c.overall_risk, `${c.overall_risk} risk`)}</div>
        <div class="faint">${c.open_impacts} open impact(s) · ${timeAgo(c.created_at)}</div></a>`).join('')
      : '<div class="empty"><b>No policy changes yet</b>Activate a new version to see what it affects.</div>';
    document.querySelectorAll('[data-change]').forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault(); state.selected = a.dataset.change; history.replaceState(null, '', `?change=${state.selected}`); loadView();
    }));
    if (state.selected) await loadView();
    else document.getElementById('change').innerHTML = '<div class="card"><div class="empty" style="padding:48px 18px"><b>Policies are stable</b>When a new version is activated, the Guardian compares the rules and re-checks every plan, lesson and live agent access that depended on the old one.</div></div>';
  }

  // ---------- One change ----------
  async function loadView() {
    state.view = await api(`/policy-guardian/changes/${state.selected}/view`);
    renderView();
  }

  function renderView() {
    const v = state.view;
    const s = v.summary || {};
    const clauses = (list) => list.map((c) => `<div class="clause ${c.added ? 'added' : ''}"><span class="n">${c.number}.</span>${esc(c.text)}${c.added ? ' <span class="badge ok">new</span>' : ''}</div>`).join('');
    document.getElementById('change').innerHTML = `
      <div class="card">
        <div class="card-head"><h2>${esc(v.policy_code)} V${v.old_version} → V${v.new_version}</h2>${badge(v.overall_risk, `${v.overall_risk} risk`)}
          <span class="spacer"></span><span class="faint">${timeAgo(v.created_at)}</span></div>
        ${s.rationale ? `<div class="ai-note"><b>AI summary of the change</b>${esc(s.rationale)}</div>` : ''}
        <p class="faint">Which items are affected is decided by policy links and rules, not by the AI.</p>
        <div class="grid-2" style="margin-top:14px">
          <div class="stack" style="gap:6px"><h3>V${v.old_version} · before</h3>${clauses(v.old_clauses)}</div>
          <div class="stack" style="gap:6px"><h3 style="color:var(--ok)">V${v.new_version} · now</h3>${clauses(v.new_clauses)}</div>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><h2>What this change affects</h2><span class="spacer"></span><span class="faint">${v.impacts.length} impact(s)</span></div>
        <div class="stack">${impactList(v.impacts)}</div>
      </div>`;
    document.querySelectorAll('[data-fix]').forEach((b) => b.addEventListener('click', () => fix(b.dataset.fix, b.dataset.kind)));
  }

  // What needs a decision first, by risk; completed cases that only keep their
  // history fold into one line so they do not crowd the screen.
  function impactList(impacts) {
    if (!impacts.length) return '<div class="empty"><b>No impacts</b>Nothing depended on the old version.</div>';
    const rank = { HIGH: 0, MEDIUM: 1, LOW: 2 };
    const history = impacts.filter((i) => i.recommended_action === 'NO_ACTION');
    const actionable = impacts.filter((i) => i.recommended_action !== 'NO_ACTION')
      .sort((a, b) => (rank[a.risk_level] ?? 3) - (rank[b.risk_level] ?? 3));
    return actionable.map(impactCard).join('') + (history.length ? `
      <details class="item"><summary class="faint" style="cursor:pointer">${history.length} completed case${history.length === 1 ? '' : 's'} kept as history, no action needed</summary>
        <div class="stack" style="margin-top:10px">${history.map(impactCard).join('')}</div></details>` : '');
  }

  function impactCard(i) {
    const t = i.target || {};
    const open = ['OPEN', 'REMEDIATING'].includes(i.status);
    let action = '';
    if (i.status === 'OPEN' && i.target_type === 'RESOURCE' && i.recommended_action === 'REGENERATE') action = `<button class="btn primary" data-fix="${i.id}" data-kind="remediate">Downscope to read-only</button>`;
    if (i.status === 'OPEN' && i.target_type === 'RESOURCE' && i.recommended_action === 'REVIEW') action = `<button class="btn primary" data-fix="${i.id}" data-kind="recertify">Re-certify sponsor</button>`;
    if (i.status === 'OPEN' && i.target_type === 'PLAN' && i.recommended_action === 'REGENERATE') action = `<button class="btn" data-fix="${i.id}" data-kind="regenerate">Regenerate plan</button>`;
    const what = {
      RESOURCE: `Live access: <b>${esc(t.label || '')}</b> <span class="mono faint">${esc(t.resource_key || '')}</span>${t.owner_name ? ` · sponsor ${esc(t.owner_name)}` : ''}${t.permission ? ` · ${esc(t.permission)}` : ''}`,
      LEARNING: `Approved lesson: <b>${esc(t.lesson || '')}</b> ${t.lesson_status ? badge(t.lesson_status) : ''}`,
      PLAN: `Plan: <b>${esc(t.label || '')}</b>${t.subject_name ? ` for ${esc(t.subject_name)}` : ''}`,
    }[i.target_type] || esc(i.target_type);
    return `<div class="item ${open && i.risk_level === 'HIGH' ? 'highlight' : ''}">
      <div class="card-head" style="margin-bottom:6px">${badge(i.risk_level, `${i.risk_level}`)}
        <span class="badge idle">${esc(human(i.recommended_action))}</span><span class="spacer"></span>${badge(i.status)}</div>
      <div>${what}</div>
      <div class="faint" style="margin-top:4px">${esc(i.explanation)}</div>
      ${i.target_type === 'LEARNING' && i.status === 'OPEN' ? '<div class="faint">Removed from the AI\'s memory; it will not guide new plans.</div>' : ''}
      <div class="btn-row" style="margin-top:8px">
        ${t.agent_key ? `<a class="btn small" href="index.html?highlight=${encodeURIComponent(t.agent_key)}">Show on map</a>` : ''}
        ${t.case_id ? `<a class="btn small" href="workspace.html?case=${t.case_id}">Open case</a>` : ''}
        <span class="spacer"></span>${action}</div>
    </div>`;
  }

  async function fix(id, kind) {
    const me = actingAs();
    try {
      if (kind === 'remediate') {
        const r = await api(`/policy-guardian/impacts/${id}/remediate`, { method: 'POST', body: { requested_by: me.id } });
        toast('Remediation opened; approve it on the Approvals page.');
        if (r.case_id) setTimeout(() => { location.href = 'approvals.html'; }, 900);
      } else if (kind === 'recertify') {
        await api(`/policy-guardian/impacts/${id}/recertify`, { method: 'POST', body: { decided_by: me.id } });
        toast('Sponsor re-certified.');
      } else {
        await api(`/policy-guardian/impacts/${id}/regenerate`, { method: 'POST', body: { resolved_by: me.id, comment: 'Regenerated after policy change.' } });
        toast('Plan regenerated under the new policy.');
      }
      await loadView();
    } catch (error) { toast(error.message, 'error'); }
  }

  document.addEventListener('persona', renderActivate);
  renderActivate();
  poll(loadChanges, 5000);
})();
