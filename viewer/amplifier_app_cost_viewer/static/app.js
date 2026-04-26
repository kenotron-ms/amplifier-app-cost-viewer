// =============================================================================
// Amplifier Cost Viewer — app.js  (v2 — Lit custom elements)
// =============================================================================
// Architecture:
//   <acv-toolbar>   — session selector, zoom controls, cost summary
//   <acv-tree>      — collapsible session / sub-agent tree (left panel)
//   <acv-timeline>  — Gantt / canvas timeline (main panel)
//   <acv-detail>    — span detail drawer (bottom panel)
//
// Each component owns its shadow DOM; global `state` is the single source of
// truth.  renderAll() triggers all components to re-render from state.
// AcvToolbar dispatches CustomEvents; init() wires them to state mutations.
// =============================================================================

import { html, render } from '/static/vendor/lit.all.min.js';

// =============================================================================
// Constants
// =============================================================================

const ZOOM_MIN    = 0.05;  // ms per pixel — most zoomed-in
const ZOOM_MAX    = 200;   // ms per pixel — most zoomed-out
const ROW_H       = 32;    // px per session row
const SPAN_H      = 20;    // px span bar height
const HEATMAP_H   = 20;    // px heatmap row height
const IO_TRUNCATE = 500;   // chars before "show more"

// =============================================================================
// Section 1: State
// Central state object — all UI reads from here, never from DOM.
// =============================================================================

const state = {
  sessions:        [],    // root-session summaries from GET /api/sessions
  activeSessionId: null,  // session shown in tree + timeline
  sessionData:     null,  // full session tree from GET /api/sessions/{id}
  spans:           [],    // flattened spans from GET /api/sessions/{id}/spans
  expandedSessions: new Set(), // session IDs expanded in the tree
  selectedSpan:    null,  // span shown in the detail panel
  timeScale:       1,     // ms per pixel
  scrollLeft:      0,     // timeline horizontal scroll position (px)
  hasMore:         false, // whether more sessions can be loaded
};

// =============================================================================
// Section 2: State notification helper
// =============================================================================

const _subscribers = new Set();

function subscribe(fn) {
  _subscribers.add(fn);
}

function notify() {
  for (const fn of _subscribers) fn();
}

// =============================================================================
// Section 3: renderAll — trigger all components to re-render
// =============================================================================

function renderAll() {
  notify();
}

// =============================================================================
// Section 4: API helpers
// =============================================================================

