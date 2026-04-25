// ================================================================
// Amplifier Cost Viewer — app.js
// Vanilla JS, no framework, no build step.
// Sections added across Tasks 7–10:
//   1. State
//   2. API calls
//   3. Toolbar rendering
//   4. Tree panel rendering       (Task 8)
//   5. Gantt SVG rendering        (Task 9)
//   6. Detail panel               (Task 10)
//   7. Init / loadSession
// ================================================================


// ================================================================
// Section 1: State
// Central state object — all UI reads from here, never from DOM.
// ================================================================

const state = {
  sessions: [],           // list of root-session summaries from GET /api/sessions
  activeSessionId: null,  // session ID currently shown in tree + Gantt
  sessionData: null,      // full session tree from GET /api/sessions/{id}
  spans: [],              // flattened spans from GET /api/sessions/{id}/spans
  selectedSpan: null,     // span shown in the detail panel
  timeScale: 1,           // ms per pixel (computed in loadSession)
};

// Tracks which session nodes are expanded in the tree.
// Populated in loadSession(); toggled by tree row clicks (Task 8).
const expandedNodes = new Set();


// ================================================================
// Section 2: API calls
// All communication with the FastAPI backend lives here.
// ================================================================

async function fetchSessions() {
  const resp = await fetch('/api/sessions');
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  state.sessions = await resp.json();
}

