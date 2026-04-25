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

function renderGantt() { /* stub — replaced in Task 9 */ }


// ================================================================
// Section 6: Detail panel  (added in Task 10)
// ================================================================

function renderDetail() { /* stub — replaced in Task 10 */ }
function selectSpan()   { /* stub — replaced in Task 10 */ }


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
