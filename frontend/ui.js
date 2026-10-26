/* Shared LivingOps UI: shell, API, persona, polling, formatting.
   Plain browser JS, no build step. Pages call LO.mount({...}). */
(function () {
  const API = '/api';
  const PERSONA_KEY = 'livingops.persona.v1';

  // Story characters (fixed UUIDs in backend seed_demo.py).
  const PEOPLE = {
    farhana: { id: '11111111-1111-4111-8111-111111111111', name: 'Farhana Islam', role: 'HR Manager' },
    nabil: { id: '22222222-2222-4222-8222-222222222222', name: 'Nabil Chowdhury', role: 'Engineering Manager' },
    tahmid: { id: '33333333-3333-4333-8333-333333333333', name: 'Tahmid Hasan', role: 'IT Security Owner' },
    arif: { id: '66666666-6666-4666-8666-666666666666', name: 'Arif Hossain', role: 'Senior Software Engineer' },
  };

  // Inline stroke icons (no icon font, so they work OFFLINE).
  const ICON = {
    dashboard: '<path d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"/>',
    cases: '<path d="M4 6h16M4 12h16M4 18h10"/>',
    approvals: '<path d="M9 12l2 2 4-4"/><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/>',
    guardian: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h4"/>',
    security: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  };
  const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[name]}</svg>`;

  const NAV = [
    { href: 'index.html', label: 'Dashboard', icon: 'dashboard' },
    { href: 'cases.html', label: 'Cases', icon: 'cases' },
    { href: 'approvals.html', label: 'Approvals', icon: 'approvals', count: 'approvals' },
    { href: 'guardian.html', label: 'Policy Guardian', icon: 'guardian' },
    { href: 'security.html', label: 'Security', icon: 'security' },
  ];

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      body: options.body && typeof options.body !== 'string' ? JSON.stringify(options.body) : options.body,
    });
    const text = await response.text();
    let payload = null;
    if (text) { try { payload = JSON.parse(text); } catch { payload = { detail: text }; } }
    if (!response.ok) {
      const detail = payload?.detail;
      const message = typeof detail === 'string' ? detail
        : Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
        : `Request failed (${response.status})`;
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function toast(message, type = '') {
    let el = document.getElementById('toast');
    if (!el) { el = document.createElement('div'); el.id = 'toast'; el.className = 'toast'; document.body.append(el); }
    el.textContent = message;
    el.className = `toast show ${type}`.trim();
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { el.className = 'toast'; }, 4200);
  }

  function persona() {
    try { return localStorage.getItem(PERSONA_KEY) || 'farhana'; } catch { return 'farhana'; }
  }
  function setPersona(key) {
    try { localStorage.setItem(PERSONA_KEY, key); } catch { /* private mode: keep in memory */ }
    document.dispatchEvent(new CustomEvent('persona', { detail: key }));
  }
  const actingAs = () => PEOPLE[persona()] || PEOPLE.farhana;

  // Status -> badge class (colour + shape)
  const TONE = {
    ACTIVE: 'ok', VERIFIED: 'ok', COMPLETED: 'ok', APPROVED: 'ok', RESOLVED: 'ok', CURRENT: 'ok', SUCCEEDED: 'ok', LOW: 'ok',
    PENDING_APPROVAL: 'pending', PENDING: 'pending', PLANNING: 'pending', EXECUTING: 'pending', DISPATCHED: 'pending', NEW: 'pending', DRAFT: 'pending', REMEDIATING: 'pending', OPEN: 'pending',
    DEPARTING: 'warn', MEDIUM: 'warn', HUMAN_REVIEW: 'warn', PAUSED: 'warn', RETRYING: 'warn', REVIEW: 'warn', CANDIDATE: 'pending',
    FAILED: 'bad', REJECTED: 'bad', DENIED: 'bad', HIGH: 'bad', STALE: 'bad', ORPHAN: 'bad', VIOLATION: 'bad', DENY: 'bad',
    INACTIVE: 'idle', ARCHIVED: 'idle', SUPERSEDED: 'idle', SKIPPED: 'idle', CANCELLED: 'idle', REVOKED: 'idle', EXPIRED: 'idle', DISABLED: 'idle',
  };
  const badge = (status, label) => `<span class="badge ${TONE[status] || 'idle'}">${esc(label || String(status || '').replaceAll('_', ' ').toLowerCase())}</span>`;

  function timeAgo(value) {
    if (!value) return '—';
    const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000);
    if (seconds < 60) return `${Math.max(seconds, 0)}s ago`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
    return new Date(value).toLocaleDateString();
  }
  function clock(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(total / 60), s = total % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  const human = (text) => String(text || '').replaceAll('_', ' ').toLowerCase();

  // Poll without overlapping requests; pauses while the tab is hidden.
  function poll(fn, ms = 3000) {
    let running = false;
    const tick = async () => {
      if (document.hidden || running) return;
      running = true;
      try { await fn(); } catch (error) { console.warn(error); } finally { running = false; }
    };
    tick();
    const timer = setInterval(tick, ms);
    document.addEventListener('visibilitychange', tick);
    return () => clearInterval(timer);
  }

  function shell({ active, title, subtitle, bare }) {
    const nav = NAV.map((n) => `
      <a href="${n.href}" class="${n.href === active ? 'active' : ''}">
        ${icon(n.icon)}<span class="lbl">${n.label}</span>
        ${n.count ? `<span class="count hidden" id="nav-count-${n.count}"></span>` : ''}
      </a>`).join('');
    const options = Object.entries(PEOPLE).filter(([k]) => k !== 'arif')
      .map(([key, p]) => `<option value="${key}">${esc(p.name)} · ${esc(p.role)}</option>`).join('');
    document.title = `${title} · LivingOps`;
    document.body.insertAdjacentHTML('afterbegin', `
      <div class="shell">
        <header class="topnav">
          <a class="brand" href="index.html"><div class="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="12" r="8.5" stroke-dasharray="2 3"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3"/></svg></div>
            <div><b>LivingOps</b><span>Every access has an owner</span></div></a>
          <nav class="nav pill">${nav}</nav>
          <div class="right">
            <span id="mode-badge" class="badge idle">connecting</span>
            <button class="btn small" id="reset-demo" title="Reset the demo company, policies and GitHub demo org">Reset demo</button>
            <label class="persona" title="Acting as"><span class="avatar" id="persona-initials"></span><select id="persona-select">${options}</select></label>
          </div>
        </header>
        <div class="main">
          ${bare ? '' : `<div class="content" style="padding-bottom:0;animation:none"><div class="page-head"><div class="title"><h1>${esc(title)}</h1><span class="faint">${esc(subtitle || '')}</span></div></div></div>`}
          <main class="content" id="page"></main>
        </div>
      </div>`);
    const select = document.getElementById('persona-select');
    document.getElementById('reset-demo').addEventListener('click', resetDemo);
    select.value = persona();
    const initials = () => { document.getElementById('persona-initials').textContent = actingAs().name.split(' ').map((p) => p[0]).join(''); };
    initials();
    select.addEventListener('change', () => { setPersona(select.value); initials(); });
    refreshChrome();
    setInterval(refreshChrome, 10000);
    return document.getElementById('page');
  }

  // Demo reset: same as `python -m app.scripts.reset_demo --yes`. It runs on
  // the server in the background (minutes), so poll until it finishes.
  async function resetDemo() {
    const ok = confirm('Reset the demo?\n\nThis deletes all demo cases, approvals and lessons, puts policies back on V1, and restores the GitHub demo org (Arif\'s access, the bot\'s write key). It takes 2-3 minutes.');
    if (!ok) return;
    const button = document.getElementById('reset-demo');
    button.disabled = true;
    try {
      await api('/demo/reset', { method: 'POST' });
    } catch (error) {
      if (error.status !== 409) { toast(error.message, 'error'); button.disabled = false; return; }
    }
    toast('Resetting the demo… this takes 2-3 minutes.');
    const started = Date.now();
    const timer = setInterval(async () => {
      let status;
      try { status = await api('/demo/reset'); } catch { return; }
      const seconds = Math.round((Date.now() - started) / 1000);
      button.textContent = status.state === 'running' ? `Resetting… ${seconds}s` : 'Reset demo';
      if (status.state === 'running') return;
      clearInterval(timer);
      button.disabled = false;
      if (status.state === 'done') { toast('Demo reset complete.'); setTimeout(() => location.reload(), 1200); }
      else toast(`Reset failed: ${status.error || 'unknown error'}`, 'error');
    }, 3000);
  }

  async function refreshChrome() {
    try {
      const mode = await api('/demo/mode');
      const el = document.getElementById('mode-badge');
      const tone = mode.mode === 'LIVE' ? 'ok' : mode.mode === 'CACHED_AI' ? 'pending' : 'warn';
      el.className = `badge ${tone} live`;
      el.textContent = `${mode.mode.replace('_', ' ')}${mode.github_enabled ? ' · GitHub' : ''}`;
      el.title = `${mode.cached_llm_answers} cached AI answers, ${mode.cached_embeddings} cached embeddings`;
    } catch { /* backend offline: leave the badge as is */ }
    try {
      const pending = await api(`/approvals?assigned_to=${actingAs().id}`);
      const count = document.getElementById('nav-count-approvals');
      if (count) { count.textContent = pending.length; count.classList.toggle('hidden', !pending.length); }
    } catch { /* ignore */ }
  }

  // Animate a number into an element: "79.2%", "11 / 24" or "5".
  function countUp(el, text) {
    const match = /^(\d+(?:\.\d+)?)(.*)$/.exec(String(text));
    if (!match || el.dataset.shown === String(text) || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.textContent = text; el.dataset.shown = text; return;
    }
    const target = parseFloat(match[1]), decimals = (match[1].split('.')[1] || '').length;
    const start = performance.now(), duration = 900;
    el.dataset.shown = text;
    const frame = (now) => {
      const t = Math.min(1, (now - start) / duration), eased = 1 - Math.pow(1 - t, 3);
      el.textContent = (target * eased).toFixed(decimals) + match[2];
      if (t < 1 && el.dataset.shown === String(text)) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }

  window.LO = { countUp, icon, api, toast, esc, badge, timeAgo, clock, human, poll, shell, actingAs, persona, PEOPLE };
})();
