/* Dashboard: KPI row, live workforce map (D3), recent cases, evaluation, table.
   Map: one zone per department, people as circles (size = live access),
   agents as hexagons next to their sponsor, sponsor links as curved arcs.
   The layout is solved once up front, so the map appears composed and calm;
   motion is kept for meaning: entry, hover focus, sponsor change, new alarm. */
(function () {
  const { api, esc, badge, toast, timeAgo, human, poll, actingAs, PEOPLE } = LO;
  const page = LO.shell({
    active: 'index.html',
    title: 'Workforce map',
    subtitle: 'People and AI agents of Nexora Labs, and who sponsors which agent',
  });

  const shape = {
    person: '<circle cx="6" cy="6" r="4.5" fill="var(--person)"/>',
    agent: '<polygon points="3,1 9,1 12,6 9,11 3,11 0,6" fill="var(--agent)"/>',
    departing: '<polygon points="6,1 11.5,11 0.5,11" fill="var(--warn)"/>',
    inactive: '<rect x="1.5" y="1.5" width="9" height="9" rx="1.5" fill="var(--idle)"/>',
    orphan: '<polygon points="3,1 9,1 12,6 9,11 3,11 0,6" fill="none" stroke="var(--bad)" stroke-width="1.6"/>',
  };
  const legend = (key, label) => `<span><svg viewBox="0 0 12 12">${shape[key]}</svg>${label}</span>`;

  page.innerHTML = `
    <section class="kpis" id="kpis">${'<div class="kpi"><div class="label skeleton" style="width:70%">&nbsp;</div><div class="value skeleton" style="width:40%">&nbsp;</div><div class="sub skeleton" style="width:55%">&nbsp;</div></div>'.repeat(6)}</section>
    <p class="kpi-note" id="kpi-note"></p>
    <section class="card map-card">
      <div class="map-toolbar">
        <h2>Nexora Labs</h2>
        <div class="legend">
          ${legend('person', 'person')}${legend('agent', 'AI agent')}${legend('departing', 'departing')}
          ${legend('inactive', 'inactive')}${legend('orphan', 'orphan or policy breach')}
          <span><svg viewBox="0 0 22 12" style="width:22px"><path d="M1 10 Q11 0 21 10" fill="none" stroke="var(--agent)" stroke-dasharray="3 3"/></svg>sponsor</span>
        </div>
        <span class="spacer"></span>
        <span class="faint num" id="map-count"></span>
      </div>
      <div class="map-stage" id="stage">
        <svg id="map" role="img" aria-label="Workforce map of people and AI agents"></svg>
        <div class="map-tip" id="tip"></div>
        <div class="map-hint">Hover to trace, click for details, scroll to zoom</div>
        <div class="map-zoom">
          <button id="zoom-in" aria-label="Zoom in">+</button>
          <button id="zoom-out" aria-label="Zoom out">−</button>
          <button id="zoom-reset" aria-label="Reset view">⟲</button>
        </div>
        <aside class="drawer" id="drawer" aria-live="polite"></aside>
      </div>
    </section>
    <section class="grid-2">
      <div class="card">
        <div class="card-head"><h2>Recent cases</h2><span class="spacer"></span>
          <button class="btn primary" id="start-arif">Start Arif Hossain's offboarding</button></div>
        <div id="cases" class="stack"><div class="item skeleton" style="height:52px"></div><div class="item skeleton" style="height:52px"></div></div>
      </div>
      <div class="card" id="eval-card">
        <div class="card-head"><h2>Evaluation</h2><span class="spacer"></span><span class="faint" id="eval-when"></span></div>
        <div id="eval"><div class="skeleton" style="height:180px"></div></div>
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
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- KPIs ----------
  async function loadKpis() {
    const k = await api('/dashboard/kpis');
    const off = k.latest_offboarding;
    const tiles = [
      { label: 'Termination → all access closed', value: off ? `${off.minutes_to_close_all_access} min` : null,
        sub: off ? `${off.automated_steps} steps, ${off.human_approvals} approval(s)` : 'Measured after the first offboarding', tone: off ? 'ok' : '' },
      { label: 'Agents with an active sponsor', value: pct(k.agents_with_active_sponsor_pct), sub: `${k.agents} agents` },
      { label: 'Orphan agents', value: String(k.orphan_agents), sub: 'sponsor gone or access expired', tone: k.orphan_agents ? 'bad' : 'ok' },
      { label: 'Human access with an active owner', value: pct(k.human_access_with_active_owner_pct), sub: 'email, GitHub, laptop, training' },
      { label: 'Changes with a policy reason', value: pct(k.with_policy_reason_pct),
        sub: k.access_changes_through_livingops ? `${k.access_changes_through_livingops} changes via LivingOps` : 'Measured once LivingOps makes a change' },
      { label: 'Agent access time-limited', value: `${k.agent_access_time_limited} / ${k.agent_access_time_limited + k.agent_access_standing}`, sub: 'vs standing access' },
    ];
    const box = document.getElementById('kpis');
    if (!box.querySelector('[data-kpi]')) {
      box.innerHTML = tiles.map((t, i) => `<div class="kpi" data-kpi="${i}"><div class="label"></div><div class="value"></div><div class="sub"></div></div>`).join('');
    }
    tiles.forEach((t, i) => {
      const el = box.querySelector(`[data-kpi="${i}"]`);
      el.className = `kpi ${t.tone || ''}`;
      el.querySelector('.label').textContent = t.label;
      el.querySelector('.sub').textContent = t.sub;
      const value = el.querySelector('.value');
      value.classList.toggle('none', t.value === null);
      if (t.value === null) { value.textContent = 'Not yet'; value.dataset.shown = ''; } else LO.countUp(value, t.value);
    });
    document.getElementById('kpi-note').textContent = k.label;
  }
  const pct = (v) => (v === null || v === undefined ? null : `${v}%`);

  // ---------- Map: model ----------
  const svg = d3.select('#map');
  const viewport = svg.append('g');
  const zoneLayer = viewport.append('g');
  const linkLayer = viewport.append('g');
  const nodeLayer = viewport.append('g');
  const fxLayer = viewport.append('g');
  const labelLayer = viewport.append('g');
  const zoom = d3.zoom().scaleExtent([0.6, 5]).on('zoom', (e) => {
    viewport.attr('transform', e.transform);
    labelLayer.selectAll('text').attr('font-size', 10.5 / Math.sqrt(e.transform.k));
  });
  svg.call(zoom).on('dblclick.zoom', null);
  svg.on('click', (e) => { if (e.target === svg.node()) clearSelection(); });

  const positions = new Map();
  let firstRender = true;
  let size = { width: 0, height: 0 };

  const hexagon = (r) => `M${d3.range(6).map((i) => [r * Math.cos((Math.PI / 3) * i), r * Math.sin((Math.PI / 3) * i)]).join('L')}Z`;
  const triangle = (r) => `M0,${-r * 1.15}L${r * 1.05},${r * 0.75}L${-r * 1.05},${r * 0.75}Z`;
  const square = (r) => `M${-r * 0.85},${-r * 0.85}h${r * 1.7}v${r * 1.7}h${-r * 1.7}Z`;
  const circle = (r) => d3.symbol(d3.symbolCircle, Math.PI * r * r)();

  function shapePath(n) {
    if (n.kind === 'agent') return hexagon(n.r);
    if (n.status === 'DEPARTING') return triangle(n.r);
    if (n.status === 'INACTIVE') return square(n.r);
    return circle(n.r);
  }
  function nodeFill(n) {
    if (n.kind === 'agent') return n.alarm ? 'var(--bad)' : 'var(--agent)';
    return { DEPARTING: 'var(--warn)', INACTIVE: 'var(--idle)', CANDIDATE: 'var(--accent)' }[n.status] || 'var(--person)';
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
      r: 3.6 + Math.sqrt(p.access_count || 0) * 1.7,
      agents: agentsBySponsor.get(p.id) || [],
    }));
    const byId = new Map(people.map((p) => [p.id, p]));
    const agents = graph.agents.map((a) => ({
      id: a.resource_key, kind: 'agent', name: a.agent_name || a.resource_key, status: a.status,
      dept: byId.get(a.sponsor_id)?.dept || a.department || 'OTHER', sponsor: a.sponsor_id,
      risk: a.risk_tier, orphan: a.orphan, reasons: a.orphan_reasons || [], violation: a.policy_violation,
      alarm: a.orphan || a.policy_violation, r: 6,
    }));
    const nodes = [...people, ...agents];
    const ids = new Set(nodes.map((n) => n.id));
    const links = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ id: `${e.kind}:${e.source}>${e.target}`, source: e.source, target: e.target, kind: e.kind }));
    const neighbours = new Map(nodes.map((n) => [n.id, new Set([n.id])]));
    links.forEach((l) => { neighbours.get(l.source).add(l.target); neighbours.get(l.target).add(l.source); });
    return { nodes, links, people, agents, byId: new Map(nodes.map((n) => [n.id, n])), neighbours };
  }

  // Department zones as a squarified treemap: bigger teams get more room.
  function layoutZones(nodes, width, height) {
    const counts = d3.rollup(nodes, (v) => v.length, (n) => n.dept);
    const root = d3.hierarchy({ children: [...counts].map(([dept, count]) => ({ dept, count })) })
      .sum((d) => (d.count ? d.count + 10 : 0))
      .sort((a, b) => b.value - a.value || a.data.dept.localeCompare(b.data.dept));
    d3.treemap().tile(d3.treemapSquarify.ratio(1.2)).size([width, height]).paddingInner(12).paddingOuter(14)(root);
    const zones = new Map();
    root.leaves().forEach((leaf, i) => zones.set(leaf.data.dept, {
      dept: leaf.data.dept, count: leaf.data.count, i,
      x: leaf.x0, y: leaf.y0, w: leaf.x1 - leaf.x0, h: leaf.y1 - leaf.y0,
    }));
    return zones;
  }

  // Lift labels that would overlap a label below them.
  function placeLabels(labelled) {
    const boxes = labelled.map((n) => ({ n, w: n.labelText.length * 6 + 6, x: n.x, y: n.y - n.r - 7 }))
      .sort((a, b) => b.y - a.y);
    boxes.forEach((box, i) => {
      for (let pass = 0; pass < 4; pass += 1) {
        const hit = boxes.slice(0, i).find((o) => Math.abs(o.x - box.x) < (o.w + box.w) / 2 && Math.abs(o.y - box.y) < 15);
        if (!hit) break;
        box.y = hit.y - 15;
      }
      box.n.ly = box.y;
    });
  }

  function solveLayout(model, zones, warm) {
    model.nodes.forEach((n) => {
      const z = zones.get(n.dept);
      const p = positions.get(n.id);
      if (p) { n.x = p.x; n.y = p.y; return; }
      const sponsor = n.kind === 'agent' && positions.get(n.sponsor);
      n.x = sponsor ? sponsor.x + 8 : z.x + z.w / 2 + (Math.random() - 0.5) * z.w * 0.5;
      n.y = sponsor ? sponsor.y + 8 : z.y + z.h / 2 + (Math.random() - 0.5) * z.h * 0.4;
    });
    const sim = d3.forceSimulation(model.nodes)
      .force('link', d3.forceLink(model.links.map((l) => ({ ...l }))).id((d) => d.id)
        .distance((d) => (d.kind === 'SPONSOR' ? 16 : 26)).strength((d) => (d.kind === 'SPONSOR' ? 0.8 : 0.08)))
      .force('charge', d3.forceManyBody().strength((d) => (d.kind === 'agent' ? -10 : -38)).distanceMax(160))
      .force('collide', d3.forceCollide().radius((d) => d.r + 2.5).iterations(2))
      .force('x', d3.forceX((d) => { const z = zones.get(d.dept); return z.x + z.w / 2; }).strength(0.035))
      .force('y', d3.forceY((d) => { const z = zones.get(d.dept); return z.y + z.h / 2 + 8; }).strength(0.05))
      .stop();
    sim.alpha(warm ? 0.3 : 1);
    const ticks = warm ? 80 : 320;
    for (let i = 0; i < ticks; i += 1) {
      sim.tick();
      model.nodes.forEach((n) => {   // keep every node inside its own zone
        const z = zones.get(n.dept);
        n.x = Math.max(z.x + n.r + 8, Math.min(z.x + z.w - n.r - 8, n.x));
        n.y = Math.max(z.y + n.r + 26, Math.min(z.y + z.h - n.r - 8, n.y));
      });
    }
    model.nodes.forEach((n) => positions.set(n.id, { x: n.x, y: n.y }));
  }

  // Sponsor links bow a little, so crossing links read as separate arcs.
  function arc(l, model) {
    const s = model.byId.get(l.source), t = model.byId.get(l.target);
    if (l.kind !== 'SPONSOR') return `M${s.x},${s.y}L${t.x},${t.y}`;
    const dx = t.x - s.x, dy = t.y - s.y, dist = Math.hypot(dx, dy) || 1;
    const bend = Math.min(40, dist * 0.35);
    return `M${s.x},${s.y}Q${(s.x + t.x) / 2 - (dy / dist) * bend},${(s.y + t.y) / 2 + (dx / dist) * bend} ${t.x},${t.y}`;
  }

  // ---------- Map: render ----------
  function renderMap(graph) {
    const el = document.getElementById('map');
    const width = el.clientWidth || 1100, height = el.clientHeight || 600;
    if (width !== size.width || height !== size.height) { positions.clear(); size = { width, height }; firstRender = true; }
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    const previous = state.model;
    const model = buildModel(graph);
    const zones = layoutZones(model.nodes, width, height);
    solveLayout(model, zones, !firstRender);
    const t = svg.transition().duration(reduced ? 0 : 700).ease(d3.easeCubicOut);
    const entering = firstRender;

    // Zones
    const zone = zoneLayer.selectAll('g.zone').data([...zones.values()], (d) => d.dept)
      .join((enter) => {
        const g = enter.append('g').attr('class', 'zone').style('opacity', 0);
        g.append('rect').attr('rx', 14);
        g.append('text').attr('class', 'zone-name');
        g.append('text').attr('class', 'zone-count').attr('text-anchor', 'end');
        g.transition().delay((d) => (reduced ? 0 : d.i * 70)).duration(500).style('opacity', 1);
        return g;
      });
    zone.select('rect').attr('x', (d) => d.x).attr('y', (d) => d.y).attr('width', (d) => d.w).attr('height', (d) => d.h);
    zone.select('.zone-name').attr('x', (d) => d.x + 14).attr('y', (d) => d.y + 20).text((d) => human(d.dept));
    zone.select('.zone-count').attr('x', (d) => d.x + d.w - 14).attr('y', (d) => d.y + 20).text((d) => {
      const members = model.nodes.filter((n) => n.dept === d.dept);
      const agents = members.filter((n) => n.kind === 'agent').length;
      return `${members.length - agents} people · ${agents} agents`;
    });

    // Links: sponsor arcs draw in; a moved sponsor link retracts and redraws.
    const link = linkLayer.selectAll('path').data(model.links, (d) => d.id)
      .join(
        (enter) => enter.append('path')
          .attr('class', (d) => (d.kind === 'SPONSOR' ? 'edge-sponsor' : 'edge-manager'))
          .attr('d', (d) => arc(d, model))
          .each(function (d) {
            if (d.kind !== 'SPONSOR' || reduced) return;
            const len = this.getTotalLength();
            d3.select(this).style('animation', 'none').attr('stroke-dasharray', `${len} ${len}`).attr('stroke-dashoffset', len)
              .transition().delay(entering ? 900 + Math.random() * 500 : 250).duration(entering ? 700 : 900).ease(d3.easeCubicInOut)
              .attr('stroke-dashoffset', 0)
              .on('end', function () { d3.select(this).attr('stroke-dasharray', null).attr('stroke-dashoffset', null).style('animation', null); });
          }),
        (update) => update,
        (exit) => exit.each(function () {
          if (reduced) { this.remove(); return; }
          const len = this.getTotalLength();
          d3.select(this).style('animation', 'none').attr('stroke-dasharray', `${len} ${len}`).attr('stroke-dashoffset', 0)
            .transition().duration(600).ease(d3.easeCubicIn).attr('stroke-dashoffset', len).style('opacity', 0).remove();
        }),
      );
    link.filter(function () { return !this.__transition; }).transition(t).attr('d', (d) => arc(d, model));
    link.classed('alarm', (d) => d.kind === 'SPONSOR' && model.byId.get(d.target)?.alarm);

    // Nodes
    const node = nodeLayer.selectAll('g.node').data(model.nodes, (d) => d.id)
      .join((enter) => {
        const g = enter.append('g').attr('class', 'node').attr('transform', (d) => `translate(${d.x},${d.y})`);
        g.append('circle').attr('class', 'ring');
        g.append('circle').attr('class', 'halo');
        g.append('path').attr('class', 'shape').attr('stroke', 'var(--bg)').attr('stroke-width', 1.2);
        g.on('mouseenter', (e, d) => hover(d, e)).on('mousemove', (e) => moveTip(e)).on('mouseleave', () => hover(null))
          .on('click', (e, d) => { e.stopPropagation(); select(d.id, true); });
        if (!reduced) {
          g.select('.shape').attr('transform', 'scale(0)')
            .transition().delay((d) => (entering ? 250 + zones.get(d.dept).i * 70 + Math.random() * 350 : 0)).duration(500)
            .ease(d3.easeBackOut.overshoot(1.6)).attr('transform', 'scale(1)')
            .on('end', function () { d3.select(this).attr('transform', null); });
        }
        return g;
      });
    node.transition(t).attr('transform', (d) => `translate(${d.x},${d.y})`);
    node.classed('inactive', (d) => d.kind === 'person' && d.status === 'INACTIVE')
      .classed('selected', (d) => d.id === state.selected);
    node.select('path.shape').attr('d', shapePath).style('fill', nodeFill);
    node.select('circle.halo').attr('r', (d) => d.r * 1.45 + 3.5);
    node.select('circle.ring')
      .attr('r', (d) => d.r + 4)
      .attr('class', (d) => `ring ${d.alarm ? 'bad breathe' : d.status === 'DEPARTING' && d.kind === 'person' ? 'warn' : ''}`)
      .style('display', (d) => (d.alarm || (d.kind === 'person' && d.status === 'DEPARTING') ? null : 'none'));

    // Something just turned red (new orphan, new policy breach): one shockwave.
    if (previous) {
      model.nodes.filter((n) => n.alarm && !previous.byId.get(n.id)?.alarm).forEach((n) => shock(n, 'shock'));
      model.nodes.filter((n) => n.kind === 'person' && n.status !== previous.byId.get(n.id)?.status && previous.byId.has(n.id))
        .forEach((n) => shock(n, n.status === 'INACTIVE' ? 'verified-pop' : 'shock'));
    }

    // Labels: story characters, alarmed agents and the selection.
    const labelled = model.nodes.filter((n) => STORY.has(n.id) || (n.kind === 'agent' && n.alarm) || n.id === state.selected);
    labelled.forEach((n) => { n.labelText = n.kind === 'agent' ? n.name : n.name.split(' ')[0]; });
    placeLabels(labelled);
    labelLayer.selectAll('text.node-label').data(labelled, (d) => d.id)
      .join((enter) => enter.append('text').attr('class', 'node-label').attr('text-anchor', 'middle')
        .attr('x', (d) => d.x).attr('y', (d) => d.ly).style('opacity', 0)
        .call((s) => s.transition('fade').delay(entering ? 1300 : 0).duration(400).style('opacity', 1)))
      .text((d) => d.labelText)
      .transition('move').duration(reduced ? 0 : 700).attr('x', (d) => d.x).attr('y', (d) => d.ly);

    document.getElementById('map-count').textContent = `${model.people.length} people · ${model.agents.length} agents`;
    state.model = model;
    firstRender = false;
    if (state.hovered) applyFocus(state.hovered);
  }

  function shock(n, kind) {
    if (reduced) return;
    fxLayer.append('circle').attr('class', kind).attr('cx', n.x).attr('cy', n.y).attr('r', n.r + 2)
      .transition().delay(3400).remove();
  }

  // ---------- Hover and focus ----------
  const tip = document.getElementById('tip');
  function hover(d, event) {
    state.hovered = d ? d.id : null;
    applyFocus(state.hovered || state.selected);
    if (!d) { tip.classList.remove('show'); return; }
    tip.innerHTML = tipHtml(d);
    tip.classList.add('show');
    moveTip(event);
  }
  function moveTip(event) {
    const box = document.getElementById('stage').getBoundingClientRect();
    let x = event.clientX - box.left + 16, y = event.clientY - box.top + 16;
    if (x + 270 > box.width) x -= 290;
    if (y + 150 > box.height) y -= 160;
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  }
  function tipHtml(d) {
    const model = state.model;
    if (d.kind === 'agent') {
      const sponsor = model.byId.get(d.sponsor);
      return `<b>${esc(d.name)}</b><span class="faint">AI agent · ${esc(human(d.dept))}</span>
        <div class="row"><span>Sponsor</span><span>${esc(sponsor?.name || 'none')}</span></div>
        <div class="row"><span>Risk tier</span><span>${esc(d.risk || 'n/a')}</span></div>
        <div class="row"><span>State</span><span>${d.violation ? 'policy breach' : d.orphan ? 'orphan' : 'sponsored'}</span></div>`;
    }
    return `<b>${esc(d.name)}</b><span class="faint">${esc(d.title || 'person')} · ${esc(human(d.dept))}</span>
      <div class="row"><span>Status</span><span>${esc(human(d.status))}</span></div>
      <div class="row"><span>Live access</span><span>${d.access}</span></div>
      <div class="row"><span>Sponsors</span><span>${d.agents.length} agent${d.agents.length === 1 ? '' : 's'}</span></div>`;
  }
  function applyFocus(id) {
    const near = id && state.model?.neighbours.get(id);
    nodeLayer.selectAll('g.node').classed('dim', (d) => Boolean(near) && !near.has(d.id));
    linkLayer.selectAll('path').classed('lit', (d) => Boolean(near) && (d.source === id || d.target === id));
    labelLayer.selectAll('text').style('opacity', (d) => (!near || near.has(d.id) ? 1 : 0.15));
    const dept = id && state.model?.byId.get(id)?.dept;
    zoneLayer.selectAll('g.zone').classed('lit', (d) => d.dept === dept);
  }

  // ---------- Selection, drawer, camera ----------
  function select(id, fly) {
    state.selected = id;
    nodeLayer.selectAll('g.node').classed('selected', (d) => d.id === id);
    applyFocus(id);
    renderDrawer();
    renderRows();
    if (fly) flyTo(id);
  }
  function clearSelection() {
    state.selected = null;
    nodeLayer.selectAll('g.node').classed('selected', false);
    applyFocus(null);
    document.getElementById('drawer').classList.remove('open');
    renderRows();
    svg.transition().duration(reduced ? 0 : 650).ease(d3.easeCubicInOut).call(zoom.transform, d3.zoomIdentity);
  }
  function flyTo(id) {
    const n = state.model?.byId.get(id);
    if (!n) return;
    const k = 2.1, drawerShift = 170;
    svg.transition().duration(reduced ? 0 : 750).ease(d3.easeCubicInOut)
      .call(zoom.transform, d3.zoomIdentity.translate(size.width / 2 - drawerShift - n.x * k, size.height / 2 - n.y * k).scale(k));
  }
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.selected) clearSelection(); });
  document.getElementById('zoom-in').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 1.4);
  document.getElementById('zoom-out').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 1 / 1.4);
  document.getElementById('zoom-reset').onclick = clearSelection;

  function renderDrawer() {
    const drawer = document.getElementById('drawer');
    const n = state.model?.byId.get(state.selected);
    if (!n) { drawer.classList.remove('open'); return; }
    const model = state.model;
    const close = '<button class="btn small close" data-close aria-label="Close">✕</button>';
    if (n.kind === 'agent') {
      const sponsor = model.byId.get(n.sponsor);
      drawer.innerHTML = `${close}
        <span class="badge agent">AI agent</span>
        <h2 style="margin-top:10px">${esc(n.name)}</h2>
        <span class="faint mono">${esc(n.id)}</span>
        <section><h3>Ownership</h3><dl class="kv">
          <dt>Sponsor</dt><dd>${sponsor ? `<a href="#" data-select="${sponsor.id}">${esc(sponsor.name)}</a> ${badge(sponsor.status)}` : badge('ORPHAN', 'no sponsor')}</dd>
          <dt>Department</dt><dd>${esc(human(n.dept))}</dd>
          <dt>Risk tier</dt><dd>${badge(n.risk || 'LOW', n.risk || 'n/a')}</dd>
          <dt>Status</dt><dd>${badge(n.status)}</dd>
        </dl></section>
        <section><h3>Why it is flagged</h3>
          ${n.orphan ? n.reasons.map((r) => `<div class="item highlight" style="margin-bottom:6px">${esc(human(r))}</div>`).join('') : ''}
          ${n.violation ? '<div class="item highlight">Breaks the current policy. <a href="guardian.html">Open Policy Guardian</a></div>' : ''}
          ${!n.alarm ? '<div class="empty" style="padding:14px">Sponsored and compliant.</div>' : ''}
        </section>`;
    } else {
      drawer.innerHTML = `${close}
        ${badge(n.status)}
        <h2 style="margin-top:10px">${esc(n.name)}</h2>
        <span class="faint">${esc(n.title || '—')} · ${esc(human(n.dept))}</span>
        <section><h3>Access</h3><dl class="kv">
          <dt>Live access</dt><dd class="num">${n.access}</dd>
          <dt>App role</dt><dd>${esc(human(n.role || '—'))}</dd>
        </dl></section>
        <section><h3>Sponsored agents</h3>
          ${n.agents.length ? n.agents.map((a) => `<a class="item" href="#" data-select="${esc(a.resource_key)}" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;color:inherit;text-decoration:none">
            <span class="badge agent">agent</span><span style="flex:1">${esc(a.agent_name)}</span>${a.orphan ? badge('ORPHAN', 'orphan') : ''}</a>`).join('') : '<div class="empty" style="padding:14px">Sponsors no agents.</div>'}
        </section>
        ${n.id === PEOPLE.arif.id ? '<section><button class="btn primary" style="width:100%" data-start-arif>Start offboarding</button></section>' : ''}`;
    }
    drawer.classList.add('open');
    drawer.querySelector('[data-close]').addEventListener('click', clearSelection);
    drawer.querySelectorAll('[data-select]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); select(a.dataset.select, true); }));
    drawer.querySelector('[data-start-arif]')?.addEventListener('click', startArif);
  }

  // ---------- Table ----------
  function renderRows() {
    if (!state.model) return;
    const q = document.getElementById('search').value.trim().toLowerCase();
    const dept = document.getElementById('dept').value;
    const filter = document.getElementById('filter').value;
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
        <td><b style="font-weight:550">${esc(n.name)}</b></td>
        <td>${n.kind === 'agent' ? '<span class="badge agent">agent</span>' : `<span class="muted">${esc(n.title || 'person')}</span>`}</td>
        <td class="muted">${esc(human(n.dept))}</td>
        <td>${n.kind === 'agent' ? (n.violation ? badge('VIOLATION', 'policy breach') : n.orphan ? badge('ORPHAN', 'orphan') : badge('ACTIVE', 'sponsored')) : badge(n.status)}</td>
        <td>${n.kind === 'agent' ? esc(state.model.byId.get(n.sponsor)?.name || '—') : `<span class="num">${n.access}</span>`}</td>
      </tr>`).join('') || '<tr><td colspan="5"><div class="empty"><b>No match</b>Try another name or clear the filters.</div></td></tr>';
    document.querySelectorAll('#rows tr[data-id]').forEach((tr) => tr.addEventListener('click', () => {
      select(tr.dataset.id, true);
      document.getElementById('stage').scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
    }));
  }
  ['search', 'dept', 'filter'].forEach((id) => document.getElementById(id).addEventListener('input', renderRows));

  async function loadGraph() {
    const graph = await api('/workforce/graph');
    const signature = JSON.stringify(graph);
    if (signature === state.signature) return;
    state.signature = signature;
    renderMap(graph);
    const depts = [...new Set(state.model.nodes.map((n) => n.dept))].sort();
    const deptSelect = document.getElementById('dept');
    if (deptSelect.options.length === 1) deptSelect.insertAdjacentHTML('beforeend', depts.map((d) => `<option value="${esc(d)}">${esc(human(d))}</option>`).join(''));
    renderRows();
    if (state.selected && !state.flown) {
      state.flown = true;
      select(state.selected, true);
      const n = state.model.byId.get(state.selected);
      if (n) setTimeout(() => shock(n, 'shock'), 800);
    } else if (state.selected) renderDrawer();
  }
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (state.signature) { state.model = null; renderMap(JSON.parse(state.signature)); } }, 250);
  });

  // ---------- Cases and evaluation ----------
  async function loadCases() {
    const cases = await api('/cases?limit=6');
    document.getElementById('cases').innerHTML = cases.length ? cases.map((c) => `
      <a class="item" href="workspace.html?case=${c.id}" style="display:flex;gap:12px;align-items:center;color:inherit;text-decoration:none">
        <div style="flex:1;min-width:0"><b style="font-weight:550">${esc(c.subject_name || '—')}</b>
          <div class="faint">${esc(human(c.case_type))}${c.origin ? ' · ' + esc(human(c.origin)) : ''}${c.tier ? ' · tier ' + esc(c.tier) : ''} · ${timeAgo(c.created_at)}</div></div>
        ${badge(c.status)}</a>`).join('') : '<div class="empty"><b>No cases yet</b>Start Arif Hossain\'s offboarding to begin the story.</div>';
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
      const bar = (v) => (v === null ? '' : `<div style="height:4px;border-radius:2px;background:var(--surface-3);margin-top:6px"><div style="height:100%;width:${v}%;border-radius:2px;background:${v >= 90 ? 'var(--ok)' : v >= 70 ? 'var(--warn)' : 'var(--bad)'}"></div></div>`);
      document.getElementById('eval').innerHTML = `<table class="data"><tbody>${rows.map(([l, v, n]) => `
        <tr><td>${esc(l)}${bar(v)}</td><td style="text-align:right"><b class="num">${v === null ? '—' : v + '%'}</b></td><td class="faint num">n=${n}</td></tr>`).join('')}
        <tr><td>Guardian false impacts</td><td style="text-align:right"><b class="num">${e.guardian.false_impacts}</b></td><td class="faint">seeded</td></tr></tbody></table>`;
    } catch {
      document.getElementById('eval').innerHTML = '<div class="empty"><b>No evaluation yet</b>Run <code>python -m app.scripts.run_evaluation</code> after a rehearsal.</div>';
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