async function fetchSessions(offset = 0) {
  const resp = await fetch(`/api/sessions?limit=25&offset=${offset}`);
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  const data = await resp.json();
  if (offset === 0) {
    state.sessions = data.sessions ?? [];
  } else {
    state.sessions = [...state.sessions, ...(data.sessions ?? [])];
  }
  state.hasMore = data.has_more ?? false;
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

// =============================================================================
// Section 5: Helper functions
// =============================================================================

/**
 * Format a duration in milliseconds as a human-readable string.
 * < 1000 ms  → "123.4ms"
 * < 60000 ms → "12.3s"
 * else       → "2.1min"
 */
function _formatMs(ms) {
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

/**
 * Format a token count as a compact string.
 * >= 1000 → "12.3k"
 * else    → "512"
 */
function _fmtTokens(n) {
  if (!n) return '0';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

/**
 * Format a date string (ISO 8601) as a human-readable relative label.
 * Today     → "Today"
 * Yesterday → "Yesterday"
 * else      → locale date string
 */
function _formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const todayStr = now.toDateString();
  const yesterdayStr = new Date(now - 86400000).toDateString();
  if (d.toDateString() === todayStr) return 'Today';
  if (d.toDateString() === yesterdayStr) return 'Yesterday';
  return d.toLocaleDateString();
}

/**
 * Escape a string for safe inclusion in HTML.
 * Replaces &, <, >, " with their HTML entity equivalents.
 */
function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// =============================================================================
// Section 6: Custom element — AcvToolbar
// Session selector dropdown, zoom controls, total cost display, refresh button.
// Dispatches CustomEvents for all user actions (session-change, zoom-in,
// zoom-out, refresh, load-more) so that init() can wire them to state updates.
// =============================================================================

class AcvToolbar extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this._render());
    this._render();
  }

  _render() {
    const totalCost = state.sessions.reduce(
      (sum, s) => sum + (s.total_cost_usd || 0), 0
    );
    render(html`
      <style>
        :host {
          display: flex;
          align-items: center;
          gap: 8px;
          height: var(--toolbar-height, 42px);
          padding: 0 12px;
          background: var(--surface, #161b22);
          border-bottom: 1px solid var(--border, #30363d);
          flex-shrink: 0;
          z-index: 10;
          box-sizing: border-box;
          font-family: "SF Mono", Consolas, Monaco, monospace;
          font-size: 12px;
          color: var(--text, #e6edf3);
        }
        .toolbar-title { font-weight: 600; margin-right: 4px; }
        select, button {
          background: var(--surface-alt, #21262d);
          color: var(--text, #e6edf3);
          border: 1px solid var(--border, #30363d);
          border-radius: 4px;
          padding: 3px 8px;
          font-family: inherit;
          font-size: 11px;
          cursor: pointer;
        }
        select { max-width: 280px; }
        select:hover, button:hover { background: var(--border, #30363d); }
        .cost-total { color: var(--text-muted, #8b949e); }
        .cost-total strong { color: var(--accent, #58a6ff); }
        .zoom-label { color: var(--text-muted, #8b949e); font-size: 10px; }
        .spacer { flex: 1; }
      </style>
      <span class="toolbar-title">Amplifier Cost Viewer</span>
      <select @change=${e => this._onSelect(e)} aria-label="Select session">
        ${state.sessions.map(s => html`
          <option
            value=${s.session_id}
            ?selected=${s.session_id === state.activeSessionId}
          >${s.session_id.slice(-8)}${s.agent_name ? ` · ${s.agent_name}` : ''} — ${_formatDate(s.created_at)} — $${(s.total_cost_usd || 0).toFixed(4)} — ${_fmtTokens(s.total_tokens || 0)} tok</option>
        `)}
        ${state.hasMore ? html`<option value="__load_more__">Load more…</option>` : ''}
      </select>
      <span class="cost-total">Total: <strong>$${totalCost.toFixed(4)}</strong></span>
      <span class="spacer"></span>
      <span class="zoom-label">${state.timeScale.toFixed(1)} ms/px</span>
      <button @click=${() => this._onZoomIn()} title="Zoom in">+</button>
      <button @click=${() => this._onZoomOut()} title="Zoom out">−</button>
      <button @click=${() => this._onRefresh()} title="Refresh">↺</button>
    `, this._root);
  }

  _onSelect(e) {
    const val = e.target.value;
    if (val === '__load_more__') {
      this.dispatchEvent(new CustomEvent('load-more', { bubbles: true, composed: true }));
    } else {
      this.dispatchEvent(new CustomEvent('session-change', {
        bubbles: true,
        composed: true,
        detail: { id: val },
      }));
    }
  }

  _onZoomIn() {
    this.dispatchEvent(new CustomEvent('zoom-in', { bubbles: true, composed: true }));
  }

  _onZoomOut() {
    this.dispatchEvent(new CustomEvent('zoom-out', { bubbles: true, composed: true }));
  }

  _onRefresh() {
    this.dispatchEvent(new CustomEvent('refresh', { bubbles: true, composed: true }));
  }
}

customElements.define('acv-toolbar', AcvToolbar);

// =============================================================================
// Section 7: Custom element — AcvTree  (full implementation)
// Collapsible session / sub-agent tree in the left panel.
// Dispatches toggle-expand and session-select CustomEvents; init() wires them.
// =============================================================================

