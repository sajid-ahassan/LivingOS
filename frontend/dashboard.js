/* Dashboard: KPI row, live workforce map (D3 force), table, recent cases. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, actingAs, PEOPLE } = LO;
  const page = LO.shell({
    active: 'index.html',
    title: 'Workforce map',
    subtitle: 'People and AI agents of Nexora Labs, with who sponsors which agent',
  });

  page.innerHTML = `
    <section class="kpis" id="kpis"></section>
    <p class="kpi-note" id="kpi-note"></p>
    <section class="split">
      <div class="card map-card">
        <div class="map-toolbar">
          <div class="legend">
            <span><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill="#8fb3ff"/></svg>person</span>
            <span><svg width="12" height="12"><polygon points="3,1 9,1 12,6 9,11 3,11 0,6" fill="#a78bfa"/></svg>AI agent</span>
            <span><svg width="12" height="12"><polygon points="6,1 11,11 1,11" fill="#fbbf24"/></svg>departing</span>
            <span><svg width="12" height="12"><rect x="1" y="1" width="10" height="10" fill="#6b768c"/></svg>inactive</span>
            <span><svg width="12" height="12"><polygon points="3,1 9,1 12,6 9,11 3,11 0,6" fill="#ff5c72"/></svg>orphan or policy breach</span>
            <span><svg width="22" height="12"><line x1="0" y1="6" x2="22" y2="6" stroke="#a78bfa" stroke-dasharray="3 3"/></svg>sponsor</span>
          </div>
        </div>
        <svg id="map" role="img" aria-label="Workforce map of people and AI agents"></svg>
      </div>
      <aside class="card" id="detail">
        <div class="card-head"><h2>Details</h2></div>
        <div class="empty">Click a person or an agent on the map.</div>
      </aside>
    </section>
    <section class="grid-2">
      <div class="card">
        <div class="card-head"><h2>Recent cases</h2><span class="spacer"></span>
          <button class="btn primary" id="start-arif">Start Arif Hossain's offboarding</button></div>
        <div id="cases" class="stack"></div>
      </div>
      <div class="card" id="eval-card">
        <div class="card-head"><h2>Evaluation</h2><span class="spacer"></span><span class="faint" id="eval-when"></span></div>
        <div id="eval"></div>
      </div>
    </section>
    <section class="card">
      <div class="card-head">
        <h2>People and agents</h2><span class="spacer"></span>
        <input id="search" placeholder="Search name, title or agent" />
        <select id="dept"><option value="">All departments</option></select>
        <select id="filter">
          <option value="">Everyone</option>
          <option value="orphan">Orphan agents</option>
          <option value="violation">Policy breaches</option>
          <option value="agents">All agents</option>
          <option value="DEPARTING">Departing people</option>
          <option value="INACTIVE">Inactive people</option>
        </select>
      </div>
      <div class="table-wrap"><table class="data"><thead><tr>
        <th>Name</th><th>Type</th><th>Department</th><th>Status</th><th>Access / sponsor</th>
      </tr></thead><tbody id="rows"></tbody></table></div>
    </section>`;

  const state = { graph: null, selected: new URLSearchParams(location.search).get('highlight') };
  const STORY = new Set(Object.values(PEOPLE).map((p) => p.id));

  // ---------- KPIs ----------
  async function loadKpis() {
    const k = await api('/dashboard/kpis');
    const off = k.latest_offboarding;
    const tiles = [
      { label: 'Termination → all access closed', value: off ? `${off.minutes_to_close_all_access} min` : '—',
        sub: off ? `${off.automated_steps} steps, ${off.human_approvals} approval(s)` : 'run an offboarding', tone: off ? 'ok' : '' },
      { label: 'Agents with an active sponsor', value: pct(k.agents_with_active_sponsor_pct), sub: `${k.agents} agents` },
      { label: 'Orphan agents', value: k.orphan_agents, sub: 'sponsor gone or access expired', tone: k.orphan_agents ? 'bad' : 'ok' },
      { label: 'Human access with an active owner', value: pct(k.human_access_with_active_owner_pct), sub: 'email, GitHub, laptop, training' },
      { label: 'Changes with a policy reason', value: pct(k.with_policy_reason_pct), sub: `${k.access_changes_through_livingops} changes via LivingOps` },
      { label: 'Agent access time-limited', value: `${k.agent_access_time_limited} / ${k.agent_access_time_limited + k.agent_access_standing}`, sub: 'vs standing access' },
    ];
    document.getElementById('kpis').innerHTML = tiles.map((t) => `
      <div class="kpi ${t.tone || ''}"><div class="label">${esc(t.label)}</div>
      <div class="value">${esc(t.value)}</div><div class="sub">${esc(t.sub)}</div></div>`).join('');
    document.getElementById('kpi-note').textContent = k.label;
  }
  const pct = (v) => (v === null || v === undefined ? '—' : `${v}%`);

  // ---------- Map ----------
  const svg = d3.select('#map');
  const root = svg.append('g');
  const linkLayer = root.append('g');
  const nodeLayer = root.append('g');
  const labelLayer = root.append('g');
  svg.call(d3.zoom().scaleExtent([0.4, 4]).on('zoom', (e) => root.attr('transform', e.transform)));
  let simulation = null;
  const positions = new Map();

  const hexagon = (r) => d3.range(6).map((i) => {
    const a = (Math.PI / 3) * i;
    return [r * Math.cos(a), r * Math.sin(a)];
  });

  function nodeFill(n) {
    if (n.kind === 'agent') return n.alarm ? 'var(--bad)' : 'var(--agent)';
    return { DEPARTING: 'var(--warn)', INACTIVE: 'var(--idle)', CANDIDATE: 'var(--accent)' }[n.status] || '#8fb3ff';
  }

  function buildModel(graph) {
    const agentsBySponsor = new Map();
    graph.agents.forEach((a) => {
      if (!agentsBySponsor.has(a.sponsor_id)) agentsBySponsor.set(a.sponsor_id, []);
      agentsBySponsor.get(a.sponsor_id).push(a);
    });
    const people = graph.people.map((p) => ({
      id: p.id, kind: 'person', name: p.name, status: p.employment_status, dept: p.department || 'OTHER',
      title: p.job_title, role: p.app_role, access: p.access_count,
      r: 4 + Math.sqrt(p.access_count || 0) * 2.2,
      faded: p.employment_status === 'INACTIVE' || (p.employment_status === 'DEPARTING' && p.access_count === 0),
      agents: agentsBySponsor.get(p.id) || [],
    }));
    const deptOf = new Map(people.map((p) => [p.id, p.dept]));
    const agents = graph.agents.map((a) => ({
      id: a.resource_key, kind: 'agent', name: a.agent_name || a.resource_key, status: a.status,
      dept: deptOf.get(a.sponsor_id) || a.department || 'OTHER', sponsor: a.sponsor_id,
      risk: a.risk_tier, orphan: a.orphan, reasons: a.orphan_reasons, violation: a.policy_violation,
      alarm: a.orphan || a.policy_violation, r: 7,
    }));
    const ids = new Set([...people, ...agents].map((n) => n.id));
    const links = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ source: e.source, target: e.target, kind: e.kind }));
    return { nodes: [...people, ...agents], links, people, agents };
  }

  function departmentAnchors(nodes, width, height) {
    const depts = [...new Set(nodes.map((n) => n.dept))].sort();
    const anchors = new Map();
    depts.forEach((d, i) => {
      const a = (2 * Math.PI * i) / depts.length - Math.PI / 2;
      anchors.set(d, { x: width / 2 + Math.cos(a) * width * 0.33, y: height / 2 + Math.sin(a) * height * 0.33 });
    });
    return anchors;
  }

  function renderMap(graph) {
    const el = document.getElementById('map');
    const width = el.clientWidth || 900, height = el.clientHeight || 560;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    const model = buildModel(graph);
    const anchors = departmentAnchors(model.nodes, width, height);
    model.nodes.forEach((n) => {
      const p = positions.get(n.id) || anchors.get(n.dept);
      n.x = p.x + (positions.has(n.id) ? 0 : (Math.random() - 0.5) * 40);
      n.y = p.y + (positions.has(n.id) ? 0 : (Math.random() - 0.5) * 40);
    });

    const link = linkLayer.selectAll('line').data(model.links, (d) => `${d.source}>${d.target}`)
      .join('line')
      .attr('class', (d) => (d.kind === 'SPONSOR' ? 'edge-sponsor' : 'edge-manager'));

    const node = nodeLayer.selectAll('g.node').data(model.nodes, (d) => d.id)
      .join((enter) => {
        const g = enter.append('g').attr('class', 'node');
        g.append('circle').attr('class', 'pulse').attr('fill', 'none').attr('stroke', 'var(--bad)').attr('stroke-width', 2);
        g.append('path').attr('class', 'shape');
        g.on('click', (_, d) => select(d.id));
        g.append('title');
        return g;
      });
    node.classed('faded', (d) => d.faded).classed('selected', (d) => d.id === state.selected);
    node.select('path.shape')
      .attr('d', (d) => (d.kind === 'agent' ? `M${hexagon(d.r).join('L')}Z` : d3.symbol(d3.symbolCircle, Math.PI * d.r * d.r)()))
      .attr('fill', nodeFill)
      .attr('stroke', 'var(--bg)').attr('stroke-width', 1.2);
    node.select('circle.pulse').attr('r', (d) => d.r + 2).style('display', (d) => (d.alarm ? null : 'none'));
    node.select('title').text((d) => `${d.name}${d.kind === 'agent' ? ' (agent)' : ''}`);

    link.classed('alarm', (d) => {
      const target = model.nodes.find((n) => n.id === (d.target.id || d.target));
      return d.kind === 'SPONSOR' && target?.alarm;
    });

    const labelled = model.nodes.filter((n) => STORY.has(n.id) || (n.kind === 'agent' && n.alarm) || n.id === state.selected);
    const label = labelLayer.selectAll('text.node-label').data(labelled, (d) => d.id)
      .join('text').attr('class', 'node-label').attr('dy', -12).attr('text-anchor', 'middle')
      .text((d) => d.name.split(' ')[0] + (d.kind === 'agent' ? '' : ''));
    const deptLabel = labelLayer.selectAll('text.dept-label').data([...anchors.keys()], (d) => d)
      .join('text').attr('class', 'dept-label').attr('text-anchor', 'middle').text((d) => human(d));
    // Keep each department label centred just above its own cluster.
    const placeDeptLabels = () => deptLabel.each(function (dept) {
      const members = model.nodes.filter((n) => n.dept === dept);
      if (!members.length) return;
      const x = d3.mean(members, (n) => n.x);
      const top = d3.min(members, (n) => n.y - n.r);
      d3.select(this).attr('x', x).attr('y', top - 10);
    });

    if (simulation) simulation.stop();
    simulation = d3.forceSimulation(model.nodes)
      .force('link', d3.forceLink(model.links).id((d) => d.id)
        .distance((d) => (d.kind === 'SPONSOR' ? 22 : 34)).strength((d) => (d.kind === 'SPONSOR' ? 0.9 : 0.25)))
      .force('charge', d3.forceManyBody().strength(-26))
      .force('collide', d3.forceCollide().radius((d) => d.r + 3))
      .force('x', d3.forceX((d) => anchors.get(d.dept).x).strength(0.12))
      .force('y', d3.forceY((d) => anchors.get(d.dept).y).strength(0.12))
      .alpha(positions.size ? 0.25 : 1)
      .on('tick', () => {
        // Keep every node inside the visible map on narrow screens too.
        model.nodes.forEach((n) => {
          n.x = Math.max(n.r + 4, Math.min(width - n.r - 4, n.x));
          n.y = Math.max(n.r + 16, Math.min(height - n.r - 4, n.y));
        });
        link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
        node.attr('transform', (d) => `translate(${d.x},${d.y})`);
        label.attr('x', (d) => d.x).attr('y', (d) => d.y);
        placeDeptLabels();
        model.nodes.forEach((n) => positions.set(n.id, { x: n.x, y: n.y }));
      });
    state.model = model;
  }

  // ---------- Detail panel ----------
  function select(id) {
    state.selected = id;
    renderDetail();
    renderRows();
    nodeLayer.selectAll('g.node').classed('selected', (d) => d.id === id);
  }

  function renderDetail() {
    const panel = document.getElementById('detail');
    const n = state.model?.nodes.find((x) => x.id === state.selected);
    if (!n) return;
    const people = new Map(state.model.people.map((p) => [p.id, p]));
    if (n.kind === 'agent') {
      const sponsor = people.get(n.sponsor);
      panel.innerHTML = `
        <div class="card-head"><h2>${esc(n.name)}</h2><span class="spacer"></span>${badge('ACTIVE', 'AI agent').replace('ok', 'agent')}</div>
        <dl class="kv">
          <dt>Sponsor</dt><dd>${sponsor ? `<a href="#" data-select="${sponsor.id}">${esc(sponsor.name)}</a> ${badge(sponsor.status)}` : badge('ORPHAN', 'no sponsor')}</dd>
          <dt>Risk tier</dt><dd>${badge(n.risk || 'LOW', n.risk || 'n/a')}</dd>
          <dt>Status</dt><dd>${badge(n.status)}</dd>
          <dt>Orphan</dt><dd>${n.orphan ? n.reasons.map((r) => badge('ORPHAN', human(r))).join(' ') : badge('ACTIVE', 'no')}</dd>
          <dt>Policy</dt><dd>${n.violation ? `${badge('VIOLATION', 'breaks a new policy')} <a href="guardian.html">open Guardian</a>` : badge('ACTIVE', 'compliant')}</dd>
        </dl>`;
    } else {
      panel.innerHTML = `
        <div class="card-head"><h2>${esc(n.name)}</h2><span class="spacer"></span>${badge(n.status)}</div>
        <dl class="kv">
          <dt>Title</dt><dd>${esc(n.title || '—')}</dd>
          <dt>Department</dt><dd>${esc(human(n.dept))}</dd>
          <dt>Live access</dt><dd>${n.access}</dd>
          <dt>Sponsors</dt><dd>${n.agents.length ? n.agents.map((a) => `<a href="#" data-select="${esc(a.resource_key)}">${esc(a.agent_name)}</a>${a.orphan ? ' ' + badge('ORPHAN', 'orphan') : ''}`).join('<br>') : '—'}</dd>
        </dl>
        ${n.id === PEOPLE.arif.id ? '<div class="btn-row" style="margin-top:12px"><button class="btn primary" data-start-arif>Start offboarding</button></div>' : ''}`;
    }
    panel.querySelectorAll('[data-select]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); select(a.dataset.select); }));
    panel.querySelector('[data-start-arif]')?.addEventListener('click', startArif);
  }

  // ---------- Table ----------
  function renderRows() {
    if (!state.model) return;
    const q = document.getElementById('search').value.trim().toLowerCase();
    const dept = document.getElementById('dept').value;
    const filter = document.getElementById('filter').value;
    const people = new Map(state.model.people.map((p) => [p.id, p]));
    const rows = state.model.nodes.filter((n) => {
      if (dept && n.dept !== dept) return false;
      if (filter === 'orphan' && !(n.kind === 'agent' && n.orphan)) return false;
      if (filter === 'violation' && !(n.kind === 'agent' && n.violation)) return false;
      if (filter === 'agents' && n.kind !== 'agent') return false;
      if (['DEPARTING', 'INACTIVE'].includes(filter) && !(n.kind === 'person' && n.status === filter)) return false;
      return !q || `${n.name} ${n.title || ''} ${n.id}`.toLowerCase().includes(q);
    }).sort((a, b) => (b.alarm ? 1 : 0) - (a.alarm ? 1 : 0) || a.name.localeCompare(b.name)).slice(0, 150);
    document.getElementById('rows').innerHTML = rows.map((n) => `
      <tr class="clickable ${n.id === state.selected ? 'selected' : ''}" data-id="${esc(n.id)}">
        <td>${esc(n.name)}</td>
        <td>${n.kind === 'agent' ? '<span class="badge agent">agent</span>' : esc(n.title || 'person')}</td>
        <td>${esc(human(n.dept))}</td>
        <td>${n.kind === 'agent' ? (n.violation ? badge('VIOLATION', 'policy breach') : n.orphan ? badge('ORPHAN', 'orphan') : badge('ACTIVE', 'sponsored')) : badge(n.status)}</td>
        <td>${n.kind === 'agent' ? esc(people.get(n.sponsor)?.name || '—') : n.access}</td>
      </tr>`).join('') || '<tr><td colspan="5" class="faint">No match.</td></tr>';
    document.querySelectorAll('#rows tr[data-id]').forEach((tr) => tr.addEventListener('click', () => select(tr.dataset.id)));
  }
  ['search', 'dept', 'filter'].forEach((id) => document.getElementById(id).addEventListener('input', renderRows));

  async function loadGraph() {
    const graph = await api('/workforce/graph');
    const signature = JSON.stringify(graph);
    if (signature === state.signature) return;
    state.signature = signature;
    renderMap(graph);
    const depts = [...new Set(state.model.nodes.map((n) => n.dept))].sort();
    const select = document.getElementById('dept');
    if (select.options.length === 1) select.insertAdjacentHTML('beforeend', depts.map((d) => `<option value="${esc(d)}">${esc(human(d))}</option>`).join(''));
    renderRows();
    if (state.selected) renderDetail();
  }

  // ---------- Cases and evaluation ----------
  async function loadCases() {
    const cases = await api('/cases?limit=6');
    document.getElementById('cases').innerHTML = cases.length ? cases.map((c) => `
      <a class="item" href="workspace.html?case=${c.id}" style="display:flex;gap:10px;align-items:center;color:inherit">
        <div style="flex:1;min-width:0"><b>${esc(c.subject_name || '—')}</b>
          <div class="faint">${esc(human(c.case_type))}${c.origin ? ' · ' + esc(human(c.origin)) : ''}${c.tier ? ' · tier ' + esc(c.tier) : ''} · ${timeAgo(c.created_at)}</div></div>
        ${badge(c.status)}</a>`).join('') : '<div class="empty">No cases yet.</div>';
  }

  async function loadEvaluation() {
    try {
      const e = await api('/evaluation/latest');
      document.getElementById('eval-when').textContent = `measured ${timeAgo(e.generated_at)} · ${e.demo_mode}`;
      const rows = [
        ['Plans valid first pass', e.plan_generation.first_pass_valid_pct, e.plan_generation.n],
        ['Plans valid after one repair', e.plan_generation.valid_after_repair_pct, e.plan_generation.n],
        ['Steps citing policy evidence', e.evidence.steps_with_policy_evidence_pct, e.evidence.n],
        ['Retrieval recall@1', e.retrieval.recall_at_1_pct, e.retrieval.n],
        ['Guardian impact recall', e.guardian.recall_pct, e.guardian.n_scenarios],
        ['Actions verified', e.execution.verified_completion_pct, e.execution.n],
      ];
      document.getElementById('eval').innerHTML = `<table class="data"><tbody>${rows.map(([l, v, n]) => `
        <tr><td>${esc(l)}</td><td><b>${v === null ? '—' : v + '%'}</b></td><td class="faint">n = ${n}</td></tr>`).join('')}
        <tr><td>Guardian false impacts</td><td><b>${e.guardian.false_impacts}</b></td><td class="faint">seeded scenarios</td></tr></tbody></table>`;
    } catch {
      document.getElementById('eval').innerHTML = '<div class="empty">No evaluation yet. Run <code>python -m app.scripts.run_evaluation</code>.</div>';
    }
  }

  async function startArif() {
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Dhaka' });
    const creator = ['farhana', 'nabil'].includes(LO.persona()) ? actingAs() : PEOPLE.farhana;
    try {
      const created = await api('/cases', { method: 'POST', body: {
        case_type: 'OFFBOARDING', subject_person_id: PEOPLE.arif.id, created_by_id: creator.id, priority: 'HIGH',
        case_facts: { last_working_day: today, manager_id: PEOPLE.nabil.id, successor_person_id: PEOPLE.nabil.id,
          department: 'ENGINEERING', job_title: 'Senior Software Engineer' },
      } });
      await api(`/cases/${created.id}/triage`, { method: 'POST' });
      location.href = `workspace.html?case=${created.id}`;
    } catch (error) { toast(error.message, 'error'); }
  }
  document.getElementById('start-arif').addEventListener('click', startArif);

  loadKpis(); loadEvaluation();
  poll(loadGraph, 3000);
  poll(loadCases, 5000);
  setInterval(loadKpis, 10000);
})();
