/* Security: access events scored by the Isolation Forest, reviewed by a human. */
(function () {
  const { api, esc, badge, toast, human, poll, PEOPLE } = LO;
  const page = LO.shell({
    active: 'security.html',
    title: 'Security',
    subtitle: 'ML-scored access anomalies; a human makes every decision',
  });

  const NAMES = {
    '44444444-4444-4444-8444-444444444444': 'Amina Rahman',
    '55555555-5555-4555-8555-555555555555': 'Rafi Ahmed',
    ...Object.fromEntries(Object.values(PEOPLE).map((p) => [p.id, p.name])),
  };
  const FEATURES = {
    event_count: 'Events', failed_login_count: 'Failed logins', failed_login_ratio: 'Failed login ratio',
    command_count: 'Commands', file_event_count: 'File events', http_count: 'HTTP events', email_count: 'Email events',
    device_count: 'Device events', session_count: 'Sessions', unique_agents: 'Unique sources', unique_decoders: 'Unique destinations',
    unique_actions: 'Unique actions', high_severity_count: 'Failed events', high_severity_ratio: 'Failure ratio',
    off_hours_count: 'Off-hours events', off_hours_ratio: 'Off-hours ratio',
  };
  const HISTORY_KEY = 'livingops.securityReviews.v1';
  const name = (id) => NAMES[id] || `Person ${String(id).slice(0, 8)}`;
  const fixed = (v, d = 3) => (Number.isFinite(Number(v)) ? Number(v).toFixed(d) : '—');
  const threshold = (a) => Number(a?.features_data?._ml?.threshold);
  const signal = (a) => { const f = a.features_data || {}; return Number(f.off_hours_count) > 0 ? 'Off-hours' : (a.success === false || Number(f.failed_login_count) > 0) ? 'Failed event' : 'Anomaly'; };
  const when = (v) => (v ? new Date(v).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');
  const loadHistory = () => { try { const x = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); return Array.isArray(x) ? x : []; } catch { return []; } };
  const state = { alerts: [], selected: null, history: loadHistory() };

  page.innerHTML = `
    <section class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))" id="summary"></section>
    <section class="card">
      <div class="card-head"><h2>Open alerts</h2><span class="spacer"></span>
        <input id="search" placeholder="Search person, event or route" />
        <select id="signal"><option value="">All signals</option><option>Off-hours</option><option>Failed event</option><option>Anomaly</option></select>
        <button class="btn primary" id="record">Record access event</button></div>
      <div class="table-wrap"><table class="data"><thead><tr>
        <th>Person</th><th>Event</th><th>Route</th><th>Anomaly score</th><th>Signal</th><th>Time</th>
      </tr></thead><tbody id="rows"><tr><td colspan="6"><div class="skeleton" style="height:100px"></div></td></tr></tbody></table></div>
    </section>
    <section class="grid-2">
      <div class="card"><div class="card-head"><h2>Detection model</h2><span class="spacer"></span><span class="badge ok">Isolation Forest</span></div>
        <dl class="kv"><dt>Dataset</dt><dd id="m-dataset">SPEDIA</dd><dt>Threshold</dt><dd class="num" id="m-threshold">after the first scored event</dd>
        <dt>Feature window</dt><dd>1 hour</dd><dt>Decision</dt><dd>Always a human</dd></dl></div>
      <div class="card"><div class="card-head"><h2>Recent reviews</h2><span class="spacer"></span><span class="faint">this browser</span></div>
        <div class="stack" id="history"></div></div>
    </section>
    <div class="scrim" id="scrim"></div>
    <aside class="side-panel" id="panel"></aside>
    <div class="modal-wrap" id="modal"><form class="modal" id="event-form">
      <h2>Record access event</h2><span class="faint">LivingOps builds the 1-hour features and scores the event.</span>
      <div class="form-grid">
        <label>Person<select id="e-person">${['44444444-4444-4444-8444-444444444444', '55555555-5555-4555-8555-555555555555', PEOPLE.arif.id, PEOPLE.tahmid.id].map((id) => `<option value="${id}">${esc(name(id))}</option>`).join('')}</select></label>
        <label>Time<input id="e-time" type="datetime-local" /></label>
        <label>Event type<input id="e-type" value="LOGIN" maxlength="40" /></label>
        <label>Result<select id="e-success"><option value="true">Success</option><option value="false">Failed</option></select></label>
        <label class="full">Source<input id="e-source" value="web-console" maxlength="120" /></label>
        <label class="full">Destination<input id="e-dest" value="github:aurora" maxlength="120" /></label>
      </div>
      <div id="e-result"></div>
      <div class="btn-row" style="justify-content:flex-end"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary" id="e-submit">Score event</button></div>
    </form></div>`;

  const panel = document.getElementById('panel'), modal = document.getElementById('modal'), scrim = document.getElementById('scrim');
  const closeAll = () => { panel.classList.remove('open'); modal.classList.remove('open'); scrim.classList.remove('open'); state.selected = null; };
  scrim.addEventListener('click', closeAll);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAll(); });

  function render() {
    const open = state.alerts.length;
    const tiles = [
      ['Open alerts', open, open ? 'awaiting a human decision' : 'nothing to review', open ? 'bad' : 'ok'],
      ['Off-hours alerts', state.alerts.filter((a) => signal(a) === 'Off-hours').length, 'outside 06:00–22:00', ''],
      ['Decision threshold', fixed(state.alerts.map(threshold).find(Number.isFinite), 3), 'Isolation Forest', ''],
      ['Reviewed', state.history.length, 'confirmed or false positive', ''],
    ];
    const summary = document.getElementById('summary');
    summary.innerHTML = tiles.map(([l, v, s, t]) => `<div class="kpi ${t}"><div class="label">${l}</div><div class="value">${esc(v)}</div><div class="sub">${s}</div></div>`).join('');
    const ml = state.alerts.find((a) => a.features_data?._ml)?.features_data._ml;
    if (ml) { document.getElementById('m-dataset').textContent = ml.dataset_name || 'SPEDIA'; document.getElementById('m-threshold').textContent = fixed(ml.threshold, 6); }

    const q = document.getElementById('search').value.trim().toLowerCase();
    const sig = document.getElementById('signal').value;
    const rows = state.alerts.filter((a) => (!sig || signal(a) === sig) && (!q || `${name(a.person_id)} ${a.event_type} ${a.source} ${a.destination}`.toLowerCase().includes(q)))
      .sort((a, b) => Number(b.anomaly_score) - Number(a.anomaly_score));
    document.getElementById('rows').innerHTML = rows.map((a) => `
      <tr class="clickable" data-id="${esc(a.id)}">
        <td><div class="who"><span class="avatar">${esc(name(a.person_id).split(' ').map((p) => p[0]).join('').slice(0, 2))}</span><b>${esc(name(a.person_id))}</b></div></td>
        <td><b style="font-weight:550">${esc(a.event_type)}</b> <span class="faint">${a.success ? 'success' : 'failed'}</span></td>
        <td class="mono">${esc(a.source)} → ${esc(a.destination)}</td>
        <td style="min-width:140px"><span class="num">${fixed(a.anomaly_score)}</span><div class="bar" style="margin-top:5px"><i style="width:${Math.min(100, Math.max(4, Number(a.anomaly_score) * 100))}%"></i></div></td>
        <td>${badge(signal(a) === 'Off-hours' ? 'DEPARTING' : 'FAILED', signal(a))}</td>
        <td class="faint">${when(a.event_time)}</td>
      </tr>`).join('') || `<tr><td colspan="6"><div class="empty"><b>${open ? 'No alerts match' : 'No open alerts'}</b>${open ? 'Change the search or signal.' : 'Scored events above the threshold appear here.'}</div></td></tr>`;
    document.querySelectorAll('#rows tr[data-id]').forEach((tr) => tr.addEventListener('click', () => openAlert(tr.dataset.id)));

    document.getElementById('history').innerHTML = state.history.slice(0, 5).map((r) => `
      <div class="item" style="display:flex;gap:10px;align-items:center">${badge(r.alert_status === 'CONFIRMED' ? 'FAILED' : 'ACTIVE', human(r.alert_status))}
        <div style="min-width:0"><b style="font-weight:550">${esc(name(r.person_id))} · ${esc(r.event_type)}</b><div class="faint">${esc(r.review_comment || 'no comment')} · ${when(r.updated_at || r.event_time)}</div></div></div>`).join('')
      || '<div class="empty"><b>No reviews yet</b>Open an alert to confirm it or mark it a false positive.</div>';
  }

  function openAlert(id) {
    const a = state.alerts.find((x) => String(x.id) === String(id));
    if (!a) return;
    state.selected = a;
    const f = a.features_data || {};
    panel.innerHTML = `<button class="btn small close" data-close aria-label="Close">✕</button>
      ${badge('FAILED', signal(a))}
      <h2 style="margin-top:10px">${esc(a.event_type)} anomaly</h2><span class="faint">${esc(name(a.person_id))} · ${when(a.event_time)}</span>
      <section><h3>Event</h3><dl class="kv"><dt>Route</dt><dd class="mono">${esc(a.source)} → ${esc(a.destination)}</dd><dt>Result</dt><dd>${a.success ? 'success' : 'failed'}</dd></dl></section>
      <section><h3>ML assessment</h3><div class="grid-2">
        <div class="item"><div class="faint">Anomaly score</div><div class="num" style="font-size:22px;color:var(--bad)">${fixed(a.anomaly_score, 4)}</div></div>
        <div class="item"><div class="faint">Threshold</div><div class="num" style="font-size:22px">${fixed(threshold(a), 4)}</div></div></div></section>
      <section><h3>Observed features · 1 hour</h3><dl class="kv">${Object.keys(FEATURES).filter((k) => f[k] != null).map((k) => `<dt>${FEATURES[k]}</dt><dd class="num">${k.includes('ratio') ? fixed(f[k], 2) : esc(f[k])}</dd>`).join('') || '<dd>none returned</dd>'}</dl></section>
      <section><h3>Human review</h3><form id="review" class="stack">
        <select id="r-decision"><option value="CONFIRMED">Confirm anomaly</option><option value="FALSE_POSITIVE">Mark false positive</option></select>
        <textarea id="r-comment" maxlength="1000" placeholder="Reason for this decision"></textarea>
        <button class="btn primary" id="r-submit">Submit review as Tahmid Hasan</button></form></section>`;
    panel.classList.add('open'); scrim.classList.add('open');
    panel.querySelector('[data-close]').addEventListener('click', closeAll);
    panel.querySelector('#review').addEventListener('submit', async (e) => {
      e.preventDefault();
      const submit = panel.querySelector('#r-submit');
      submit.disabled = true;
      try {
        const reviewed = await api(`/access-events/${encodeURIComponent(a.id)}/review`, { method: 'POST', body: {
          reviewed_by: PEOPLE.tahmid.id, decision: panel.querySelector('#r-decision').value, comment: panel.querySelector('#r-comment').value.trim() || null } });
        state.history = [reviewed, ...state.history.filter((x) => x.id !== reviewed.id)].slice(0, 50);
        try { localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history)); } catch { /* private mode */ }
        toast(`Alert marked ${human(reviewed.alert_status)}.`);
        closeAll(); await load();
      } catch (error) { toast(error.message, 'error'); submit.disabled = false; }
    });
  }

  // ---------- Record event ----------
  const localNow = () => { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
  document.getElementById('record').addEventListener('click', () => {
    document.getElementById('e-time').value = localNow();
    document.getElementById('e-result').innerHTML = '';
    modal.classList.add('open'); scrim.classList.add('open');
  });
  modal.querySelector('[data-close]').addEventListener('click', closeAll);
  document.getElementById('event-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submit = document.getElementById('e-submit');
    submit.disabled = true;
    try {
      const result = await api('/access-events', { method: 'POST', body: {
        person_id: document.getElementById('e-person').value, event_time: new Date(document.getElementById('e-time').value).toISOString(),
        source: document.getElementById('e-source').value.trim(), destination: document.getElementById('e-dest').value.trim(),
        event_type: document.getElementById('e-type').value.trim(), success: document.getElementById('e-success').value === 'true' } });
      const alerted = result.alert_status === 'OPEN';
      document.getElementById('e-result').innerHTML = `<div class="item ${alerted ? 'highlight' : ''}" style="margin-bottom:12px"><b>${alerted ? 'Anomaly alert opened' : 'Recorded, no alert'}</b>
        <div class="faint num">score ${fixed(result.anomaly_score, 6)} · threshold ${fixed(threshold(result), 6)}</div></div>`;
      await load();
      if (alerted) setTimeout(() => { closeAll(); openAlert(result.id); }, 600);
    } catch (error) { toast(error.message, 'error'); } finally { submit.disabled = false; }
  });

  async function load() {
    try { state.alerts = (await api('/security/alerts')) || []; } catch (error) { state.alerts = []; toast(error.message, 'error'); }
    render();
  }
  ['search', 'signal'].forEach((id) => document.getElementById(id).addEventListener('input', render));
  poll(load, 10000);
})();
