/* Cases: every onboarding, offboarding and agent access request, newest first. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, actingAs, PEOPLE } = LO;
  const page = LO.shell({
    active: 'cases.html',
    title: 'Cases',
    subtitle: 'Onboarding, offboarding and agent access requests, each with its plan and evidence',
  });

  const STORY = [
    ['44444444-4444-4444-8444-444444444444', 'Amina Rahman', 'AI Engineer'],
    ['55555555-5555-4555-8555-555555555555', 'Rafi Ahmed', 'AI Engineer'],
    [PEOPLE.arif.id, 'Arif Hossain', 'Senior Software Engineer'],
  ];
  const ACTIVE = new Set(['NEW', 'TRIAGE', 'PLANNING', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING', 'RETRYING']);
  const REVIEW = new Set(['HUMAN_REVIEW', 'PAUSED', 'FAILED']);
  const TYPES = [['', 'All'], ['OFFBOARDING', 'Offboarding'], ['ONBOARDING', 'Onboarding'], ['ACCESS_REQUEST', 'Agent access']];

  page.innerHTML = `
    <section class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))" id="summary"></section>
    <section class="card">
      <div class="card-head">
        <div class="tabs" id="tabs"></div><span class="spacer"></span>
        <input id="search" placeholder="Search person, ID or status" />
        <select id="status"><option value="">All statuses</option></select>
        <button class="btn primary" id="new-case">New case</button>
      </div>
      <div class="table-wrap"><table class="data"><thead><tr>
        <th>Case</th><th>Subject</th><th>Type</th><th>Status</th><th>Priority</th><th>Updated</th>
      </tr></thead><tbody id="rows"><tr><td colspan="6"><div class="skeleton" style="height:120px"></div></td></tr></tbody></table></div>
    </section>
    <div class="scrim" id="scrim"></div>
    <div class="modal-wrap" id="modal"><form class="modal" id="form">
      <h2>New case</h2>
      <span class="faint">Created and triaged at once; the plan appears in the workspace.</span>
      <div class="form-grid">
        <label>Type<select id="f-type"><option value="ONBOARDING">Onboarding</option><option value="OFFBOARDING">Offboarding</option></select></label>
        <label>Priority<select id="f-priority"><option>MEDIUM</option><option>HIGH</option><option>LOW</option></select></label>
        <label class="full">Person<select id="f-person">${STORY.map(([id, name, role]) => `<option value="${id}">${esc(name)} · ${esc(role)}</option>`).join('')}</select></label>
        <label class="full">Case facts (JSON)<textarea id="f-facts" class="mono" rows="7"></textarea></label>
      </div>
      <div class="btn-row" style="justify-content:flex-end">
        <button type="button" class="btn" data-close>Cancel</button>
        <button type="submit" class="btn primary" id="f-submit">Create and triage</button>
      </div>
    </form></div>`;

  const state = { cases: [], type: '', loaded: false };
  const caseId = (id) => `LO-${String(id).split('-')[0].toUpperCase()}`;
  const initials = (name) => String(name || '?').split(' ').map((p) => p[0]).join('').slice(0, 2);

  function render() {
    const all = state.cases;
    const tiles = [
      ['Cases', all.length, 'all types', ''],
      ['In progress', all.filter((c) => ACTIVE.has(c.status)).length, 'planning, approval or execution', ''],
      ['Needs review', all.filter((c) => REVIEW.has(c.status)).length, 'human review, paused or failed', all.some((c) => REVIEW.has(c.status)) ? 'bad' : ''],
      ['Completed', all.filter((c) => c.status === 'COMPLETED').length, 'verified end to end', 'ok'],
    ];
    const summary = document.getElementById('summary');
    if (!summary.children.length) summary.innerHTML = tiles.map((_, i) => `<div class="kpi" data-i="${i}"><div class="label"></div><div class="value"></div><div class="sub"></div></div>`).join('');
    tiles.forEach(([label, value, sub, tone], i) => {
      const el = summary.querySelector(`[data-i="${i}"]`);
      el.className = `kpi ${tone}`;
      el.querySelector('.label').textContent = label;
      el.querySelector('.sub').textContent = sub;
      LO.countUp(el.querySelector('.value'), String(value));
    });

    document.getElementById('tabs').innerHTML = TYPES.map(([key, label]) => `<button data-type="${key}" class="${state.type === key ? 'active' : ''}">${label}<span class="n">${key ? all.filter((c) => c.case_type === key).length : all.length}</span></button>`).join('');
    document.querySelectorAll('#tabs button').forEach((b) => b.addEventListener('click', () => { state.type = b.dataset.type; render(); }));

    const statusSelect = document.getElementById('status');
    const current = statusSelect.value;
    const statuses = [...new Set(all.map((c) => c.status))].sort();
    statusSelect.innerHTML = '<option value="">All statuses</option>' + statuses.map((s) => `<option value="${s}">${esc(human(s))}</option>`).join('');
    statusSelect.value = statuses.includes(current) ? current : '';

    const q = document.getElementById('search').value.trim().toLowerCase();
    const rows = all.filter((c) => (!state.type || c.case_type === state.type) && (!statusSelect.value || c.status === statusSelect.value)
      && (!q || `${c.id} ${caseId(c.id)} ${c.subject_name} ${c.status} ${c.agent_key || ''}`.toLowerCase().includes(q)));
    document.getElementById('rows').innerHTML = rows.map((c) => `
      <tr class="clickable" data-id="${c.id}">
        <td><span class="mono" style="color:var(--text)">${caseId(c.id)}</span></td>
        <td><div class="who"><span class="avatar">${esc(initials(c.subject_name))}</span><div><b>${esc(c.subject_name || '—')}</b>
          <small>${c.agent_key ? esc(c.agent_key) : c.created_by_name ? 'by ' + esc(c.created_by_name) : ''}</small></div></div></td>
        <td>${c.case_type === 'ACCESS_REQUEST' ? `<span class="badge agent">agent access${c.tier ? ' · ' + esc(c.tier) : ''}</span>` : `<span class="muted">${esc(human(c.case_type))}</span>`}</td>
        <td>${badge(c.status)}</td>
        <td>${badge(c.priority === 'HIGH' ? 'HIGH' : c.priority === 'LOW' ? 'INACTIVE' : 'MEDIUM', human(c.priority))}</td>
        <td class="faint">${timeAgo(c.updated_at)}</td>
      </tr>`).join('') || `<tr><td colspan="6"><div class="empty"><b>${all.length ? 'No cases match' : 'No cases yet'}</b>${all.length ? 'Change the tab, status or search.' : 'Create one, or start Arif Hossain\'s offboarding from the dashboard.'}</div></td></tr>`;
    document.querySelectorAll('#rows tr[data-id]').forEach((tr) => tr.addEventListener('click', () => { location.href = `workspace.html?case=${tr.dataset.id}`; }));
  }

  async function load() {
    state.cases = await api('/cases?limit=200');
    render();
  }
  ['search', 'status'].forEach((id) => document.getElementById(id).addEventListener('input', render));

  // ---------- New case ----------
  const modal = document.getElementById('modal'), scrim = document.getElementById('scrim');
  const open = (on) => { modal.classList.toggle('open', on); scrim.classList.toggle('open', on); };
  function facts() {
    const onboarding = document.getElementById('f-type').value === 'ONBOARDING';
    const day = (offset) => new Date(Date.now() + offset * 86400000).toISOString().slice(0, 10);
    document.getElementById('f-person').value = onboarding ? STORY[0][0] : PEOPLE.arif.id;
    document.getElementById('f-facts').value = JSON.stringify(onboarding
      ? { start_date: day(0), requires_email: true, requires_github: true, requires_laptop: true, requires_training: true }
      : { last_working_day: day(7), successor_person_id: PEOPLE.nabil.id, manager_id: PEOPLE.nabil.id }, null, 2);
  }
  document.getElementById('new-case').addEventListener('click', () => { facts(); open(true); });
  document.getElementById('f-type').addEventListener('change', facts);
  modal.querySelector('[data-close]').addEventListener('click', () => open(false));
  scrim.addEventListener('click', () => open(false));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') open(false); });
  document.getElementById('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submit = document.getElementById('f-submit');
    submit.disabled = true;
    try {
      let caseFacts;
      try { caseFacts = JSON.parse(document.getElementById('f-facts').value || '{}'); } catch { throw new Error('Case facts must be valid JSON.'); }
      const created = await api('/cases', { method: 'POST', body: {
        case_type: document.getElementById('f-type').value, subject_person_id: document.getElementById('f-person').value,
        created_by_id: actingAs().id, priority: document.getElementById('f-priority').value, case_facts: caseFacts,
      } });
      await api(`/cases/${created.id}/triage`, { method: 'POST', body: {} });
      location.href = `workspace.html?case=${created.id}`;
    } catch (error) { toast(error.message, 'error'); } finally { submit.disabled = false; }
  });

  poll(load, 5000);
})();