class AcvTree extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this.update());
    this.update();
  }

  update() {
    if (!state.sessionData) {
      render(html`
        <style>${this.#styles()}</style>
        <div class="panel-placeholder">No session loaded.</div>
      `, this._root);
      return;
    }

    const maxCost = this.#maxCostOf(state.sessionData);
    const rows = [];
    this.#flatten(
      state.sessionData, 0,
      state.expandedSessions,
      maxCost,
      state.activeSessionId,
      rows
    );

    render(html`
      <style>${this.#styles()}</style>
      ${rows.map(({ node, depth, toggle, isActive, costPct }) => html`
        <div
          class=${'tree-row' + (isActive ? ' active' : '')}
          @click=${() => this.#onRowClick(node.session_id, (node.children?.length ?? 0) > 0)}
          data-session-id=${node.session_id}
          style=${'padding-left:' + (depth * 12) + 'px'}
        >
          <span class="toggle">${toggle}</span>
          <span class="session-label" title=${node.session_id}>
            ${node.name || node.agent_name || node.session_id.slice(-8)}
          </span>
          <span class="session-cost">$${(node.total_cost_usd || 0).toFixed(4)}·${_fmtTokens(node.total_tokens || 0)}</span>
          <div class="cost-bar" style=${'width:' + costPct.toFixed(1) + '%'}></div>
        </div>
      `)}
    `, this._root);
  }

  #styles() {
    return `
      :host {
        display: block;
        width: var(--tree-width, 220px);
        background: #161b22;
        border-right: 1px solid var(--border, #30363d);
        overflow-y: auto;
        flex-shrink: 0;
        box-sizing: border-box;
        font-family: "SF Mono", Consolas, Monaco, monospace;
        font-size: 12px;
        color: var(--text, #e6edf3);
      }
      .panel-placeholder {
        padding: 12px 8px;
        color: var(--text-muted, #8b949e);
      }
      .tree-row {
        display: flex;
        align-items: center;
        height: 32px;
        cursor: pointer;
        user-select: none;
        border-left: 2px solid transparent;
        position: relative;
        box-sizing: border-box;
        padding-right: 8px;
        overflow: hidden;
      }
      .tree-row:hover { background: var(--surface-alt, #21262d); }
      .tree-row.active {
        border-left-color: #58a6ff;
        background: var(--surface-alt, #21262d);
      }
      .toggle {
        width: 14px;
        flex-shrink: 0;
        text-align: center;
        font-size: 10px;
      }
      .session-label {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .session-cost {
        color: var(--text-muted, #8b949e);
        font-size: 11px;
        margin-left: 4px;
        flex-shrink: 0;
      }
      .cost-bar {
        position: absolute;
        bottom: 0;
        left: 0;
        height: 3px;
        background: #58a6ff;
        opacity: 0.4;
        pointer-events: none;
      }
    `;
  }

  #maxCostOf(node) {
    let max = node.total_cost_usd || 0;
    for (const child of node.children ?? []) {
      max = Math.max(max, this.#maxCostOf(child));
    }
    return max;
  }

  #flatten(node, depth, expanded, maxCost, activeId, rows) {
    const sid = node.session_id;
    const hasChildren = (node.children?.length ?? 0) > 0;
    const isExpanded = expanded.has(sid);
    const toggle = hasChildren ? (isExpanded ? '▾' : '▸') : ' ';
    const isActive = sid === activeId;
    const cost = node.total_cost_usd || 0;
    const costPct = maxCost > 0 ? (cost / maxCost) * 100 : 0;

    rows.push({ node, depth, toggle, isActive, costPct });

    if (isExpanded && hasChildren) {
      for (const child of node.children) {
        this.#flatten(child, depth + 1, expanded, maxCost, activeId, rows);
      }
    }
  }

  #onRowClick(sid, hasChildren) {
    if (hasChildren) {
      this.dispatchEvent(new CustomEvent('toggle-expand', {
        bubbles: true,
        composed: true,
        detail: { id: sid },
      }));
    }
    this.dispatchEvent(new CustomEvent('session-select', {
      bubbles: true,
      composed: true,
      detail: { id: sid },
    }));
  }
}

customElements.define('acv-tree', AcvTree);

// =============================================================================
// Section 8: Custom element — AcvTimeline  (shell)
// Canvas-based Gantt / timeline showing spans per session row.
// =============================================================================

class AcvTimeline extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this._render());
    this._render();
  }

  _render() {
    render(html`
      <style>
        :host {
          display: flex;
          flex-direction: column;
          flex: 1;
          overflow: hidden;
          min-width: 0;
          position: relative;
          background: var(--bg, #0d1117);
          box-sizing: border-box;
          font-family: "SF Mono", Consolas, Monaco, monospace;
          font-size: 12px;
        }
        #time-ruler {
          height: var(--ruler-height, 28px);
          background: var(--surface, #161b22);
          border-bottom: 1px solid var(--border, #30363d);
          flex-shrink: 0;
          overflow: hidden;
        }
        #gantt-rows {
          flex: 1;
          overflow-x: auto;
          overflow-y: auto;
          position: relative;
        }
        .placeholder {
          padding: 12px 8px;
          color: var(--text-muted, #8b949e);
          font-style: italic;
        }
      </style>
      <div id="time-ruler"></div>
      <div id="gantt-rows">
        ${state.spans.length === 0
          ? html`<div class="placeholder">No spans to display.</div>`
          : html`<!-- timeline rows rendered here -->`}
      </div>
    `, this._root);
  }
}

customElements.define('acv-timeline', AcvTimeline);

// =============================================================================
// Section 9: Custom element — AcvDetail  (shell)
// Detail drawer shown at the bottom when a span is selected.
// =============================================================================

