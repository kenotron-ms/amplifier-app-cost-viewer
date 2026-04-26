// =============================================================================
// Amplifier Cost Viewer — app.js  (v2 — Lit custom elements)
// =============================================================================
// Architecture:
//   <acv-toolbar>   — session selector, zoom controls, cost summary
//   <acv-tree>      — collapsible session / sub-agent tree (left panel)
//   <acv-timeline>  — cost heatmap + ruler + canvas timeline (main panel)
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
  loading: false,          // true while fetchSession/fetchSpans in flight
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
  // Push loading flag directly to timeline (so #draw() sees it before the RAF fires)
  const _tl = document.querySelector('acv-timeline');
  if (_tl) _tl.loading = state.loading;
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
 * Nice human-readable tick intervals for the ruler (ms).
 * Covers 100ms → 1h; used by both #renderRuler and the grid-line drawing.
 */
const NICE_INTERVALS = [
  100,      // 0.1s
  250,      // 0.25s
  500,      // 0.5s
  1000,     // 1s
  2000,     // 2s
  5000,     // 5s
  10000,    // 10s
  30000,    // 30s
  60000,    // 1m
  120000,   // 2m
  300000,   // 5m
  600000,   // 10m
  1800000,  // 30m
  3600000,  // 1h
];

/**
 * Format a ruler tick label based on the active tick interval.
 * Uses interval-aware units so labels are always readable at any zoom level.
 */