async function fetchSession(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id} → ${resp.status}`);
  state.sessionData = await resp.json();
}

async function fetchSpans(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}/spans`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id}/spans → ${resp.status}`);
  state.spans = await resp.json();
}


// ================================================================
// Section 3: Toolbar rendering
// Session dropdown + total cost display + refresh button.
// ================================================================

function renderToolbar() {
  const toolbar = document.getElementById('toolbar');

  const totalCost = state.sessions.reduce(
    (sum, s) => sum + (s.total_cost_usd || 0), 0
  );
  const costStr = `$${totalCost.toFixed(4)}`;

  toolbar.innerHTML = `
    <span class="toolbar-title">Cost Viewer</span>
    <select id="session-select" aria-label="Select session">
      ${state.sessions.map(s => `
        <option value="${s.session_id}"
          ${s.session_id === state.activeSessionId ? 'selected' : ''}>
          ${s.session_id.slice(-8)} — ${_formatDate(s.start_ts)} — $${(s.total_cost_usd || 0).toFixed(4)}
        </option>
      `).join('')}
    </select>
    <span class="cost-total">All sessions: <strong>${costStr}</strong></span>
    <button id="refresh-btn" title="Refresh session list">&#8635;</button>
  `;

  document.getElementById('session-select').addEventListener('change', e => {
    loadSession(e.target.value).catch(err => {
      console.error('Failed to switch session:', err);
      _showError(`Error: ${err.message}`);
    });
  });

  document.getElementById('refresh-btn').addEventListener('click', async () => {
    try {
      await fetchSessions();
      state.activeSessionId = null;
      if (state.sessions.length > 0) {
        await loadSession(state.sessions[0].session_id);
      } else {
        renderToolbar();
      }
    } catch (err) {
      console.error('Refresh failed:', err);
      _showError(`Refresh failed: ${err.message}`);
    }
  });
}

function _showError(msg) {
  const el = document.getElementById('tree-panel');
  if (el) el.innerHTML =
    `<div class="panel-placeholder" style="color:#f85149">${msg}</div>`;
}

function _formatDate(isoStr) {
  if (!isoStr) return 'unknown';
  try {
    const d = new Date(isoStr);
    const diffMs = Date.now() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) {
      const hh = d.getHours().toString().padStart(2, '0');
      const mm = d.getMinutes().toString().padStart(2, '0');
      return `Today ${hh}:${mm}`;
    }
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString();
  } catch {
    return isoStr;
  }
}


// ================================================================
// Section 4: Tree panel rendering  (added in Task 8)
// ================================================================

function renderTreePanel() {
  const panel = document.getElementById('tree-panel');
  panel.innerHTML = '';

  if (!state.sessionData) {
    panel.innerHTML = '<div class="panel-placeholder">No session loaded.</div>';
    return;
  }

  _renderTreeNode(panel, state.sessionData, 0);
}

function _renderTreeNode(container, node, depth) {
  const sessionId = node.session_id;
  const isExpanded = expandedNodes.has(sessionId);
  const hasChildren = node.children && node.children.length > 0;

  const row = document.createElement('div');
  row.className = 'tree-row' + (sessionId === state.activeSessionId ? ' active' : '');
  row.dataset.sessionId = sessionId;

  // Indent span — width = depth * 12px
  const indentSpan = document.createElement('span');
  indentSpan.className = 'tree-indent';
  indentSpan.style.display = 'inline-block';
  indentSpan.style.width = `${depth * 12}px`;
  row.appendChild(indentSpan);

  // Toggle span — ▾ if expanded, ▸ if collapsed, &nbsp; if no children
  const toggleSpan = document.createElement('span');
  toggleSpan.className = 'tree-toggle';
  if (hasChildren) {
    toggleSpan.textContent = isExpanded ? '\u25be' : '\u25b8';
  } else {
    toggleSpan.innerHTML = '&nbsp;';
  }
  row.appendChild(toggleSpan);

  // Session label span — last 8 chars of session_id, optionally '· agentName'
  const labelSpan = document.createElement('span');
  labelSpan.className = 'session-label';
  const shortId = sessionId.slice(-8);
  const agentName = node.agent_name || node.agentName || null;
  labelSpan.textContent = agentName ? `${shortId} \u00b7 ${agentName}` : shortId;
  labelSpan.title = sessionId;
  row.appendChild(labelSpan);

  // Session cost span — $X.XXXX of total_cost_usd
  const costSpan = document.createElement('span');
  costSpan.className = 'session-cost';
  const cost = node.total_cost_usd || 0;
  costSpan.textContent = `$${cost.toFixed(4)}`;
  row.appendChild(costSpan);

  // Click handler — toggles expand/collapse, re-renders tree, scrolls Gantt
  row.addEventListener('click', () => {
    if (hasChildren) {
      if (expandedNodes.has(sessionId)) {
        expandedNodes.delete(sessionId);
      } else {
        expandedNodes.add(sessionId);
      }
    }
    renderTreePanel();
    _scrollGanttToSession(sessionId);
  });

  container.appendChild(row);

  // Recursively render children if expanded
  if (isExpanded && hasChildren) {
    node.children.forEach(child => _renderTreeNode(container, child, depth + 1));
  }
}

function _scrollGanttToSession(sessionId) {
  const ganttRows = document.getElementById('gantt-rows');
  if (!ganttRows) return;
  const el = ganttRows.querySelector(`g[data-session-id='${sessionId}']`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}


// ================================================================
// Section 5: Gantt SVG rendering  (added in Task 9)
// ================================================================

const ROW_HEIGHT = 32;
const SPAN_H = 20;
const SPAN_Y_OFF = 6;
const MIN_BAR_W = 2;

function renderGantt() {
  const ganttRows = document.getElementById('gantt-rows');
  const timeRuler = document.getElementById('time-ruler');
  if (!ganttRows || !timeRuler) return;

  ganttRows.innerHTML = '';
  timeRuler.innerHTML = '';

  if (!state.spans || state.spans.length === 0) {
    ganttRows.innerHTML = '<div class="panel-placeholder">No spans to display.</div>';
    return;
  }

  // Compute maxEndMs from spans
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);

  // Compute svgWidth: max of panel width and timeline extent
  const ganttPanel = document.getElementById('gantt-panel');
  const panelWidth = (ganttPanel ? ganttPanel.clientWidth : 800) - 80;
  const timelineWidth = maxEndMs / (state.timeScale || 1);
  const svgWidth = Math.max(panelWidth, timelineWidth);

  // Build sessionOrder via _flattenSessionOrder DFS
  const sessionOrder = [];
  if (state.sessionData) {
    _flattenSessionOrder(state.sessionData, sessionOrder);
  }

  // Group spans by session_id
  const spansBySession = {};
  state.spans.forEach(span => {
    const sid = span.session_id;
    if (!spansBySession[sid]) spansBySession[sid] = [];
    spansBySession[sid].push(span);
  });

  // Create main SVG element
  const totalHeight = Math.max(sessionOrder.length * ROW_HEIGHT, ROW_HEIGHT);
  const svg = _svgEl('svg', {
    width: svgWidth,
    height: totalHeight,
    style: 'display:block',
  });

  // Alternating row backgrounds (#0d1117 / #161b22)
  sessionOrder.forEach((node, i) => {
    const bg = _svgEl('rect', {
      x: 0,
      y: i * ROW_HEIGHT,
      width: svgWidth,
      height: ROW_HEIGHT,
      fill: i % 2 === 0 ? '#0d1117' : '#161b22',
    });
    svg.appendChild(bg);
  });

  // SVG background click: compute clickMs and call _showGap
  svg.addEventListener('click', e => {
    const svgRect = svg.getBoundingClientRect();
    const x = e.clientX - svgRect.left;
    const clickMs = x * (state.timeScale || 1);
    _showGap(clickMs);
  });

  // For each session row, create <g data-session-id> with transform translate
  sessionOrder.forEach((node, i) => {
    const sid = node.session_id;
    const g = _svgEl('g', {
      'data-session-id': sid,
      transform: `translate(0, ${i * ROW_HEIGHT})`,
    });

    const spans = spansBySession[sid] || [];
    spans.forEach(span => {
      const x = (span.start_ms || 0) / (state.timeScale || 1);
      const rawW = ((span.end_ms || 0) - (span.start_ms || 0)) / (state.timeScale || 1);
      const w = Math.max(rawW, MIN_BAR_W);
      const fill = span.color || '#64748B';

      const rect = _svgEl('rect', {
        x,
        y: SPAN_Y_OFF,
        width: w,
        height: SPAN_H,
        rx: 3,
        fill,
        opacity: 0.85,
      });

      // SVG <title> tooltip
      const titleEl = _svgEl('title', {});
      titleEl.textContent = _spanTooltip(span);
      rect.appendChild(titleEl);

      // Click handler: select span, stop propagation to SVG background
      rect.addEventListener('click', e => {
        e.stopPropagation();
        selectSpan(span);
      });

      // Hover highlight: brighten on enter, restore on leave
      rect.addEventListener('mouseenter', () => {
        rect.setAttribute('opacity', '1');
      });
      rect.addEventListener('mouseleave', () => {
        rect.setAttribute('opacity', '0.85');
      });

      g.appendChild(rect);
    });

    svg.appendChild(g);
  });

  ganttRows.appendChild(svg);
  _renderRuler(timeRuler, maxEndMs, svgWidth);
}


function _flattenSessionOrder(node, result) {
  result.push(node);
  if (node.children && node.children.length > 0) {
    node.children.forEach(child => _flattenSessionOrder(child, result));
  }
}


function _renderRuler(container, maxEndMs, svgWidth) {
  const svg = _svgEl('svg', {
    width: svgWidth,
    height: 28,
    style: 'display:block',
  });

  // Ruler background
  const bg = _svgEl('rect', {
    x: 0, y: 0, width: svgWidth, height: 28,
    fill: '#0d1117',
  });
  svg.appendChild(bg);

  // Pick tick interval based on total duration: 5s/30s/1m/5m
  let tickInterval;
  if (maxEndMs < 30000) {
    tickInterval = 5000;      // 5s ticks for short sessions
  } else if (maxEndMs < 120000) {
    tickInterval = 30000;     // 30s ticks
  } else if (maxEndMs < 600000) {
    tickInterval = 60000;     // 1m ticks
  } else {
    tickInterval = 300000;    // 5m ticks for long sessions
  }

  const timeScale = state.timeScale || 1;
  for (let t = 0; t <= maxEndMs; t += tickInterval) {
    const x = t / timeScale;

    // Tick line
    const line = _svgEl('line', {
      x1: x, y1: 0, x2: x, y2: 8,
      stroke: '#30363d',
      'stroke-width': 1,
    });
    svg.appendChild(line);

    // Tick label
    const text = _svgEl('text', {
      x,
      y: 22,
      fill: '#8b949e',
      'font-size': 10,
      'font-family': 'monospace',
      'text-anchor': 'middle',
    });
    text.textContent = _formatMs(t);
    svg.appendChild(text);
  }

  container.appendChild(svg);
}


function _svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}


function _formatMs(ms) {
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000).toString().padStart(2, '0');
  return minutes + 'm' + seconds + 's';
}


function _spanTooltip(span) {
  const type = span.type || '';
  const start = _formatMs(span.start_ms || 0);
  const end = _formatMs(span.end_ms || 0);

  if (type === 'llm') {
    const lines = [
      `${span.provider || ''}/${span.model || ''}`,
      `${start} \u2192 ${end}`,
    ];
    if (span.input_tokens != null)  lines.push(`in: ${span.input_tokens} tokens`);
    if (span.output_tokens != null) lines.push(`out: ${span.output_tokens} tokens`);
    if (span.cost_usd != null)      lines.push(`$${span.cost_usd.toFixed(6)}`);
    return lines.join('\n');
  }

  if (type === 'tool') {
    const ok = span.success ? '\u2713' : '\u2717';
    return [
      `tool: ${span.name || ''}`,
      `${ok} ${start} \u2192 ${end}`,
    ].join('\n');
  }

  if (type === 'thinking') {
    return `thinking\n${start} \u2192 ${end}`;
  }

  return `${type}\n${start} \u2192 ${end}`;
}


function _showGap(clickMs) {
  // Find the span ending just before and starting just after clickMs
  let before = null;
  let after = null;

  state.spans.forEach(span => {
    if ((span.end_ms || 0) <= clickMs) {
      if (!before || (span.end_ms || 0) > (before.end_ms || 0)) {
        before = span;
      }
    }
    if ((span.start_ms || 0) >= clickMs) {
      if (!after || (span.start_ms || 0) < (after.start_ms || 0)) {
        after = span;
      }
    }
  });

  renderDetail({ type: 'gap', before, after, clickMs });
}


// ================================================================
// Section 6: Detail panel  (added in Task 10)
// ================================================================

function renderDetail() { /* stub — replaced in Task 10 */ }

function selectSpan(span) {
  state.selectedSpan = span;
  renderDetail(span);
}


// ================================================================
// Section 7: Init / loadSession
// Entry point — runs on DOMContentLoaded.
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await fetchSession(id);
  await fetchSpans(id);

  // Auto-expand root and its immediate children
  expandedNodes.clear();
  expandedNodes.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => expandedNodes.add(c.session_id));
  }

  // Compute timeScale: fit the full timeline into the visible Gantt width
  // Use reduce instead of spread to avoid RangeError on very large span arrays.
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
  const ganttWidth = document.getElementById('gantt-panel').clientWidth || 1000;
  state.timeScale = maxEndMs / Math.max(ganttWidth - 80, 400);

  renderToolbar();
  renderTreePanel();
  renderGantt();
}

async function init() {
  try {
    await fetchSessions();
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    _showError(`Error: ${err.message}`);
    return;
  }

  renderToolbar();

  if (state.sessions.length > 0) {
    try {
      await loadSession(state.sessions[0].session_id);
    } catch (err) {
      console.error('Failed to load session:', err);
      _showError(`Error: ${err.message}`);
    }
  } else {
    document.getElementById('tree-panel').innerHTML =
      '<div class="panel-placeholder">No sessions found in ~/.amplifier/projects/</div>';
  }
}

document.addEventListener('DOMContentLoaded', init);