class AcvDetail extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this._render());
    this._render();
  }

  _render() {
    const span = state.selectedSpan;
    render(html`
      <style>
        :host {
          display: block;
          background: var(--surface, #161b22);
          border-top: 1px solid var(--border, #30363d);
          min-height: var(--detail-height, 180px);
          overflow-y: auto;
          padding: 10px 14px;
          box-sizing: border-box;
          font-family: "SF Mono", Consolas, Monaco, monospace;
          font-size: 12px;
          color: var(--text, #e6edf3);
        }
        :host(.hidden) { display: none; }
        .detail-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
        .detail-title { font-weight: 600; }
        .detail-close {
          background: none;
          border: none;
          color: var(--text-muted, #8b949e);
          cursor: pointer;
          font-size: 14px;
          padding: 2px 4px;
          border-radius: 3px;
        }
        .detail-close:hover { color: var(--text, #e6edf3); background: var(--surface-alt, #21262d); }
      </style>
      ${span ? html`
        <div class="detail-header">
          <span class="detail-title">${span.type || 'span'}: ${span.name || span.model || span.tool_name || ''}</span>
          <button class="detail-close" @click=${() => this._close()}>✕</button>
        </div>
        <div class="detail-section">
          <div>start: ${span.start_ms ?? 0}ms</div>
          <div>end: ${span.end_ms ?? 0}ms</div>
          ${span.cost_usd != null ? html`<div>cost: $${span.cost_usd.toFixed(6)}</div>` : ''}
        </div>
      ` : html`<div class="placeholder" style="color:var(--text-muted,#8b949e);font-style:italic">Select a span to view details.</div>`}
    `, this._root);
  }

  _close() {
    state.selectedSpan = null;
    this.classList.add('hidden');
    notify();
  }
}

customElements.define('acv-detail', AcvDetail);

// =============================================================================
// Section 10: loadSession helper
// =============================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  state.selectedSpan = null;

  // Fetch session data and spans in parallel
  await Promise.all([fetchSession(id), fetchSpans(id)]);

  // Auto-expand root and first-level children
  state.expandedSessions.clear();
  state.expandedSessions.add(id);
  if (state.sessionData?.children) {
    for (const c of state.sessionData.children) {
      state.expandedSessions.add(c.session_id);
    }
  }

  // Compute initial timeScale to fit timeline in view
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
  const viewWidth = document.getElementById('timeline')?.clientWidth || 800;
  state.timeScale = maxEndMs / Math.max(viewWidth - 80, 400);
  state.scrollLeft = 0;

  renderAll();
}

// =============================================================================
// Section 11: init — entry point
// Wires toolbar CustomEvents to state mutations and kicks off initial data load.
// =============================================================================

async function init() {
  const toolbar = document.querySelector('acv-toolbar');

  // Wire: session-change → load the selected session
  if (toolbar) {
    toolbar.addEventListener('session-change', async e => {
      try {
        await loadSession(e.detail.id);
      } catch (err) {
        console.error('Failed to switch session:', err);
      }
    });

    // Wire: zoom-in → decrease ms/px (zoom in = fewer ms per pixel)
    toolbar.addEventListener('zoom-in', () => {
      state.timeScale = Math.max(ZOOM_MIN, state.timeScale / 1.5);
      renderAll();
    });

    // Wire: zoom-out → increase ms/px (zoom out = more ms per pixel)
    toolbar.addEventListener('zoom-out', () => {
      state.timeScale = Math.min(ZOOM_MAX, state.timeScale * 1.5);
      renderAll();
    });

    // Wire: refresh → reload all data from server
    toolbar.addEventListener('refresh', async () => {
      try {
        await fetch('/api/refresh', { method: 'POST' });
        await fetchSessions(0);
        renderAll();
        if (state.sessions.length > 0) {
          await loadSession(state.sessions[0].session_id);
        }
      } catch (err) {
        console.error('Refresh failed:', err);
      }
    });

    // Wire: load-more → fetch next page of sessions
    toolbar.addEventListener('load-more', async () => {
      try {
        await fetchSessions(state.sessions.length);
        renderAll();
      } catch (err) {
        console.error('Load more failed:', err);
      }
    });
  }

  // Wire tree events: toggle-expand and session-select
  const tree = document.querySelector('acv-tree');
  if (tree) {
    // Wire: toggle-expand → toggle expandedSessions set membership
    tree.addEventListener('toggle-expand', e => {
      const id = e.detail.id;
      if (state.expandedSessions.has(id)) {
        state.expandedSessions.delete(id);
      } else {
        state.expandedSessions.add(id);
      }
      renderAll();
    });

    // Wire: session-select → update activeSessionId and renderAll
    tree.addEventListener('session-select', e => {
      state.activeSessionId = e.detail.id;
      renderAll();
    });
  }

  // Initial data load
  try {
    await fetchSessions();
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    return;
  }

  renderAll();

  if (state.sessions.length > 0) {
    try {
      await loadSession(state.sessions[0].session_id);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  }
}

document.addEventListener('DOMContentLoaded', init);