function _formatRulerLabel(ms, intervalMs) {
  if (ms === 0) return '0';
  if (intervalMs < 1000) {
    // Sub-second: show ms
    return ms + 'ms';
  }
  if (intervalMs < 60000) {
    // Seconds
    return Math.round(ms / 1000) + 's';
  }
  if (intervalMs < 3600000) {
    // Minutes[:seconds]
    const totalSec = Math.round(ms / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return s === 0 ? `${m}m` : `${m}m${s}s`;
  }
  // Hours[:minutes]
  const totalMin = Math.round(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return m === 0 ? `${h}h` : `${h}h${m}m`;
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
// Section 5b: Tree traversal helpers
// =============================================================================

/**
 * Walk the session tree and return the list of visible nodes (respecting
 * the expanded set).  A node is visible if it is the root, or its parent
 * is expanded.
 *
 * @param {Object} node     - root session node (has .children array)
 * @param {Set}    expanded - set of expanded session IDs
 * @returns {Array}         - flat array of visible nodes in display order
 */
function _visibleRows(node, expanded) {
  const rows = [];
  function walk(n) {
    rows.push(n);
    if (expanded.has(n.session_id) && n.children?.length) {
      for (const child of n.children) walk(child);
    }
  }
  walk(node);
  return rows;
}

/**
 * Build a sessionId → rowIndex map for the visible rows.
 *
 * @param {Object} sessionData - root session node
 * @param {Set}    expanded    - set of expanded session IDs
 * @returns {Map}              - Map<sessionId, rowIndex>
 */
function _rowIndexMap(sessionData, expanded) {
  const rows = _visibleRows(sessionData, expanded);
  const map = new Map();
  rows.forEach((n, i) => map.set(n.session_id, i));
  return map;
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
        .spinner {
          display: inline-block;
          width: 14px;
          height: 14px;
          border: 2px solid #30363d;
          border-top-color: #58a6ff;
          border-radius: 50%;
          animation: spin 0.7s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      </style>
      <span class="toolbar-title">Amplifier Cost Viewer</span>
      <select @change=${e => this._onSelect(e)} aria-label="Select session" ?disabled=${state.loading}>
        ${state.sessions.map(s => html`
          <option
            value=${s.session_id}
            ?selected=${s.session_id === state.activeSessionId}
          >${s.session_id.slice(-8)}${s.name ? ` · ${s.name}` : ''} — ${_formatDate(s.start_ts)} — $${(s.total_cost_usd || 0).toFixed(4)} — ${_fmtTokens((s.total_input_tokens || 0) + (s.total_output_tokens || 0))} tok</option>
        `)}
        ${state.hasMore ? html`<option value="__load_more__">Load more…</option>` : ''}
      </select>
      <span class="cost-total">Total: <strong>$${totalCost.toFixed(4)}</strong></span>
      <span class="spacer"></span>
      <span class="zoom-label">${state.timeScale.toFixed(1)} ms/px</span>
      <button @click=${() => this._onZoomIn()} title="Zoom in">+</button>
      <button @click=${() => this._onZoomOut()} title="Zoom out">−</button>
      <button @click=${() => this._onRefresh()} title="Refresh">↺</button>
      ${state.loading ? html`<span class="spinner" aria-label="Loading"></span>` : ''}
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
          <span class="session-cost">$${(node.total_cost_usd || 0).toFixed(4)}·${_fmtTokens((node.total_input_tokens || 0) + (node.total_output_tokens || 0))}</span>
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
    const toggle = hasChildren ? (isExpanded ? '▾' : '▸') : '\u00a0';
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
// Section 8: Custom element — AcvTimeline  (full implementation)
// Cost heatmap strip + time ruler + canvas area for spans.
// =============================================================================

class AcvTimeline extends HTMLElement {
  // Private fields
  #canvas  = null;
  #ctx     = null;
  #rafId   = null;
  #loading = false;
  // Drag-to-pan state
  #dragStartX = 0;
  #dragStartScrollLeft = 0;
  #isDragging = false;
  #hasDragged = false;

  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this.update());
    this.update();
  }

  /** Called externally to push new data; schedules a RAF-debounced redraw. */
  set data(value) {
    this.update();
    this.#scheduleRedraw();
  }

  /** Set loading state — shows overlay on canvas while true. */
  set loading(v) {
    this.#loading = !!v;
    this.#scheduleRedraw();
  }

  /** Render the shadow DOM structure: heatmap, ruler, canvas-wrap, detail panel. */
  update() {
    const spans   = state.spans;
    const ts      = state.timeScale;
    const scrollL = state.scrollLeft;

    render(html`
      <style>${this.#styles()}</style>
      <div id="heatmap"></div>
      <div id="ruler" @wheel=${e => this.#onRulerWheel(e)}></div>
      <div id="canvas-wrap">
        <canvas></canvas>
      </div>
      <acv-detail
        id="detail"
        .data=${state.selectedSpan}
        @detail-close=${e => this.#onDetailClose(e)}
      ></acv-detail>
    `, this._root);

    // After render, populate heatmap and ruler, then schedule canvas draw
    this.#renderHeatmap(spans, ts, scrollL);
    this.#renderRuler(spans, ts, scrollL);
    this.#scheduleRedraw();
  }

  /** Re-dispatch 'detail-close' so it bubbles out of the timeline. */
  #onDetailClose(_e) {
    this.dispatchEvent(new CustomEvent('detail-close', {
      bubbles:  true,
      composed: true,
    }));
  }

  // ---------------------------------------------------------------------------
  // Private: canvas management
  // ---------------------------------------------------------------------------

  /** Find the canvas in shadow DOM, get 2D context, attach click/drag listeners. */
  #ensureCanvas() {
    const canvas = this._root.querySelector('canvas');
    if (!canvas) return false;
    if (this.#canvas !== canvas) {
      this.#canvas = canvas;
      this.#ctx = canvas.getContext('2d');
      canvas.addEventListener('click', e => this.#onCanvasClick(e));

      // Drag-to-pan: mousedown starts drag
      canvas.addEventListener('mousedown', e => {
        if (e.button !== 0) return; // left button only
        this.#dragStartX = e.clientX;
        this.#dragStartScrollLeft = state.scrollLeft;
        this.#isDragging = true;
        this.#hasDragged = false;
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
      });

      // Drag-to-pan: mousemove updates scrollLeft
      canvas.addEventListener('mousemove', e => {
        if (!this.#isDragging) return;
        const delta = e.clientX - this.#dragStartX;
        if (Math.abs(delta) > 4) this.#hasDragged = true;
        if (this.#hasDragged) {
          state.scrollLeft = Math.max(0, this.#dragStartScrollLeft - delta);
          this.#draw();
        }
      });

      // Drag-to-pan: stop drag on mouseup (suppress click if we dragged)
      canvas.addEventListener('mouseup', e => {
        if (this.#hasDragged) e.stopPropagation();
        this.#isDragging = false;
        canvas.style.cursor = 'grab';
      });

      // Drag-to-pan: stop drag on mouseleave to avoid stuck drag state
      canvas.addEventListener('mouseleave', () => {
        this.#isDragging = false;
        canvas.style.cursor = 'grab';
      });
    }
    return true;
  }

  /** Resize canvas to match its CSS size, applying DPR scaling. */
  #resizeCanvas() {
    if (!this.#canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const wrap = this._root.querySelector('#canvas-wrap');
    const w = wrap ? wrap.clientWidth  : this.clientWidth;
    const h = wrap ? wrap.clientHeight : this.clientHeight;
    this.#canvas.width  = Math.round(w * dpr);
    this.#canvas.height = Math.round(h * dpr);
    this.#canvas.style.width  = w + 'px';
    this.#canvas.style.height = h + 'px';
    if (this.#ctx) {
      this.#ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
  }

  /** Schedule a debounced redraw via requestAnimationFrame. */
  #scheduleRedraw() {
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = requestAnimationFrame(() => {
      this.#rafId = null;
      if (this.#ensureCanvas()) {
        this.#resizeCanvas();
        this.#draw();
      }
    });
  }

  /** Draw canvas content: clear background, render spans or placeholder. */
  #draw() {
    if (!this.#ctx || !this.#canvas) return;
    const ctx     = this.#ctx;
    const cw      = this.#canvas.width  / (window.devicePixelRatio || 1);
    const ch      = this.#canvas.height / (window.devicePixelRatio || 1);
    const ts      = state.timeScale;
    const scrollL = state.scrollLeft;

    // Loading overlay — shown while session data is being fetched
    if (this.#loading) {
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, cw, ch);
      ctx.fillStyle = '#8b949e';
      ctx.font = '14px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Loading\u2026', cw / 2, ch / 2);
      ctx.textAlign = 'left'; // reset
      return;
    }

    // 1. Resize is already done by #resizeCanvas before #draw is called.

    // 2. clearRect full canvas
    ctx.clearRect(0, 0, cw, ch);

    // 3. Early return with 'No spans' message if empty
    if (!state.spans || state.spans.length === 0) {
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, cw, ch);
      ctx.fillStyle = '#8b949e';
      ctx.font = '12px "SF Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('No spans to display.', cw / 2, ch / 2);
      return;
    }

    // 4. Build rowMap via _rowIndexMap
    const rowMap = state.sessionData
      ? _rowIndexMap(state.sessionData, state.expandedSessions)
      : new Map();

    const numRows = rowMap.size || 1;

    // 5. Draw alternating row backgrounds (#0d1117 even, #161b22 odd)
    for (let i = 0; i < numRows; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#0d1117' : '#161b22';
      ctx.fillRect(0, i * ROW_H, cw, ROW_H);
    }
    // Fill any remaining canvas area below the rows
    if (numRows * ROW_H < ch) {
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, numRows * ROW_H, cw, ch - numRows * ROW_H);
    }

    // 6. Draw vertical grid lines matching ruler tick intervals (strokeStyle #21262d)
    //    Uses the same NICE_INTERVALS adaptive algorithm as #renderRuler.
    {
      const visibleMs      = cw * ts;
      const rawInterval    = visibleMs / 8;
      const tickIntervalMs = NICE_INTERVALS.find(v => v >= rawInterval)
        || NICE_INTERVALS[NICE_INTERVALS.length - 1];
      const scrollLeftMs   = scrollL * ts;
      const lastTickMs     = scrollLeftMs + visibleMs;
      const firstTick      = Math.ceil(scrollLeftMs / tickIntervalMs) * tickIntervalMs;

      ctx.beginPath();
      ctx.strokeStyle = '#21262d';
      ctx.lineWidth   = 1;
      for (let ms = firstTick; ms <= lastTickMs + tickIntervalMs; ms += tickIntervalMs) {
        const px = (ms - scrollLeftMs) / ts;
        if (px < 0 || px > cw) continue;
        ctx.moveTo(px, 0);
        ctx.lineTo(px, ch);
      }
      ctx.stroke();
    }

    // 7. Color-batched span drawing
    //    Batch spans by color into Map<color, rects[]> for efficient rendering.
    const batches = new Map(); // Map<color, Array<{x,y,w,h}>>

    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue; // collapsed / not visible

      const x        = (span.start_ms || 0) / ts - scrollL;
      const duration = Math.max(0, (span.end_ms || 0) - (span.start_ms || 0));
      const w        = Math.max(2, duration / ts); // minimum 2px width

      // Visibility culling: skip off-screen spans
      if (x + w < -10 || x > cw + 10) continue;

      const y     = rowIdx * ROW_H + (ROW_H - SPAN_H) / 2;
      const color = span.color || '#64748B'; // fallback color

      let rects = batches.get(color);
      if (!rects) { rects = []; batches.set(color, rects); }
      rects.push({ x, y, w, h: SPAN_H });
    }

    // Draw each color batch: beginPath, rect each, fill()
    for (const [color, rects] of batches) {
      ctx.fillStyle = color;
      ctx.beginPath();
      for (const r of rects) {
        ctx.rect(r.x, r.y, r.w, r.h);
      }
      ctx.fill();
    }

    // 8. Text labels on spans wider than 60px
    ctx.font          = '11px "SF Mono", monospace';
    ctx.fillStyle     = '#e6edf3';
    ctx.textAlign     = 'left';
    ctx.textBaseline  = 'middle';

    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue;

      const x        = (span.start_ms || 0) / ts - scrollL;
      const duration = Math.max(0, (span.end_ms || 0) - (span.start_ms || 0));
      const w        = Math.max(2, duration / ts);

      if (x + w < -10 || x > cw + 10) continue;
      if (w <= 60) continue; // only label spans wider than 60px

      const y = rowIdx * ROW_H + ROW_H / 2;

      // Build label: model·cost for LLM spans, tool_name for tool spans
      let label = '';
      if (span.type === 'llm' || span.model) {
        const costStr = span.cost_usd != null ? `$${span.cost_usd.toFixed(4)}` : '';
        label = span.model
          ? `${span.model}${costStr ? '·' + costStr : ''}`
          : costStr;
      } else if (span.tool_name) {
        label = span.tool_name;
      } else {
        label = span.name || '';
      }
      if (!label) continue;

      ctx.fillText(label, x + 4, y, w - 8); // maxWidth = w - 8
    }

    // 9. Orchestrator gap labels: 'idle Xms' in dark spaces > 200px
    const spansBySession = new Map();
    for (const span of state.spans) {
      const sid = span.session_id;
      if (!spansBySession.has(sid)) spansBySession.set(sid, []);
      spansBySession.get(sid).push(span);
    }

    ctx.font      = 'italic 10px "SF Mono", monospace';
    ctx.fillStyle = '#8b949e';
    ctx.textAlign = 'center';

    for (const [sid, spans] of spansBySession) {
      const rowIdx = rowMap.get(sid);
      if (rowIdx === undefined) continue;
      const sorted = spans.slice().sort((a, b) => (a.start_ms || 0) - (b.start_ms || 0));
      for (let i = 0; i < sorted.length - 1; i++) {
        const gapStartMs  = sorted[i].end_ms || 0;
        const gapEndMs    = sorted[i + 1].start_ms || 0;
        const gapDuration = gapEndMs - gapStartMs;
        if (gapDuration <= 0) continue;
        const gapX1 = gapStartMs / ts - scrollL;
        const gapX2 = gapEndMs   / ts - scrollL;
        const gapW  = gapX2 - gapX1;
        if (gapW <= 200) continue;      // only label gaps > 200px
        if (gapX2 < 0 || gapX1 > cw) continue;
        const midX = (gapX1 + gapX2) / 2;
        const y    = rowIdx * ROW_H + ROW_H / 2;
        ctx.fillText(`idle ${_formatMs(gapDuration)}`, midX, y);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Private: heatmap rendering
  // ---------------------------------------------------------------------------

  /**
   * Bucketize spans by cost into 4px-wide columns.
   * Fills each column with Anthropic purple (rgba(123,47,190, opacity)).
   * Marks the peak bucket with an amber border.
   */
  #renderHeatmap(spans, ts, scrollL) {
    const el = this._root.querySelector('#heatmap');
    if (!el) return;

    if (!spans || spans.length === 0) {
      el.innerHTML = '';
      return;
    }

    const colW = 4; // px per bucket
    const containerW = el.clientWidth || 800;
    const numCols = Math.ceil(containerW / colW);
    const buckets = new Float64Array(numCols);

    for (const span of spans) {
      const cost = span.cost_usd || 0;
      if (cost <= 0) continue;
      // Map the midpoint of the span to a pixel column
      const midMs  = ((span.start_ms || 0) + (span.end_ms || 0)) / 2;
      const px     = (midMs - scrollL) / ts;
      const col    = Math.floor(px / colW);
      if (col >= 0 && col < numCols) {
        buckets[col] += cost;
      }
    }

    // Find peak bucket for normalisation
    let peak = 0;
    let peakIdx = -1;
    for (let i = 0; i < numCols; i++) {
      if (buckets[i] > peak) { peak = buckets[i]; peakIdx = i; }
    }

    // Build HTML
    let html = '';
    for (let i = 0; i < numCols; i++) {
      if (buckets[i] <= 0) continue;
      const opacity = peak > 0 ? Math.max(0.08, buckets[i] / peak) : 0;
      const isAmber = i === peakIdx;
      const border  = isAmber ? 'border:1px solid #f59e0b;' : '';
      html += `<div style="position:absolute;left:${i * colW}px;top:0;width:${colW}px;height:100%;background:rgba(123,47,190,${opacity.toFixed(3)});${border}box-sizing:border-box;"></div>`;
    }
    el.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // Private: ruler rendering
  // ---------------------------------------------------------------------------

  /**
   * Adaptive tick rendering — Chrome DevTools style.
   * Selects a tick interval from NICE_INTERVALS so ~8 ticks fit the visible
   * window, then draws only ticks in the visible range (scrollL…scrollL+W).
   */
  #renderRuler(spans, ts, scrollL) {
    const el = this._root.querySelector('#ruler');
    if (!el) return;

    const containerW = el.clientWidth || 800;

    // Visible time window in ms
    const visibleMs = containerW * ts;

    // Target ~8 ticks across the view; snap to nearest nice interval
    const rawInterval = visibleMs / 8;
    const tickIntervalMs = NICE_INTERVALS.find(v => v >= rawInterval)
      || NICE_INTERVALS[NICE_INTERVALS.length - 1];

    // Convert scroll offset to ms
    const scrollLeftMs = scrollL * ts;
    const lastTickMs   = scrollLeftMs + visibleMs;

    // First tick at or after scrollLeftMs
    const firstTick = Math.ceil(scrollLeftMs / tickIntervalMs) * tickIntervalMs;

    let html = '';
    for (let ms = firstTick; ms <= lastTickMs + tickIntervalMs; ms += tickIntervalMs) {
      const px = (ms - scrollLeftMs) / ts;
      if (px < 0 || px > containerW) continue;
      html += `<div class="tick" style="left:${px.toFixed(1)}px;">` +
        `<div class="tick-line"></div>` +
        `<div class="tick-label">${_formatRulerLabel(ms, tickIntervalMs)}</div>` +
        `</div>`;
    }
    el.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // Private: event handlers
  // ---------------------------------------------------------------------------

  /** Wheel on ruler: cursor-centred zoom. */
  #onRulerWheel(e) {
    e.preventDefault();

    const el  = this._root.querySelector('#ruler');
    const rect = el ? el.getBoundingClientRect() : { left: 0 };
    const cursorPx = e.clientX - rect.left;

    // Time at cursor before zoom
    const msAtCursor = (cursorPx + state.scrollLeft) * state.timeScale;

    // Zoom factor
    const factor = e.deltaY > 0 ? 1.15 : 0.87;
    state.timeScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, state.timeScale * factor));

    // Adjust scrollLeft so the same ms stays under cursor
    state.scrollLeft = Math.max(0, msAtCursor / state.timeScale - cursorPx);

    renderAll();
  }

  /** Canvas click: hit-test spans, dispatch 'span-select' CustomEvent. */
  #onCanvasClick(e) {
    if (!this.#canvas) return;
    const rect   = this.#canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const ts      = state.timeScale;
    const scrollL = state.scrollLeft;
    const rowMap  = state.sessionData
      ? _rowIndexMap(state.sessionData, state.expandedSessions)
      : new Map();

    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue;

      const x        = (span.start_ms || 0) / ts - scrollL;
      const duration = Math.max(0, (span.end_ms || 0) - (span.start_ms || 0));
      const w        = Math.max(2, duration / ts);
      const y        = rowIdx * ROW_H + (ROW_H - SPAN_H) / 2;

      if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + SPAN_H) {
        this.dispatchEvent(new CustomEvent('span-select', {
          bubbles:  true,
          composed: true,
          detail:   { span },
        }));
        return;
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Private: styles
  // ---------------------------------------------------------------------------

  #styles() {
    return `
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
      #heatmap {
        height: 20px;
        position: relative;
        overflow: hidden;
        flex-shrink: 0;
        background: var(--bg, #0d1117);
      }
      #ruler {
        height: 28px;
        position: relative;
        overflow: hidden;
        flex-shrink: 0;
        background: var(--surface, #161b22);
        border-bottom: 1px solid var(--border, #30363d);
        cursor: ew-resize;
      }
      .tick {
        position: absolute;
        top: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        transform: translateX(-50%);
      }
      .tick-line {
        width: 1px;
        height: 8px;
        background: var(--border, #30363d);
      }
      .tick-label {
        font-size: 10px;
        color: var(--text-muted, #8b949e);
        white-space: nowrap;
        text-align: center;
        margin-top: 2px;
      }
      #canvas-wrap {
        flex: 1;
        position: relative;
        overflow: hidden;
      }
      canvas {
        display: block;
        cursor: grab;
      }
    `;
  }
}

