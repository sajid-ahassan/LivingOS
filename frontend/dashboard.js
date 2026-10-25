/* Dashboard: the ownership tree.
   Left, Nexora Labs as an orb ringed by one particle per person and agent
   (red = needs an owner). Middle, one glass card per department. Right, the
   chosen department fans out: every person, with the agents they sponsor
   directly beneath them. When ownership moves, the agent glides to its new
   sponsor; when something newly needs an owner, it flares. The glass panel
   on the right explains whatever is selected. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, actingAs, PEOPLE } = LO;
  const page = LO.shell({ active: 'index.html', title: 'Workforce map', bare: true });
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const STORY = new Set(Object.values(PEOPLE).map((p) => p.id));
  const SLOTS = 15, SPAN = 150;   // visible fan items and the arc they span, in degrees

  const SHAPE = {
    person: '<circle cx="7" cy="7" r="4.6" fill="currentColor"/>',
    agent: '<polygon points="7,1.2 12.2,4.1 12.2,9.9 7,12.8 1.8,9.9 1.8,4.1" fill="currentColor"/>',
    departing: '<polygon points="7,1.2 13,12.4 1,12.4" fill="currentColor"/>',
    inactive: '<rect x="2.5" y="2.5" width="9" height="9" rx="1.5" fill="currentColor"/>',
  };
  const ICON = {
    pulse: '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
    team: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c.6-3.4 3-5.4 6-5.4s5.4 2 6 5.4"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14.6c2.4.2 4.2 1.9 4.8 4.4"/>',
    person: '<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.8 3.6-6 7-6s6.2 2.2 7 6"/>',
    agent: '<rect x="5" y="7" width="14" height="11" rx="3"/><path d="M12 3v4M9 12h.01M15 12h.01M9.5 15.5h5"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l2 2M15 8l2 2"/>',
    alert: '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17h.01"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    check: '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 12.5l2.4 2.4 4.6-5"/>',
    shield: '<path d="M12 3l8 3.5v5.5c0 4.6-3.4 8-8 9-4.6-1-8-4.4-8-9V6.5z"/>',
    doc: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h4"/>',
  };
  const ico = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[name]}</svg>`;

  page.innerHTML = `
    <section class="card stage" id="stage">
      <svg class="tree" id="tree">
        <defs>
          <linearGradient id="dept-grad" x1="0" x2="1"><stop offset="0" stop-color="#7fe0cf" stop-opacity=".15"/><stop offset="1" stop-color="#e6bd6e" stop-opacity=".9"/></linearGradient>
          <linearGradient id="line-grad" x1="0" x2="1"><stop offset="0" stop-color="#e6bd6e" stop-opacity=".9"/><stop offset=".6" stop-color="#cfe9e4" stop-opacity=".55"/><stop offset="1" stop-color="#cfe9e4" stop-opacity=".25"/></linearGradient>
          <linearGradient id="hot-grad" x1="0" x2="1"><stop offset="0" stop-color="#e6bd6e" stop-opacity=".8"/><stop offset="1" stop-color="#ff6a5a"/></linearGradient>
        </defs>
        <g id="lines"></g>
      </svg>
      <div class="orb-wrap" id="orb" title="Nexora Labs overview">
        <div class="halo-ring"></div><div class="halo-ring r2"></div>
        <svg class="particles" id="ring-people" viewBox="-140 -140 280 280"></svg>
        <svg class="particles rev" id="ring-agents" viewBox="-140 -140 280 280"></svg>
        <div class="orb" id="orb-core"></div>
        <div class="orb-label top"><b>Nexora Labs</b><span id="orb-count"></span></div>
        <div class="orb-label bottom" id="orb-alarm"></div>
      </div>
      <div id="depts"></div>
      <div id="fan"></div>
      <div class="fan-hint" id="fan-hint"></div>
      <form class="find" id="find" autocomplete="off">
        <input id="find-input" list="find-list" placeholder="Find a person or an agent…" aria-label="Find a person or an agent" />
        <datalist id="find-list"></datalist>
        <button class="go" aria-label="Find">→</button>
      </form>
      <aside class="insight" id="insight"><div class="skeleton" style="height:28px;width:60%"></div><div class="skeleton" style="height:120px"></div><div class="skeleton" style="height:180px"></div></aside>
    </section>
    <p class="kpi-note" id="kpi-note"></p>
    <section class="grid-2">
      <div class="card">
        <div class="card-head"><h2>Recent cases</h2><span class="spacer"></span>
          <button class="btn primary" data-start-arif>Start Arif Hossain's offboarding</button></div>
        <div id="cases" class="stack"><div class="item skeleton" style="height:54px"></div><div class="item skeleton" style="height:54px"></div></div>
      </div>
      <div class="card">
        <div class="card-head"><h2>Evaluation</h2><span class="spacer"></span><span class="faint" id="eval-when"></span></div>
        <div id="eval"><div class="skeleton" style="height:180px"></div></div>
      </div>
    </section>
    <section class="card">
      <div class="card-head">
        <h2>People and agents</h2><span class="spacer"></span>
        <input id="search" placeholder="Search name, title or agent" />
        <select id="dept-filter"><option value="">All departments</option></select>
        <select id="filter">
          <option value="">Everyone</option><option value="orphan">Orphan agents</option><option value="violation">Policy breaches</option>
          <option value="agents">All agents</option><option value="DEPARTING">Departing people</option><option value="INACTIVE">Inactive people</option>
        </select>
      </div>
      <div class="table-wrap"><table class="data"><thead><tr>
        <th>Name</th><th>Type</th><th>Department</th><th>Status</th><th>Access / sponsor</th>
      </tr></thead><tbody id="rows"></tbody></table></div>
    </section>`;

  const state = {
    model: null, signature: null, kpis: null, dept: null, offset: 0, focus: 'company', hovered: null,
    highlight: new URLSearchParams(location.search).get('highlight'), first: true, panelSig: null,
  };
  const $ = (id) => document.getElementById(id);
  const stage = $('stage');
  const pct = (v) => (v === null || v === undefined ? null : `${v}%`);

  // ---------- Model ----------
  function buildModel(graph) {
    const agentsBySponsor = new Map();
    graph.agents.forEach((a) => {
      if (!agentsBySponsor.has(a.sponsor_id)) agentsBySponsor.set(a.sponsor_id, []);
      agentsBySponsor.get(a.sponsor_id).push(a.resource_key);
    });
    const people = graph.people.map((p) => ({
      id: p.id, kind: 'person', name: p.name, status: p.employment_status, dept: p.department || 'OTHER',
      title: p.job_title, role: p.app_role, access: p.access_count, agentIds: agentsBySponsor.get(p.id) || [],
    }));
    const byId = new Map(people.map((p) => [p.id, p]));
    const agents = graph.agents.map((a) => ({
      id: a.resource_key, kind: 'agent', name: a.agent_name || a.resource_key, status: a.status,
      dept: byId.get(a.sponsor_id)?.dept || a.department || 'OTHER', sponsor: a.sponsor_id,
      risk: a.risk_tier, orphan: a.orphan, reasons: a.orphan_reasons || [], violation: a.policy_violation,
      alarm: a.orphan || a.policy_violation,
    }));
    agents.forEach((a) => byId.set(a.id, a));
    const depts = d3.groups([...people, ...agents], (n) => n.dept).map(([dept, members]) => {
      const ag = members.filter((n) => n.kind === 'agent');
      return {
        dept, members, people: members.length - ag.length, agents: ag.length,
        alarms: ag.filter((a) => a.alarm).length, departing: members.filter((n) => n.status === 'DEPARTING').length,
        coverage: ag.length ? Math.round((ag.filter((a) => !a.orphan).length / ag.length) * 100) : 100,
      };
    }).sort((a, b) => b.members.length - a.members.length || a.dept.localeCompare(b.dept));
    return { people, agents, byId, depts };
  }

  // A department's fan: each person followed by the agents they sponsor;
  // groups that need attention first, then the story characters.
  function fanOrder(model, dept) {
    const people = model.people.filter((p) => p.dept === dept);
    const groups = people.map((p) => {
      const agents = p.agentIds.map((id) => model.byId.get(id)).filter(Boolean);
      const weight = (agents.some((a) => a.alarm) ? 4 : 0) + (p.status === 'DEPARTING' ? 2 : 0) + (STORY.has(p.id) ? 1 : 0);
      return { p, agents, weight };
    }).sort((a, b) => b.weight - a.weight || a.p.name.localeCompare(b.p.name));
    const orphanAgents = model.agents.filter((a) => a.dept === dept && !model.byId.get(a.sponsor));
    return [...groups.flatMap((g) => [g.p, ...g.agents]), ...orphanAgents];
  }

  // ---------- Geometry ----------
  function geometry() {
    const W = stage.clientWidth, H = stage.clientHeight;
    const panel = W > 1100 ? 412 : 0;
    const right = W - panel;
    const orb = { x: Math.max(150, Math.min(210, right * 0.16)), y: H / 2 };
    const deptX = orb.x + 155;
    const n = state.model.depts.length;
    const spacing = Math.min(62, (H - 70) / Math.max(n, 1));
    const deptY = (i) => H / 2 + (i - (n - 1) / 2) * spacing;
    const origin = { x: deptX + 168, y: deptY(Math.max(0, state.model.depts.findIndex((d) => d.dept === state.dept))) };
    const ax = origin.x + 26;
    const rx = Math.max(90, Math.min(240, right - ax - 250));
    const step = Math.min(42, (H - 64) / SLOTS);
    return { W, H, panel, right, orb, deptX, deptY, origin, ax, ay: H / 2, rx, step };
  }
  // Equal vertical steps along a bowed arc, so labels never collide.
  function slot(g, k) {
    const half = (SLOTS - 1) / 2;
    const dy = (k - half) * g.step;
    const reach = half * g.step * 1.15;
    const off = Math.abs(k - half);
    return { x: g.ax + g.rx * Math.sqrt(Math.max(0, 1 - (dy / reach) ** 2)), y: g.ay + dy,
      opacity: k < 0 || k > SLOTS - 1 ? 0 : off > half - 2 ? 0.45 + 0.55 * (half - off) / 2 : 1 };
  }
  const curve = (x1, y1, x2, y2, a = 0.45, b = 0.4) => `M${x1},${y1}C${x1 + (x2 - x1) * a},${y1} ${x2 - (x2 - x1) * b},${y2} ${x2},${y2}`;

  // ---------- Render: orb ----------
  function renderOrb(g) {
    const orb = $('orb');
    orb.style.left = `${g.orb.x}px`; orb.style.top = `${g.orb.y}px`;
    const m = state.model;
    const alarms = m.agents.filter((a) => a.alarm).length;
    $('orb-count').textContent = `${m.people.length} people · ${m.agents.length} agents`;
    $('orb-alarm').innerHTML = alarms ? `<span class="badge bad">${alarms} need an owner</span>` : '<span class="badge ok">every agent owned</span>';
    $('orb-core').classList.toggle('hot', alarms > 0);
    const ring = (svgId, nodes, r) => {
      d3.select(`#${svgId}`).selectAll('circle').data(nodes, (d) => d.id).join('circle')
        .attr('cx', (d, i) => Math.cos((i / nodes.length) * Math.PI * 2) * (r + (i % 3) * 3))
        .attr('cy', (d, i) => Math.sin((i / nodes.length) * Math.PI * 2) * (r + (i % 3) * 3))
        .attr('r', (d) => (d.alarm ? 3.4 : 1.6))
        .attr('fill', (d) => (d.alarm ? '#ff6a5a' : d.kind === 'agent' ? '#b29bff' : d.status === 'DEPARTING' ? '#f2b552' : d.status === 'INACTIVE' ? '#3d4b4c' : '#e9dcbc'))
        .style('filter', (d) => (d.alarm ? 'drop-shadow(0 0 4px #ff6a5a)' : null));
    };
    ring('ring-people', m.people, 96);
    ring('ring-agents', m.agents, 120);
  }

  // ---------- Render: departments ----------
  function renderDepts(g) {
    const sel = d3.select('#depts').selectAll('div.dept').data(state.model.depts, (d) => d.dept)
      .join((enter) => enter.append('div').attr('class', 'dept').style('opacity', 0)
        .on('click', (e, d) => chooseDept(d.dept, true))
        .call((s) => s.transition().delay((d, i) => (reduced ? 0 : 200 + i * 60)).duration(0).style('opacity', 1)));
    sel.classed('on', (d) => d.dept === state.dept)
      .style('left', `${g.deptX}px`).style('top', (d, i) => `${g.deptY(i)}px`)
      .html((d) => `<span class="n">${d.people}</span><span class="meta"><b>${esc(human(d.dept))}</b><span>${d.agents} agent${d.agents === 1 ? '' : 's'}</span></span>${d.alarms ? `<span class="alarm">${d.alarms}</span>` : ''}`);
  }

  // ---------- Render: fan ----------
  function itemShape(n) {
    if (n.kind === 'agent') return { svg: SHAPE.agent, color: n.alarm ? '#ff6a5a' : '#b29bff' };
    if (n.status === 'DEPARTING') return { svg: SHAPE.departing, color: '#f2b552' };
    if (n.status === 'INACTIVE') return { svg: SHAPE.inactive, color: '#5c6d6e' };
    return { svg: SHAPE.person, color: STORY.has(n.id) ? '#f6d898' : '#e9dcbc' };
  }
  function itemChips(n) {
    if (n.kind === 'agent') {
      const sponsor = state.model.byId.get(n.sponsor);
      return `${n.violation ? '<i class="bad">POLICY BREACH</i>' : n.orphan ? '<i class="bad">ORPHAN</i>' : '<i class="agent">SPONSORED</i>'}<i>${esc(sponsor ? sponsor.name.split(' ')[0] : 'no sponsor')}</i>${n.risk ? `<i>${esc(n.risk)}</i>` : ''}`;
    }
    return `<i>ACCESS ${n.access}</i>${n.agentIds.length ? `<i class="agent">${n.agentIds.length} AGENT${n.agentIds.length === 1 ? '' : 'S'}</i>` : ''}${n.status === 'DEPARTING' ? '<i class="warn">DEPARTING</i>' : n.status === 'INACTIVE' ? '<i>INACTIVE</i>' : ''}`;
  }

  function renderFan(g, previous) {
    const items = fanOrder(state.model, state.dept);
    state.items = items;
    state.offset = Math.max(0, Math.min(state.offset, Math.max(0, items.length - SLOTS)));
    const pos = new Map(items.map((n, i) => [n.id, slot(g, i - state.offset)]));
    const fresh = (n) => previous && n.alarm && !previous.byId.get(n.id)?.alarm;

    d3.select('#fan').selectAll('div.fan-item').data(items, (d) => d.id)
      .join(
        (enter) => enter.append('div').attr('class', 'fan-item')
          .style('opacity', 0)
          .style('transform', (d) => `translate(${g.origin.x}px, ${g.origin.y}px) translateY(-50%)`)
          .on('mouseenter', (e, d) => hover(d.id)).on('mouseleave', () => hover(null))
          .on('click', (e, d) => focus(d.id)),
        (update) => update,
        (exit) => exit.transition().duration(reduced ? 0 : 300).style('opacity', 0).remove(),
      )
      .each(function (d, i) {
        const el = this, p = pos.get(d.id), s = itemShape(d);
        el.className = `fan-item ${d.kind}${d.kind === 'person' && d.status === 'INACTIVE' ? ' inactive' : ''}${d.alarm ? ' hot' : ''}${state.focus === d.id ? ' sel' : ''}`;
        el.innerHTML = `<span class="dot" style="color:${s.color}"><svg viewBox="0 0 14 14">${s.svg}</svg></span>
          <span><span class="label">${esc(d.name)}</span><span class="sub">${itemChips(d)}</span></span>`;
        const apply = () => {
          el.style.transform = `translate(${p.x}px, ${p.y}px) translateY(-50%)`;
          el.style.opacity = p.opacity;
          el.style.pointerEvents = p.opacity ? 'auto' : 'none';
        };
        if (el.style.opacity === '0' && !reduced) setTimeout(apply, (state.first ? 500 : 60) + Math.min(i - state.offset, SLOTS) * 35);
        else apply();
        if (fresh(d)) { el.classList.add('flare'); setTimeout(() => el.classList.remove('flare'), 3000); }
      });

    const n = items.length;
    $('fan-hint').textContent = n > SLOTS ? `${state.offset + 1}–${Math.min(n, state.offset + SLOTS)} of ${n} · scroll to turn` : `${n} in ${human(state.dept)}`;
    $('fan-hint').style.left = `${g.ax + g.rx - 40}px`;
    $('fan-hint').style.bottom = '14px';
    renderLines(g, items, pos);
  }

  function renderLines(g, items, pos) {
    const deptLines = state.model.depts.map((d, i) => ({ id: `d:${d.dept}`, cls: `t-line dept${d.dept === state.dept ? ' on flowing' : ''}`,
      d: curve(g.orb.x + 48, g.orb.y, g.deptX, g.deptY(i), 0.5, 0.45), opacity: 1 }));
    const fanLines = items.map((n) => {
      const p = pos.get(n.id);
      return { id: `f:${n.id}`, node: n.id, cls: `t-line${n.alarm ? ' hot' : ''}`, d: curve(g.origin.x, g.origin.y, p.x - 8, p.y), opacity: p.opacity };
    });
    const lines = d3.select('#lines').selectAll('path').data([...deptLines, ...fanLines], (d) => d.id)
      .join(
        (enter) => enter.append('path').attr('d', (d) => d.d).style('opacity', 0)
          .each(function (d) {
            if (reduced) return;
            const len = this.getTotalLength();
            d3.select(this).attr('stroke-dasharray', `${len} ${len}`).attr('stroke-dashoffset', len)
              .transition().delay(state.first ? (d.node ? 450 : 150) + Math.random() * 300 : 80).duration(800).ease(d3.easeCubicInOut)
              .attr('stroke-dashoffset', 0).on('end', function () { d3.select(this).attr('stroke-dasharray', null).attr('stroke-dashoffset', null).attr('d', (x) => x.d); });
          }),
        (update) => update,
        (exit) => exit.transition().duration(reduced ? 0 : 300).style('opacity', 0).remove(),
      );
    lines.attr('class', (d) => d.cls);
    lines.filter(function () { return !this.__transition; }).transition().duration(reduced ? 0 : 650).ease(d3.easeCubicOut)
      .attr('d', (d) => d.d).style('opacity', (d) => d.opacity);
    lines.filter(function () { return this.__transition; }).attr('d', (d) => d.d).style('opacity', (d) => d.opacity);
    applyHover();
  }

  function render(previous) {
    if (!state.model) return;
    const g = geometry();
    renderOrb(g);
    renderDepts(g);
    renderFan(g, previous);
    $('find').style.left = `${Math.max(16, g.right / 2 - 190)}px`;
    state.first = false;
  }

  // ---------- Interaction ----------
  function chooseDept(dept, showPanel) {
    if (state.dept !== dept) { state.dept = dept; state.offset = 0; }
    if (showPanel) state.focus = `dept:${dept}`;
    render();
    renderPanel();
  }
  function focus(id) {
    const n = state.model.byId.get(id);
    if (!n) return;
    if (n.dept !== state.dept) { state.dept = n.dept; state.offset = 0; }
    const index = fanOrder(state.model, n.dept).findIndex((x) => x.id === id);
    if (index < state.offset || index >= state.offset + SLOTS) state.offset = Math.max(0, index - Math.floor(SLOTS / 2));
    state.focus = id;
    render();
    renderPanel();
  }
  function hover(id) { state.hovered = id; applyHover(); }
  function applyHover() {
    const id = state.hovered;
    const n = id && state.model?.byId.get(id);
    const related = new Set();
    if (n) {
      related.add(n.id);
      if (n.kind === 'agent') related.add(n.sponsor);
      else n.agentIds.forEach((a) => related.add(a));
    }
    d3.selectAll('#fan .fan-item').classed('dimmed', (d) => Boolean(n) && !related.has(d.id));
    d3.selectAll('#lines path').classed('lit', (d) => Boolean(n) && related.has(d.node)).classed('dim', (d) => Boolean(n) && d.node && !related.has(d.node));
  }
  $('fan').addEventListener('wheel', (e) => {
    if (!state.items || state.items.length <= SLOTS) return;
    e.preventDefault();
    const next = Math.max(0, Math.min(state.items.length - SLOTS, state.offset + Math.sign(e.deltaY) * 2));
    if (next !== state.offset) { state.offset = next; render(); }
  }, { passive: false });
  $('orb').addEventListener('click', () => { state.focus = 'company'; render(); renderPanel(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { state.focus = 'company'; render(); renderPanel(); } });
  $('find').addEventListener('submit', (e) => {
    e.preventDefault();
    const q = $('find-input').value.trim().toLowerCase();
    const n = [...state.model.byId.values()].find((x) => x.name.toLowerCase() === q) || [...state.model.byId.values()].find((x) => x.name.toLowerCase().includes(q));
    if (!n) { toast('Nobody by that name.', 'error'); return; }
    focus(n.id);
    flare(n.id);
  });
  function flare(id) {
    setTimeout(() => {
      const el = [...document.querySelectorAll('#fan .fan-item')].find((x) => d3.select(x).datum()?.id === id);
      if (el) { el.classList.add('flare'); setTimeout(() => el.classList.remove('flare'), 3000); }
    }, 700);
  }

  // ---------- Insight panel ----------
  function renderPanel() {
    if (!state.model) return;
    const sig = JSON.stringify([state.focus, state.signature?.length, state.kpis, state.signature]);
    if (sig === state.panelSig) return;
    state.panelSig = sig;
    const el = $('insight');
    const f = state.focus;
    if (f === 'company') el.innerHTML = companyPanel();
    else if (f.startsWith('dept:')) el.innerHTML = deptPanel(f.slice(5));
    else el.innerHTML = nodePanel(state.model.byId.get(f));
    el.querySelectorAll('[data-focus]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); focus(a.dataset.focus); flare(a.dataset.focus); }));
    el.querySelectorAll('[data-dept]').forEach((a) => a.addEventListener('click', () => chooseDept(a.dataset.dept, true)));
    el.querySelector('[data-close]')?.addEventListener('click', () => { state.focus = 'company'; render(); renderPanel(); });
    el.querySelectorAll('[data-start-arif]').forEach((b) => b.addEventListener('click', startArif));
    el.querySelectorAll('[data-count]').forEach((v) => LO.countUp(v, v.dataset.count));
  }
  const tile = (icon, value, label, tone = '') => `<div class="tile ${tone}">${ico(icon)}<div class="v" ${value !== null && /^\d/.test(String(value)) ? `data-count="${esc(value)}"` : ''}>${value === null ? '<span class="faint" style="font-size:14px">Not yet</span>' : esc(value)}</div><div class="l">${label}</div></div>`;
  const close = '<button class="btn small icon close" data-close aria-label="Back to overview">✕</button>';
  const alarmList = (agents) => agents.length ? `<div><h3 style="margin-bottom:8px">Needs an owner</h3><div class="stack" style="gap:8px">${agents.map((a) => `
    <a class="item highlight" href="#" data-focus="${esc(a.id)}" style="display:flex;align-items:center;gap:10px;color:inherit;text-decoration:none;padding:10px 12px">
      <span style="color:var(--bad);width:14px;height:14px"><svg viewBox="0 0 14 14">${SHAPE.agent}</svg></span>
      <span style="flex:1;min-width:0"><b style="font-weight:550">${esc(a.name)}</b><span class="faint" style="display:block">${a.violation ? 'breaks the current policy' : a.reasons.map(human).join(', ')}</span></span></a>`).join('')}</div></div>` : '';

  function companyPanel() {
    const k = state.kpis || {};
    const m = state.model;
    const off = k.latest_offboarding;
    const bars = m.depts.filter((d) => d.agents).map((d) => `<i class="${d.coverage < 80 ? 'low' : ''}" title="${esc(human(d.dept))}: ${d.coverage}%" style="height:${Math.max(10, d.coverage * 0.42)}px"></i>`).join('');
    return `
      <div class="eyebrow">${ico('pulse')}Workforce health <span class="spacer"></span><span class="badge ok live">live</span></div>
      <h2>Nexora Labs<small>People and AI agents, and who sponsors which agent</small></h2>
      <div class="hero-metric ${k.agents_with_active_sponsor_pct < 90 ? 'hot' : ''}">
        <div class="faint" style="color:var(--text-2)">Agents with an active sponsor</div>
        <div class="row"><div class="big" ${k.agents_with_active_sponsor_pct != null ? `data-count="${k.agents_with_active_sponsor_pct}%"` : ''}>${pct(k.agents_with_active_sponsor_pct) ?? '—'}</div>
          <div class="faint" style="margin-bottom:4px">${k.agents ?? ''} agents</div><div class="bars" title="Sponsor coverage by department">${bars}</div></div>
      </div>
      <div class="tiles">
        ${tile('alert', k.orphan_agents ?? null, 'Orphan agents<br>sponsor gone or access expired', k.orphan_agents ? 'bad' : 'ok')}
        ${tile('key', pct(k.human_access_with_active_owner_pct), 'Human access<br>with an active owner')}
        ${tile('clock', k.agents != null ? `${k.agent_access_time_limited} / ${k.agent_access_time_limited + k.agent_access_standing}` : null, 'Agent access<br>time-limited')}
        ${tile('check', off ? `${off.minutes_to_close_all_access} min` : null, 'Termination to<br>all access closed', off ? 'ok' : '')}
      </div>
      ${tile('doc', pct(k.with_policy_reason_pct), `Changes with a policy reason · ${k.access_changes_through_livingops ?? 0} via LivingOps`)}
      ${alarmList(m.agents.filter((a) => a.alarm))}
      <button class="btn primary" data-start-arif style="width:100%">Start Arif Hossain's offboarding</button>`;
  }

  function deptPanel(dept) {
    const d = state.model.depts.find((x) => x.dept === dept);
    if (!d) return companyPanel();
    return `${close}
      <div class="eyebrow">${ico('team')}Department</div>
      <h2>${esc(human(dept))}<small>${d.people} people · ${d.agents} agents</small></h2>
      <div class="hero-metric ${d.coverage < 100 ? 'hot' : ''}"><div class="faint" style="color:var(--text-2)">Agents with an active sponsor</div>
        <div class="row"><div class="big" data-count="${d.coverage}%">${d.coverage}%</div></div></div>
      <div class="tiles">
        ${tile('person', String(d.people), 'People')}${tile('agent', String(d.agents), 'AI agents')}
        ${tile('alert', String(d.departing), 'Departing', d.departing ? '' : 'ok')}${tile('shield', String(d.alarms), 'Need an owner', d.alarms ? 'bad' : 'ok')}
      </div>
      ${alarmList(d.members.filter((n) => n.alarm))}`;
  }

  function nodePanel(n) {
    if (!n) return companyPanel();
    if (n.kind === 'agent') {
      const sponsor = state.model.byId.get(n.sponsor);
      return `${close}
        <div class="eyebrow" style="color:var(--agent)">${ico('agent')}AI agent</div>
        <h2>${esc(n.name)}<small class="mono" style="font-size:12px">${esc(n.id)}</small></h2>
        <div class="chips">${badge(n.status)}${n.risk ? badge(n.risk, `${n.risk} risk`) : ''}${n.violation ? badge('VIOLATION', 'policy breach') : n.orphan ? badge('ORPHAN', 'orphan') : badge('ACTIVE', 'sponsored')}</div>
        ${n.alarm ? `<div class="hero-metric hot"><div class="faint" style="color:var(--bad)">Why it needs an owner</div>
          <div style="margin-top:6px;font-size:14px">${n.violation ? 'It breaks the current access policy.' : ''} ${n.reasons.map((r) => esc(human(r))).join('; ')}</div></div>` : ''}
        <div class="tiles">
          ${tile('person', sponsor ? sponsor.name : 'none', `Sponsor${sponsor ? ` · ${esc(human(sponsor.status))}` : ''}`, sponsor && sponsor.status !== 'ACTIVE' ? 'bad' : '')}
          ${tile('team', human(n.dept), 'Department')}
        </div>
        <div class="btn-row">${sponsor ? `<a class="btn" href="#" data-focus="${sponsor.id}">Show sponsor</a>` : ''}${n.violation ? '<a class="btn" href="guardian.html">Open Policy Guardian</a>' : ''}</div>`;
    }
    const agents = n.agentIds.map((id) => state.model.byId.get(id)).filter(Boolean);
    return `${close}
      <div class="eyebrow">${ico('person')}Person</div>
      <h2>${esc(n.name)}<small>${esc(n.title || '—')} · ${esc(human(n.dept))}</small></h2>
      <div class="chips">${badge(n.status)}${n.role ? `<span class="badge idle">${esc(human(n.role))}</span>` : ''}</div>
      <div class="tiles">
        ${tile('key', String(n.access), 'Live access<br>email, GitHub, laptop, training')}
        ${tile('agent', String(agents.length), 'AI agents<br>sponsored', agents.some((a) => a.alarm) ? 'bad' : '')}
      </div>
      ${agents.length ? `<div><h3 style="margin-bottom:8px">Sponsored agents</h3><div class="stack" style="gap:8px">${agents.map((a) => `
        <a class="item ${a.alarm ? 'highlight' : ''}" href="#" data-focus="${esc(a.id)}" style="display:flex;align-items:center;gap:10px;color:inherit;text-decoration:none;padding:10px 12px">
          <span style="color:${a.alarm ? 'var(--bad)' : 'var(--agent)'};width:14px;height:14px"><svg viewBox="0 0 14 14">${SHAPE.agent}</svg></span>
          <span style="flex:1">${esc(a.name)}</span>${a.alarm ? badge('ORPHAN', 'needs owner') : ''}</a>`).join('')}</div></div>` : ''}
      ${n.id === PEOPLE.arif.id ? '<button class="btn primary" data-start-arif style="width:100%">Start offboarding</button>' : ''}`;
  }

  // ---------- Data ----------
  async function loadGraph() {
    const graph = await api('/workforce/graph');
    const signature = JSON.stringify(graph);
    if (signature === state.signature) return;
    const previous = state.model;
    state.signature = signature;
    state.model = buildModel(graph);
    if (!state.dept || !state.model.depts.some((d) => d.dept === state.dept)) {
      state.dept = (state.model.depts.find((d) => d.alarms) || state.model.depts[0]).dept;
    }
    if (state.highlight && state.model.byId.has(state.highlight)) {
      const id = state.highlight; state.highlight = null;
      focus(id); flare(id);
    } else {
      render(previous);
      renderPanel();
    }
    $('find-list').innerHTML = [...state.model.byId.values()].map((n) => `<option value="${esc(n.name)}">`).join('');
    const deptSelect = $('dept-filter');
    if (deptSelect.options.length === 1) deptSelect.insertAdjacentHTML('beforeend', state.model.depts.map((d) => `<option value="${esc(d.dept)}">${esc(human(d.dept))}</option>`).join(''));
    renderRows();
  }
  async function loadKpis() {
    state.kpis = await api('/dashboard/kpis');
    $('kpi-note').textContent = state.kpis.label;
    renderPanel();
  }
  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => render(), 150); });

  // ---------- Table ----------
  function renderRows() {
    if (!state.model) return;
    const q = $('search').value.trim().toLowerCase();
    const dept = $('dept-filter').value;
    const filter = $('filter').value;
    const rows = [...state.model.byId.values()].filter((n) => {
      if (dept && n.dept !== dept) return false;
      if (filter === 'orphan' && !(n.kind === 'agent' && n.orphan)) return false;
      if (filter === 'violation' && !(n.kind === 'agent' && n.violation)) return false;
      if (filter === 'agents' && n.kind !== 'agent') return false;
      if (['DEPARTING', 'INACTIVE'].includes(filter) && !(n.kind === 'person' && n.status === filter)) return false;
      return !q || `${n.name} ${n.title || ''} ${n.id}`.toLowerCase().includes(q);
    }).sort((a, b) => (b.alarm ? 1 : 0) - (a.alarm ? 1 : 0) || a.name.localeCompare(b.name)).slice(0, 150);
    $('rows').innerHTML = rows.map((n) => `
      <tr class="clickable ${n.id === state.focus ? 'selected' : ''}" data-id="${esc(n.id)}">
        <td><b style="font-weight:550">${esc(n.name)}</b></td>
        <td>${n.kind === 'agent' ? '<span class="badge agent">agent</span>' : `<span class="muted">${esc(n.title || 'person')}</span>`}</td>
        <td class="muted">${esc(human(n.dept))}</td>
        <td>${n.kind === 'agent' ? (n.violation ? badge('VIOLATION', 'policy breach') : n.orphan ? badge('ORPHAN', 'orphan') : badge('ACTIVE', 'sponsored')) : badge(n.status)}</td>
        <td>${n.kind === 'agent' ? esc(state.model.byId.get(n.sponsor)?.name || '—') : `<span class="num">${n.access}</span>`}</td>
      </tr>`).join('') || '<tr><td colspan="5"><div class="empty"><b>No match</b>Try another name or clear the filters.</div></td></tr>';
    document.querySelectorAll('#rows tr[data-id]').forEach((tr) => tr.addEventListener('click', () => {
      focus(tr.dataset.id); flare(tr.dataset.id);
      stage.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
    }));
  }
  ['search', 'dept-filter', 'filter'].forEach((id) => $(id).addEventListener('input', renderRows));

  // ---------- Cases and evaluation ----------
  async function loadCases() {
    const cases = await api('/cases?limit=6');
    $('cases').innerHTML = cases.length ? cases.map((c) => `
      <a class="item" href="workspace.html?case=${c.id}" style="display:flex;gap:12px;align-items:center;color:inherit;text-decoration:none">
        <div style="flex:1;min-width:0"><b style="font-weight:550">${esc(c.subject_name || '—')}</b>
          <div class="faint">${esc(human(c.case_type))}${c.origin ? ' · ' + esc(human(c.origin)) : ''}${c.tier ? ' · tier ' + esc(c.tier) : ''} · ${timeAgo(c.created_at)}</div></div>
        ${badge(c.status)}</a>`).join('') : '<div class="empty"><b>No cases yet</b>Start Arif Hossain\'s offboarding to begin the story.</div>';
  }
  async function loadEvaluation() {
    try {
      const e = await api('/evaluation/latest');
      $('eval-when').textContent = `measured ${timeAgo(e.generated_at)} · ${e.demo_mode}`;
      const rows = [
        ['Plans valid first pass', e.plan_generation.first_pass_valid_pct, e.plan_generation.n],
        ['Plans valid after one repair', e.plan_generation.valid_after_repair_pct, e.plan_generation.n],
        ['Steps citing policy evidence', e.evidence.steps_with_policy_evidence_pct, e.evidence.n],
        ['Retrieval recall@1', e.retrieval.recall_at_1_pct, e.retrieval.n],
        ['Guardian impact recall', e.guardian.recall_pct, e.guardian.n_scenarios],
        ['Actions verified', e.execution.verified_completion_pct, e.execution.n],
      ];
      const bar = (v) => (v === null ? '' : `<div class="bar" style="margin-top:6px"><i style="width:${v}%;background:${v >= 90 ? 'var(--ok)' : v >= 70 ? 'var(--warn)' : 'var(--bad)'}"></i></div>`);
      $('eval').innerHTML = `<table class="data"><tbody>${rows.map(([l, v, n]) => `
        <tr><td>${esc(l)}${bar(v)}</td><td style="text-align:right"><b class="num">${v === null ? '—' : v + '%'}</b></td><td class="faint num">n=${n}</td></tr>`).join('')}
        <tr><td>Guardian false impacts</td><td style="text-align:right"><b class="num">${e.guardian.false_impacts}</b></td><td class="faint">seeded</td></tr></tbody></table>`;
    } catch {
      $('eval').innerHTML = '<div class="empty"><b>No evaluation yet</b>Run <code>python -m app.scripts.run_evaluation</code> after a rehearsal.</div>';
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
  document.querySelectorAll('[data-start-arif]').forEach((b) => b.addEventListener('click', startArif));

  loadKpis(); loadEvaluation();
  poll(loadGraph, 3000);
  poll(loadCases, 5000);
  setInterval(loadKpis, 10000);
})();
