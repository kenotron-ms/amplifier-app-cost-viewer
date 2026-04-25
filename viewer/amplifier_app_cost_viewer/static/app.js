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
    loadSession(e.target.value);
  });

  document.getElementById('refresh-btn').addEventListener('click', async () => {
    try {
      state.sessions = [];
      state.activeSessionId = null;
      await fetchSessions();
      if (state.sessions.length > 0) {
        await loadSession(state.sessions[0].session_id);
      } else {
        renderToolbar();
      }
    } catch (err) {
      console.error('Refresh failed:', err);
      document.getElementById('tree-panel').innerHTML =
        `<div class="panel-placeholder" style="color:#f85149">Refresh failed: ${err.message}</div>`;
    }
  });
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

function renderTreePanel() { /* stub — replaced in Task 8 */ }


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
  const maxEndMs = Math.max(...state.spans.map(s => s.end_ms || 0), 1);
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
    document.getElementById('tree-panel').innerHTML =
      `<div class="panel-placeholder" style="color:#f85149">Error: ${err.message}</div>`;
    return;
  }

  renderToolbar();

  if (state.sessions.length > 0) {
    try {
      await loadSession(state.sessions[0].session_id);
    } catch (err) {
      console.error('Failed to load session:', err);
      document.getElementById('tree-panel').innerHTML =
        `<div class="panel-placeholder" style="color:#f85149">Error: ${err.message}</div>`;
    }
  } else {
    document.getElementById('tree-panel').innerHTML =
      '<div class="panel-placeholder">No sessions found in ~/.amplifier/projects/</div>';
  }
}

document.addEventListener('DOMContentLoaded', init);