customElements.define('acv-timeline', AcvTimeline);

// =============================================================================
// Section 9: Custom element — AcvDetail  (full implementation)
// Detail drawer shown at the bottom when a span is selected.
// Shadow DOM component with timing, token, cost rows and I/O blocks.
// =============================================================================

class AcvDetail extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this.update());
    this.update();
  }

  /** Property setter: called by AcvTimeline when selectedSpan changes. */
  set data(_) {
    this.update();
  }

  /** Main render method — renders nothing (hidden) when span is null. */
  update() {
    const span = state.selectedSpan;
    render(html`
      <style>${this.#styles()}</style>
      ${span ? html`
        <div class="panel">
          <div class="header">
            <span class="title">${this.#titleFor(span)}</span>
            <button class="close-btn" @click=${() => this.#onClose()}>✕</button>
          </div>
          <div class="grid">
            ${this.#timingRow(span)}
            ${span.type === 'llm' || span.model ? this.#llmRows(span) : ''}
            ${span.type === 'tool' ? this.#toolRows(span) : ''}
          </div>
          ${this.#ioBlock('INPUT', span.input)}
          ${this.#ioBlock('OUTPUT', span.output)}
        </div>
      ` : html`<div class="hidden"></div>`}
    `, this._root);
  }

  // ---------------------------------------------------------------------------
  // Private: title for the detail panel header
  // ---------------------------------------------------------------------------

  /**
   * Returns `{ ok, icon, color }` for a span's success state.
   * Centralises the success indicator contract used by #titleFor and #toolRows.
   */
  #successDisplay(span) {
    const ok    = span.success !== false;
    const icon  = ok ? '✓' : '✗';
    const color = ok ? '#3fb950' : '#f85149';
    return { ok, icon, color };
  }

  /** Returns the header title for a span based on its type. */
  #titleFor(span) {
    if (span.type === 'thinking') {
      return html`<span style="color:#a78bfa">thinking</span>`;
    }
    if (span.type === 'tool') {
      const { icon, color } = this.#successDisplay(span);
      return html`${span.tool_name || 'tool'} <span style="color:${color}">${icon}</span>`;
    }
    // LLM span: provider/model
    const parts = [span.provider, span.model].filter(Boolean);
    return parts.join('/') || span.name || 'span';
  }

  // ---------------------------------------------------------------------------
  // Private: grid rows
  // ---------------------------------------------------------------------------

  /** Renders a timing row: start → end (duration) using _formatMs. */
  #timingRow(span) {
    const startMs  = span.start_ms || 0;
    const endMs    = span.end_ms   || 0;
    const duration = Math.max(0, endMs - startMs);
    return html`
      <span class="label">time</span>
      <span class="value">${_formatMs(startMs)} → ${_formatMs(endMs)} (${_formatMs(duration)})</span>
    `;
  }

  /** Renders LLM-specific rows: tokens, cache tokens (conditional), cost. */
  #llmRows(span) {
    const inputTok  = span.input_tokens  || 0;
    const outputTok = span.output_tokens || 0;
    const total     = inputTok + outputTok;
    return html`
      <span class="label">in tokens</span>  <span class="value">${inputTok}</span>
      <span class="label">out tokens</span> <span class="value">${outputTok}</span>
      ${span.cache_read_tokens  ? html`<span class="label">cache read</span>  <span class="value">${span.cache_read_tokens}</span>`  : ''}
      ${span.cache_write_tokens ? html`<span class="label">cache write</span> <span class="value">${span.cache_write_tokens}</span>` : ''}
      <span class="label">total tok</span>  <span class="value">${total}</span>
      ${span.cost_usd != null ? html`<span class="label">cost</span> <span class="value">$${span.cost_usd.toFixed(6)}</span>` : ''}
    `;
  }

  /** Renders tool-specific rows: duration and success indicator. */
  #toolRows(span) {
    const duration        = _formatMs(Math.max(0, (span.end_ms || 0) - (span.start_ms || 0)));
    const { icon, color } = this.#successDisplay(span);
    return html`
      <span class="label">duration</span> <span class="value">${duration}</span>
      <span class="label">success</span>  <span class="value" style="color:${color}">${icon}</span>
    `;
  }

  // ---------------------------------------------------------------------------
  // Private: I/O blocks
  // ---------------------------------------------------------------------------

  /**
   * Renders an INPUT or OUTPUT block.
   * - Stringifies non-string values with JSON.stringify
   * - Truncates at IO_TRUNCATE chars with '…' suffix
   * - Provides a 'show more' link that reveals the full text
   */
  #ioBlock(label, value) {
    if (value == null) return '';
    const str       = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    const truncated = str.length > IO_TRUNCATE;
    const display   = truncated ? str.slice(0, IO_TRUNCATE) + '…' : str;

    const handleShowMore = (e) => {
      e.preventDefault();
      const block = e.target.closest('.io-block');
      const pre   = block?.querySelector('pre');
      if (pre) pre.textContent = str;
      e.target.remove();
    };

    return html`
      <div class="io-block">
        <div class="io-label">${label}</div>
        <div class="io-content">
          <pre>${display}</pre>
          ${truncated ? html`<a class="show-more" href="#" @click=${handleShowMore}>show more</a>` : ''}
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Private: close handler
  // ---------------------------------------------------------------------------

  /** Dispatches 'detail-close' event (bubbles + composed). */
  #onClose() {
    this.dispatchEvent(new CustomEvent('detail-close', {
      bubbles:  true,
      composed: true,
    }));
  }

  // ---------------------------------------------------------------------------
  // Private: styles
  // ---------------------------------------------------------------------------

  #styles() {
    return `
      :host { display: block; }
      .hidden { display: none; }
      .panel {
        background: #161b22;
        border-top: 1px solid var(--border, #30363d);
        max-height: 40vh;
        overflow-y: auto;
        padding: 10px 14px;
        box-sizing: border-box;
        font-family: "SF Mono", Consolas, Monaco, monospace;
        font-size: 12px;
        color: var(--text, #e6edf3);
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
      }
      .title { font-weight: 600; }
      .close-btn {
        background: none;
        border: none;
        color: var(--text-muted, #8b949e);
        cursor: pointer;
        font-size: 14px;
        padding: 2px 4px;
        border-radius: 3px;
      }
      .close-btn:hover { color: var(--text, #e6edf3); }
      .grid {
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 4px 12px;
        margin-bottom: 10px;
      }
      .label { color: var(--text-muted, #8b949e); }
      .io-block { margin-top: 8px; }
      .io-label {
        text-transform: uppercase;
        font-size: 10px;
        color: var(--text-muted, #8b949e);
        margin-bottom: 4px;
        letter-spacing: 0.05em;
      }
      .io-content pre {
        margin: 0;
        background: var(--surface-alt, #21262d);
        padding: 6px 8px;
        border-radius: 4px;
        overflow: auto;
        max-height: 80px;
        white-space: pre-wrap;
        word-break: break-all;
        font-size: 11px;
      }
      .show-more {
        display: inline-block;
        margin-top: 4px;
        color: var(--accent, #58a6ff);
        font-size: 11px;
        text-decoration: none;
        cursor: pointer;
      }
      .show-more:hover { text-decoration: underline; }
    `;
  }
}

customElements.define('acv-detail', AcvDetail);

// =============================================================================
// Section 10: loadSession helper
// =============================================================================

async function loadSession(id) {
  state.loading = true;
  renderAll(); // immediately show loading state

  try {
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
  } finally {
    state.loading = false;
    renderAll();
  }
}

// =============================================================================
// Section 11: init — entry point
// Wires toolbar CustomEvents to state mutations and kicks off initial data load.
// Also wires keyboard shortcuts for zoom/pan.
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

  // Wire timeline events: span-select and detail-close
  const timeline = document.querySelector('acv-timeline');
  if (timeline) {
    // Wire: span-select → set state.selectedSpan and call renderAll()
    timeline.addEventListener('span-select', e => {
      state.selectedSpan = e.detail.span;
      renderAll();
    });

    // Wire: detail-close → clear state.selectedSpan and call renderAll()
    timeline.addEventListener('detail-close', () => {
      state.selectedSpan = null;
      renderAll();
    });
  }

  // ---------------------------------------------------------------------------
  // Keyboard shortcuts: W/S zoom, A/D pan, Escape close detail
  // Shift key gives 3× speed.  Skips when target is INPUT/SELECT/TEXTAREA.
  // ---------------------------------------------------------------------------
  document.addEventListener('keydown', e => {
    const tag = e.target?.tagName;
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;

    const shift = e.shiftKey ? 3 : 1;

    switch (e.code) {
      case 'KeyW':
      case 'Equal': // = key (zoom in)
        e.preventDefault();
        state.timeScale = Math.max(ZOOM_MIN, state.timeScale * Math.pow(0.7, shift));
        renderAll();
        break;

      case 'KeyS':
      case 'Minus': // - key (zoom out)
        e.preventDefault();
        state.timeScale = Math.min(ZOOM_MAX, state.timeScale * Math.pow(1.3, shift));
        renderAll();
        break;

      case 'KeyA':
      case 'ArrowLeft':
        e.preventDefault();
        state.scrollLeft = Math.max(0, state.scrollLeft - 150 * shift);
        renderAll();
        break;

      case 'KeyD':
      case 'ArrowRight':
        e.preventDefault();
        state.scrollLeft = state.scrollLeft + 150 * shift;
        renderAll();
        break;

      case 'Escape':
        state.selectedSpan = null;
        renderAll();
        break;
    }
  });

  // Initial data load
  state.loading = true;
  renderAll(); // immediately show loading state

  try {
    await fetchSessions();
    renderAll();

    if (state.sessions.length > 0) {
      await loadSession(state.sessions[0].session_id);
    }
  } catch (err) {
    console.error('Failed to load initial data:', err);
  } finally {
    state.loading = false;
    renderAll();
  }
}

document.addEventListener('DOMContentLoaded', init);
