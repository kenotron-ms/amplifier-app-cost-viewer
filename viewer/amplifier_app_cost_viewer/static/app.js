// =============================================================================
// Amplifier Cost Viewer — app.js  (v3 — Lit custom elements)
// =============================================================================
// Architecture:
//   <acv-toolbar>   — session selector, cost summary
//   <acv-body>      — canvas-based span renderer (main panel)
//   <acv-overview>  — minimap overview strip
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
const RULER_H     = 28;    // px ruler strip height
const SPAN_H      = 20;    // px span bar height
const HEATMAP_H   = 20;    // px heatmap row height
const IO_TRUNCATE = 500;   // chars before "show more"
const MIN_SPAN_MS = 100;   // minimum viewport span in milliseconds
const VIRTUAL_BUFFER = 5;  // extra rows to render above/below visible area

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
  scrollTop:       0,  // scrollTop: 0 — vertical scroll offset in CSS pixels (tree is scroll master)
  hasMore:         false, // whether more sessions can be loaded
  loading: false,          // true while fetchSession/fetchSpans in flight
  _zoomAnimRaf:    null,  // requestAnimationFrame handle for in-flight zoom animation
  totalDurationMs: 0,    // total session duration in ms (v3 viewport model)
  viewportStartMs: 0,    // viewport start time in ms (v3 viewport model)
  viewportEndMs:   0,    // viewport end time in ms (v3 viewport model)
  _animRaf:        null, // requestAnimationFrame handle for in-flight viewport animation
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

function renderAll() { notify(); }

// =============================================================================
// Section 3b: Coordinate helpers (v3 viewport model)
// =============================================================================

/**
 * Convert a time value in milliseconds to a canvas pixel x-position.
 * Uses state.viewportStartMs / viewportEndMs as the visible range.
 *
 * @param {number} ms      - time value in milliseconds
 * @param {number} canvasW - canvas width in pixels
 * @returns {number}       - pixel x-position
 */
function timeToPixel(ms, canvasW) {
  const span = state.viewportEndMs - state.viewportStartMs;
  if (span === 0) return 0;
  return (ms - state.viewportStartMs) / span * canvasW;
}

/**
 * Convert a canvas pixel x-position to a time value in milliseconds.
 * Uses state.viewportStartMs / viewportEndMs as the visible range.
 *
 * @param {number} px      - pixel x-position
 * @param {number} canvasW - canvas width in pixels
 * @returns {number}       - time value in milliseconds
 */
function pixelToTime(px, canvasW) {
  if (canvasW === 0) return state.viewportStartMs;
  return state.viewportStartMs + (px / canvasW) * (state.viewportEndMs - state.viewportStartMs);
}

/**
 * Return milliseconds per pixel for the current viewport.
 *
 * @param {number} canvasW - canvas width in pixels
 * @returns {number}       - ms per pixel
 */
function msPerPx(canvasW) {
  if (canvasW === 0) return 0;
  return (state.viewportEndMs - state.viewportStartMs) / canvasW;
}

/**
 * Overview coordinate — maps [0, totalDurationMs] to [0, canvasW].
 * Different from timeToPixel which maps [viewportStartMs, viewportEndMs].
 * ONLY used by AcvOverview. Never use timeToPixel in the overview.
 *
 * @param {number} ms      - time value in milliseconds
 * @param {number} canvasW - overview canvas width in CSS pixels
 * @returns {number}       - pixel x-position
 */
function ovTimeToPixel(ms, canvasW) {
  if (!state.totalDurationMs) return 0;
  return (ms / state.totalDurationMs) * canvasW;
}

/**
 * Set the viewport to the given time range, optionally animating the transition.
 * Enforces a minimum span of MIN_SPAN_MS to prevent extreme zoom.
 *
 * @param {number}  startMs - new viewport start in milliseconds
 * @param {number}  endMs   - new viewport end in milliseconds
 * @param {boolean} animate - if true (default), animate the transition
 */
function setViewport(startMs, endMs, animate = true) {
  // Enforce minimum span
  let span = endMs - startMs;
  if (span < MIN_SPAN_MS) {
    const mid = (startMs + endMs) / 2;
    startMs = mid - MIN_SPAN_MS / 2;
    endMs = mid + MIN_SPAN_MS / 2;
  }
  if (animate) {
    _animateViewport(startMs, endMs);
  } else {
    state.viewportStartMs = startMs;
    state.viewportEndMs = endMs;
    renderAll();
  }
}

/**
 * Animate state.viewportStartMs / viewportEndMs from their current values to
 * targetStart / targetEnd over 100ms using easeOutQuad easing.
 *
 * @param {number} targetStart - target viewport start in milliseconds
 * @param {number} targetEnd   - target viewport end in milliseconds
 */
function _animateViewport(targetStart, targetEnd) {
  const DURATION = 100; // ms
  const fromStart = state.viewportStartMs;
  const fromEnd   = state.viewportEndMs;
  const t0        = performance.now();

  // Cancel any in-flight viewport animation before starting a new one
  if (state._animRaf !== null) {
    cancelAnimationFrame(state._animRaf);
    state._animRaf = null;
  }

  function step(now) {
    const elapsed = now - t0;
    const t = Math.min(elapsed / DURATION, 1);
    // easeOutQuad: t * (2 - t)
    const eased = t * (2 - t);
    state.viewportStartMs = fromStart + (targetStart - fromStart) * eased;
    state.viewportEndMs   = fromEnd   + (targetEnd   - fromEnd)   * eased;
    renderAll();
    if (t < 1) {
      state._animRaf = requestAnimationFrame(step);
    } else {
      state.viewportStartMs = targetStart;
      state.viewportEndMs   = targetEnd;
      state._animRaf = null;
      renderAll();
    }
  }
  state._animRaf = requestAnimationFrame(step);
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
 * Format a duration in milliseconds as a human-readable string.
 * < 1000ms → '342ms'
 * < 60s    → '4.2s'
 * else     → '2m 15s'
 * Returns '—' for null/negative.
 */
function _formatDuration(ms) {
  if (ms == null || ms < 0) return '\u2014';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.round((ms % 60000) / 1000);
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
}

/**
 * Extract readable text from various content shapes:
 * - string → return as-is
 * - array of messages [{role, content}] → extract last user message content
 * - {role, content: [{type:'text', text:'...'}]} → extract text
 * - {role, content: [{type:'tool_use', name:'...'}]} → '[called: name]'
 * - null/undefined → '—'
 */
function _extractContent(value) {
  if (value == null) return '\u2014';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    // Array of messages [{role, content}] — find last user message
    const userMsgs = value.filter(m => m && m.role === 'user');
    const last = userMsgs.length > 0 ? userMsgs[userMsgs.length - 1] : value[value.length - 1];
    if (!last) return '\u2014';
    return _extractContent(last.content != null ? last.content : last);
  }
  if (typeof value === 'object') {
    if (Array.isArray(value.content)) {
      const parts = value.content.map(block => {
        if (block.type === 'text') return block.text;
        if (block.type === 'tool_use') return `[called: ${block.name}]`;
        return '';
      }).filter(Boolean);
      return parts.join('\n') || '\u2014';
    }
    if (value.content != null) return _extractContent(value.content);
    if (value.text != null) return value.text;
  }
  return String(value);
}

/**
 * Render tool input as 'key: value' lines for objects, as-is for strings, '—' for null.
 */
function _renderToolInput(input) {
  if (input == null) return '\u2014';
  if (typeof input === 'string') return input;
  if (typeof input === 'object' && !Array.isArray(input)) {
    const lines = Object.entries(input)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`);
    return lines.join('\n') || '\u2014';
  }
  return String(input);
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

/**
 * Walk the session tree and return visible nodes with their depth for indentation.
 * Like _visibleRows but returns {node, depth} objects so labels can be indented.
 *
 * @param {Object} node     - root session node (has .children array)
 * @param {Set}    expanded - set of expanded session IDs
 * @returns {Array}         - flat array of {node, depth} objects in display order
 */
function _visibleRowsWithDepth(node, expanded) {
  const rows = [];
  function walk(n, depth) {
    rows.push({ node: n, depth });
    if (expanded.has(n.session_id) && n.children?.length) {
      for (const child of n.children) walk(child, depth + 1);
    }
  }
  walk(node, 0);
  return rows;
}

/**
 * Animate state.timeScale from its current value to targetScale over 100ms
 * with ease-out cubic easing: eased = t * (2 - t).
 *
 * If anchorMs and anchorPx are provided, keeps that time position fixed at
 * that screen pixel throughout the animation (cursor-anchored zoom).
 * If null, only timeScale is interpolated and scrollLeft is left unchanged.
 *
 * @param {number}      targetScale - target ms-per-pixel value
 * @param {number|null} anchorMs    - millisecond time position to keep fixed
 * @param {number|null} anchorPx   - screen pixel position where anchorMs stays
 */
function _animateZoom(targetScale, anchorMs, anchorPx) {
  const DURATION = 100; // ms
  const startScale = state.timeScale;
  const startTime = performance.now();

  // Cancel any in-flight zoom animation before starting a new one
  if (state._zoomAnimRaf !== null) {
    cancelAnimationFrame(state._zoomAnimRaf);
    state._zoomAnimRaf = null;
  }

  function step(now) {
    const elapsed = now - startTime;
    const t = Math.min(elapsed / DURATION, 1);
    const eased = t * (2 - t); // ease-out cubic

    state.timeScale = startScale + (targetScale - startScale) * eased;

    if (anchorMs !== null && anchorPx !== null) {
      // Keep anchorMs fixed at anchorPx: scrollLeft = anchorMs/scale - anchorPx
      state.scrollLeft = Math.max(0, anchorMs / state.timeScale - anchorPx);
    }

    renderAll();

    if (t < 1) {
      state._zoomAnimRaf = requestAnimationFrame(step);
    } else {
      // Set exact final values
      state.timeScale = targetScale;
      if (anchorMs !== null && anchorPx !== null) {
        state.scrollLeft = Math.max(0, anchorMs / targetScale - anchorPx);
      }
      renderAll();
      state._zoomAnimRaf = null;
    }
  }

  state._zoomAnimRaf = requestAnimationFrame(step);
}

// =============================================================================
// Section 6: Custom element — AcvToolbar
// Session selector dropdown, total cost display, refresh button.
// Dispatches CustomEvents for all user actions (session-change,
// refresh, load-more) so that init() can wire them to state updates.
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

  _onRefresh() {
    this.dispatchEvent(new CustomEvent('refresh', { bubbles: true, composed: true }));
  }
}

customElements.define('acv-toolbar', AcvToolbar);

// =============================================================================
// =============================================================================
// Section 9: Custom element — AcvOverview
// Thin 60px strip above the detail drawer. Canvas minimap of compressed spans.
// =============================================================================

class AcvOverview extends HTMLElement {
  // ── Private canvas state ────────────────────────────────────────────────
  #canvas = null;
  #ctx = null;
  #rafId = null;
  #resizeObserver = null;
  // drag interaction state (reset per mousedown)
  #dragMode = null;
  #dragStartX = 0;
  #dragStartMs = null;

  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this.notify());
    this._render();
    requestAnimationFrame(() => {
      this.#ensureCanvas();
      this.#scheduleRedraw();
      this.#setupResizeObserver();
    });
  }

  disconnectedCallback() {
    if (this.#resizeObserver) {
      this.#resizeObserver.disconnect();
      this.#resizeObserver = null;
    }
    if (this.#rafId) {
      cancelAnimationFrame(this.#rafId);
      this.#rafId = null;
    }
  }

  /** Called on every state change to re-render template + canvas. */
  notify() {
    this._render();
    requestAnimationFrame(() => {
      this.#ensureCanvas();
      this.#scheduleRedraw();
    });
  }

  _render() {
    render(html`
      <style>
        :host {
          display: block;
          width: 100%;
          height: 60px;
          background: var(--surface, #161b22);
          border-bottom: 1px solid var(--border, #30363d);
          box-sizing: border-box;
          position: relative;
          overflow: hidden;
        }
        canvas {
          display: block;
          position: absolute;
          top: 0;
          left: 0;
        }
      </style>
      <canvas id="ov-canvas"></canvas>
    `, this._root);
  }

  #setupResizeObserver() {
    this.#resizeObserver = new ResizeObserver(() => {
      this.#ensureCanvas();
      this.#scheduleRedraw();
    });
    this.#resizeObserver.observe(this);
  }

  #ensureCanvas() {
    const canvas = this._root.getElementById('ov-canvas');
    if (!canvas) return;
    const dpr  = window.devicePixelRatio || 1;
    const rect = this.getBoundingClientRect();
    const cssW = Math.max(1, Math.round(rect.width));
    const cssH = Math.max(1, Math.round(rect.height));
    if (canvas.style.width !== cssW + 'px' || canvas.style.height !== cssH + 'px' ||
        canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
      canvas.style.width  = cssW + 'px';
      canvas.style.height = cssH + 'px';
      canvas.width  = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      this.#ctx    = canvas.getContext('2d');
      this.#ctx.scale(dpr, dpr);
      this.#canvas = canvas;
    } else if (!this.#ctx) {
      this.#ctx    = canvas.getContext('2d');
      this.#canvas = canvas;
    }
    // Wire pointer events once
    if (!canvas._v3wired) {
      this.#wireOverviewEvents(canvas);
      canvas._v3wired = true;
    }
  }

  #scheduleRedraw() {
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = requestAnimationFrame(() => {
      this.#rafId = null;
      this.#draw();
    });
  }

  #draw() {
    const ctx    = this.#ctx;
    const canvas = this.#canvas;
    if (!ctx || !canvas) return;
    const W = parseFloat(canvas.style.width)  || canvas.width  / (window.devicePixelRatio || 1);
    const H = parseFloat(canvas.style.height) || canvas.height / (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, W, H);

    if (!state.spans || state.spans.length === 0 || !state.totalDurationMs) return;

    const rowMap    = state.sessionData
      ? _rowIndexMap(state.sessionData, state.expandedSessions)
      : new Map();
    const totalRows = rowMap.size || 1;
    const rowH      = Math.min(8, H / totalRows);

    // Color-batched compressed span rectangles
    const batches = new Map();
    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue;
      const y = rowIdx * rowH;
      const x = ovTimeToPixel(span.start_ms || 0, W);
      const w = Math.max(1, ovTimeToPixel(span.end_ms || 0, W) - x);
      const color = span.color || '#64748B';
      if (!batches.has(color)) batches.set(color, []);
      batches.get(color).push({ x, y, w, h: rowH });
    }

    for (const [color, rects] of batches) {
      ctx.beginPath();
      for (const r of rects) ctx.rect(r.x, r.y, r.w, r.h);
      ctx.fillStyle = color;
      ctx.fill();
    }

    // Selection box overlay
    this.#drawSelectionBox(ctx, W, H);
  }

  #drawSelectionBox(ctx, W, H) {
    if (!state.totalDurationMs) return;
    const x1   = ovTimeToPixel(state.viewportStartMs, W);
    const x2   = ovTimeToPixel(state.viewportEndMs, W);
    const boxW = Math.max(4, x2 - x1);

    // Darken area outside selection
    ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
    ctx.fillRect(0, 0, x1, H);
    ctx.fillRect(x1 + boxW, 0, W - (x1 + boxW), H);

    // Selection box border
    ctx.strokeStyle = 'rgba(88, 166, 255, 0.9)';
    ctx.lineWidth = 1;
    ctx.strokeRect(x1 + 0.5, 0.5, boxW - 1, H - 1);

    // Resize handles — 4px-wide blue strips at left and right edges
    ctx.fillStyle = 'rgba(88, 166, 255, 0.9)';
    ctx.fillRect(x1, 0, 4, H);
    ctx.fillRect(x1 + boxW - 4, 0, 4, H);
  }

  #wireOverviewEvents(canvas) {
    const HANDLE_PX = 8;  // hit area pixels from edge (visual handle is 4px)

    canvas.addEventListener('mousedown', e => {
      const W  = canvas.width / (window.devicePixelRatio || 1);
      const x  = e.offsetX;
      const x1 = ovTimeToPixel(state.viewportStartMs, W);
      const x2 = ovTimeToPixel(state.viewportEndMs, W);

      this.#dragStartX  = x;
      this.#dragStartMs = { start: state.viewportStartMs, end: state.viewportEndMs };

      if (x < x1 - HANDLE_PX || x > x2 + HANDLE_PX) {
        // Click outside selection — jump viewport center to click position
        const clickMs = (x / W) * state.totalDurationMs;
        const half = (state.viewportEndMs - state.viewportStartMs) / 2;
        setViewport(clickMs - half, clickMs + half);
        this.#dragMode = null;
      } else if (x <= x1 + HANDLE_PX) {
        this.#dragMode = 'resize-left';
        canvas.style.cursor = 'ew-resize';
      } else if (x >= x2 - HANDLE_PX) {
        this.#dragMode = 'resize-right';
        canvas.style.cursor = 'ew-resize';
      } else {
        this.#dragMode = 'pan';
        canvas.style.cursor = 'grabbing';
      }
      e.preventDefault();
    });

    canvas.addEventListener('mousemove', e => {
      const W = canvas.width / (window.devicePixelRatio || 1);

      // Drag handling
      if (this.#dragMode) {
        const dx  = e.offsetX - this.#dragStartX;
        const dms = (dx / W) * state.totalDurationMs;

        if (this.#dragMode === 'pan') {
          setViewport(this.#dragStartMs.start + dms, this.#dragStartMs.end + dms, false);
        } else if (this.#dragMode === 'resize-left') {
          setViewport(this.#dragStartMs.start + dms, this.#dragStartMs.end, false);
        } else if (this.#dragMode === 'resize-right') {
          setViewport(this.#dragStartMs.start, this.#dragStartMs.end + dms, false);
        }
        return;
      }

      // Cursor feedback when not dragging
      const x  = e.offsetX;
      const x1 = ovTimeToPixel(state.viewportStartMs, W);
      const x2 = ovTimeToPixel(state.viewportEndMs, W);

      if ((x >= x1 - HANDLE_PX && x <= x1 + HANDLE_PX) ||
          (x >= x2 - HANDLE_PX && x <= x2 + HANDLE_PX)) {
        canvas.style.cursor = 'ew-resize';
      } else if (x > x1 && x < x2) {
        canvas.style.cursor = 'grab';
      } else {
        canvas.style.cursor = 'crosshair';
      }
    });

    const stopDrag = () => {
      if (this.#dragMode) {
        this.#dragMode = null;
      }
    };
    canvas.addEventListener('mouseup', stopDrag);
    canvas.addEventListener('mouseleave', stopDrag);
  }
}

customElements.define('acv-overview', AcvOverview);

// =============================================================================
// Section 9b: Custom element — AcvBody  (CSS Grid shell with labels)
// Two-column CSS Grid: 220px labels column + 1fr canvas column.
// Row 1: sticky ruler wrapper (spans both columns).
// Row 2: labels column (tree-like labels with depth indentation) + canvas column.
// Dispatches toggle-expand and session-select CustomEvents on label row clicks.
// =============================================================================

class AcvBody extends HTMLElement {
  // ── Private canvas state ────────────────────────────────────────────────
  #canvas = null;
  #ctx = null;
  #rulerCanvas = null;
  #rulerCtx = null;
  #rafId = null;
  #resizeObserver = null;
  #dragStartX = 0;
  #dragStartViewportStart = 0;
  #dragStartViewportEnd = 0;
  #isDragging = false;
  #hasDragged = false;
  #rowH   = ROW_H;    // actual rendered table row height (measured, may differ from ROW_H)
  #theadH = RULER_H;  // actual rendered thead height (measured, may differ from RULER_H)
  #firstVisible = 0;   // first row index in virtual window
  #lastVisible = 50;   // last row index in virtual window (initial guess)
  #totalRows = 0;      // total number of visible rows (updated each render)
  #renderRafId = null;  // requestAnimationFrame handle for throttled re-renders

  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this.notify());
    this._render();
    requestAnimationFrame(() => {
      this.#ensureCanvases();
      this.#scheduleRedraw();
      const wrap = this._root.getElementById('table-wrap');
      if (wrap) {
        wrap.addEventListener('scroll', () => {
          state.scrollTop = wrap.scrollTop;
          if (this.#computeVirtualWindow()) { this.#scheduleRender(); }
          this.#scheduleRedraw();
        });
      }
      this.#setupResizeObserver();
    });
  }

  disconnectedCallback() {
    if (this.#resizeObserver) {
      this.#resizeObserver.disconnect();
      this.#resizeObserver = null;
    }
    if (this.#rafId) {
      cancelAnimationFrame(this.#rafId);
      this.#rafId = null;
    }
    if (this.#renderRafId) {
      cancelAnimationFrame(this.#renderRafId);
      this.#renderRafId = null;
    }
  }

  /** Called on every state change to re-render Lit template + canvas. */
  notify() {
    this._render();
    // ResizeObserver will handle async resizing, but also call sync for immediate needs
    requestAnimationFrame(() => {
      this.#ensureCanvases();
      this.#scheduleRedraw();
    });
  }

  _render() {
    const sd = state.sessionData;
    const rows = sd ? _visibleRowsWithDepth(sd, state.expandedSessions) : [];
    this.#totalRows = rows.length;
    this.#computeVirtualWindow();
    const first = this.#firstVisible;
    const last = this.#lastVisible;
    const visibleSlice = rows.slice(first, last + 1);
    const topSpacerH = first * this.#rowH;
    const bottomSpacerH = Math.max(0, (rows.length - last - 1) * this.#rowH);

    render(html`
      <style>
        :host {
          display: flex;
          flex-direction: column;
          flex: 1;
          overflow: hidden;
          min-width: 0;
          box-sizing: border-box;
          font-family: "SF Mono", Consolas, Monaco, monospace;
          font-size: 12px;
          color: var(--text, #e6edf3);
          background: var(--bg, #0d1117);
        }
        .table-wrap {
          position: relative;
          overflow-y: auto;
          overflow-x: hidden;
          flex: 1;
          min-height: 0;
        }
        table {
          border-collapse: collapse;
          width: 100%;
          table-layout: fixed;
        }
        col.col-label { width: 220px; }
        col.col-canvas { width: auto; }
        .th-label {
          position: sticky; left: 0; top: 0; z-index: 3;
          width: 220px; height: ${RULER_H}px;
          background: #161b22;
          border-right: 1px solid #30363d;
          border-bottom: 1px solid #30363d;
        }
        .th-ruler {
          position: sticky; top: 0; z-index: 2;
          height: ${RULER_H}px; padding: 0;
          background: #161b22;
          border-bottom: 1px solid #30363d;
        }
        .th-ruler canvas { display: block; width: 100%; height: ${RULER_H}px; }
        .td-label {
          position: sticky; left: 0; z-index: 1;
          height: ${ROW_H}px; width: 220px;
          padding: 0 8px;
          font-size: 11px; font-family: "SF Mono", Consolas, Monaco, monospace;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
          border-right: 1px solid #30363d;
          border-bottom: 1px solid #21262d;
          color: #e6edf3;
          vertical-align: middle;
          cursor: pointer;
          user-select: none;
        }
        .td-label:hover { filter: brightness(1.15); }
        .td-label .label-toggle {
          display: inline-block;
          width: 14px;
          text-align: center;
          font-size: 10px;
          flex-shrink: 0;
        }
        .td-label .label-name {
          display: inline;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .td-label .label-cost {
          float: right;
          color: #3fb950;
          font-size: 10px;
          margin-left: 4px;
        }
        .td-canvas {
          height: ${ROW_H}px; padding: 0;
          border-bottom: 1px solid #21262d;
        }
        #main-canvas {
          position: absolute;
          cursor: grab;
          display: block;
        }
        #main-canvas.dragging { cursor: grabbing; }
      </style>
      <div class="table-wrap" id="table-wrap">
        <table>
          <colgroup>
            <col class="col-label">
            <col class="col-canvas">
          </colgroup>
          <thead>
            <tr>
              <th class="th-label"></th>
              <th class="th-ruler"><canvas id="ruler-canvas"></canvas></th>
            </tr>
          </thead>
          <tbody>
            <tr class="spacer-top" style="height: ${topSpacerH}px;"><td colspan="2"></td></tr>
            ${visibleSlice.map(({ node, depth }, sliceIdx) => {
              const absIdx = first + sliceIdx;
              const hasChildren = (node.children?.length ?? 0) > 0;
              const isExpanded = state.expandedSessions.has(node.session_id);
              const toggle = hasChildren ? (isExpanded ? '▾' : '▸') : '\u00a0';
              const cost = node.total_cost_usd || 0;
              const name = node.name || node.agent_name || node.session_id.slice(-8);
              const bg = absIdx % 2 === 0 ? '#0d1117' : '#161b22';
              const indent = 8 + depth * 14;
              return html`
                <tr class="data-row">
                  <td
                    class="td-label"
                    style="padding-left: ${indent}px; background: ${bg};"
                    title=${node.session_id}
                    @click=${() => this._onLabelClick(node.session_id, hasChildren)}
                  ><span class="label-cost">$${cost.toFixed(4)}</span><span class="label-toggle">${toggle}</span><span class="label-name">${name}</span></td>
                  <td class="td-canvas" style="background: ${bg};"></td>
                </tr>`;
            })}
            <tr class="spacer-bottom" style="height: ${bottomSpacerH}px;"><td colspan="2"></td></tr>
          </tbody>
        </table>
        <canvas id="main-canvas"></canvas>
      </div>
      <acv-detail></acv-detail>
    `, this._root);
  }

  // ── Canvas lifecycle ──────────────────────────────────────────────────────

  #setupResizeObserver() {
    if (this.#resizeObserver) this.#resizeObserver.disconnect();
    this.#resizeObserver = new ResizeObserver(() => {
      this.#ensureCanvases();
      this.#scheduleRedraw();
    });
    this.#resizeObserver.observe(this);
    const tbody = this._root.querySelector('tbody');
    if (tbody) this.#resizeObserver.observe(tbody);
  }

  #ensureCanvases() {
    const mc = this._root.getElementById('main-canvas');
    const rc = this._root.getElementById('ruler-canvas');
    const tableWrap = this._root.getElementById('table-wrap');
    const tbody = this._root.querySelector('tbody');
    const thRuler = this._root.querySelector('.th-ruler');
    if (!mc || !rc || !tableWrap || !tbody) return;

    const dpr = window.devicePixelRatio || 1;

    // MEASURE — don't compute
    const tbodyRect  = tbody.getBoundingClientRect();
    const wrapRect   = tableWrap.getBoundingClientRect();
    const rulerRect  = thRuler ? thRuler.getBoundingClientRect() : wrapRect;

    const canvasW = Math.max(1, Math.round(wrapRect.width  - 220));
    const canvasH = Math.max(1, Math.round(tbodyRect.height));
    const rulerW  = Math.max(1, Math.round(rulerRect.width));

    // Main canvas: CSS size = measured, pixel buffer = measured × dpr
    const mcCssW = canvasW + 'px';
    const mcCssH = canvasH + 'px';
    if (mc.style.width !== mcCssW || mc.style.height !== mcCssH ||
        mc.width !== Math.round(canvasW * dpr) || mc.height !== Math.round(canvasH * dpr)) {
      mc.style.width  = mcCssW;
      mc.style.height = mcCssH;
      mc.width  = Math.round(canvasW * dpr);
      mc.height = Math.round(canvasH * dpr);
      this.#ctx = mc.getContext('2d');
      this.#ctx.scale(dpr, dpr);
      this.#canvas = mc;
    } else if (!this.#ctx) {
      this.#ctx = mc.getContext('2d');
      this.#canvas = mc;
    }

    // Ruler canvas
    if (rc.style.width !== rulerW + 'px' ||
        rc.width !== Math.round(rulerW * dpr)) {
      rc.style.width  = rulerW + 'px';
      rc.style.height = RULER_H + 'px';
      rc.width  = Math.round(rulerW * dpr);
      rc.height = Math.round(RULER_H * dpr);
      this.#rulerCtx = rc.getContext('2d');
      this.#rulerCtx.scale(dpr, dpr);
      this.#rulerCanvas = rc;
    } else if (!this.#rulerCtx) {
      this.#rulerCtx = rc.getContext('2d');
      this.#rulerCanvas = rc;
    }

    // Measure actual rendered dimensions — border-bottom adds pixels the constant doesn't know about
    const theadEl = this._root.querySelector('thead');
    const firstTr = tbody.querySelector('tr.data-row');
    if (theadEl) {
      const measured = Math.round(theadEl.getBoundingClientRect().height);
      if (measured > 0) this.#theadH = measured;
    }
    if (firstTr) {
      const measured = Math.round(firstTr.getBoundingClientRect().height);
      if (measured > 0) this.#rowH = measured;
    }

    // Position canvas using measured thead height, not hardcoded RULER_H
    mc.style.top  = this.#theadH + 'px';
    mc.style.left = '220px';

    // Wire events once
    if (!mc._v3wired) { this.#wireCanvasEvents(mc); mc._v3wired = true; }
    if (!rc._v3wired) { this.#wireRulerEvents(rc);  rc._v3wired = true; }
  }

  #computeVirtualWindow() {
    const wrap = this._root.getElementById('table-wrap');
    if (!wrap || this.#totalRows === 0) {
      const changed = this.#firstVisible !== 0 || this.#lastVisible !== 0;
      this.#firstVisible = 0;
      this.#lastVisible = 0;
      return changed;
    }
    const scrollTop = wrap.scrollTop;
    const viewportH = wrap.clientHeight;
    const rowH = this.#rowH || ROW_H;
    const first = Math.max(0, Math.floor(scrollTop / rowH) - VIRTUAL_BUFFER);
    const last = Math.min(this.#totalRows - 1, Math.ceil((scrollTop + viewportH) / rowH) + VIRTUAL_BUFFER);
    const changed = first !== this.#firstVisible || last !== this.#lastVisible;
    this.#firstVisible = first;
    this.#lastVisible = last;
    return changed;
  }

  #scheduleRender() {
    if (this.#renderRafId) return;
    this.#renderRafId = requestAnimationFrame(() => {
      this.#renderRafId = null;
      this._render();
      this.#ensureCanvases();
      this.#scheduleRedraw();
    });
  }

  #scheduleRedraw() {
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = requestAnimationFrame(() => {
      this.#rafId = null;
      this.#draw();
      this.#drawRuler();
    });
  }

  // ── Gantt canvas draw ─────────────────────────────────────────────────────

  #draw() {
    const ctx    = this.#ctx;
    const canvas = this.#canvas;
    if (!ctx || !canvas) return;
    // Use CSS pixel dimensions, not canvas.width/canvas.height (those are DPR-scaled)
    const W = parseFloat(canvas.style.width) || canvas.width / (window.devicePixelRatio || 1);
    const H = parseFloat(canvas.style.height) || canvas.height / (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, W, H);

    const rowMap   = state.sessionData
      ? _rowIndexMap(state.sessionData, state.expandedSessions)
      : new Map();
    // Loading overlay
    if (state.loading) {
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle  = '#8b949e';
      ctx.font       = '14px monospace';
      ctx.textAlign  = 'center';
      ctx.fillText('Loading\u2026', W / 2, H / 2);
      ctx.textAlign  = 'left';
      return;
    }

    // Alternating row backgrounds — canvas is absolute and scrolls with container,
    // so row positions are absolute (no scrollTop subtraction needed).
    for (const [, rowIdx] of rowMap) {
      const y = rowIdx * this.#rowH;
      ctx.fillStyle = rowIdx % 2 === 0 ? '#0d1117' : '#161b22';
      ctx.fillRect(0, y, W, this.#rowH);
    }

    // Row separator lines — match table's border-bottom: 1px solid #21262d
    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (const [, rowIdx] of rowMap) {
      const y = Math.floor((rowIdx + 1) * this.#rowH) - 0.5;
      if (y >= 0 && y <= H) {
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
      }
    }
    ctx.stroke();

    if (!state.spans || state.spans.length === 0) return;

    // Vertical grid lines (same tick intervals as ruler)
    if (state.viewportEndMs > state.viewportStartMs) {
      const visMs       = state.viewportEndMs - state.viewportStartMs;
      const rawInterval = visMs / 8;
      const tickInt     = NICE_INTERVALS.find(v => v >= rawInterval)
                          || NICE_INTERVALS[NICE_INTERVALS.length - 1];
      const firstTick   = Math.ceil(state.viewportStartMs / tickInt) * tickInt;
      ctx.strokeStyle   = '#21262d';
      ctx.lineWidth     = 1;
      for (let t = firstTick; t <= state.viewportEndMs + tickInt; t += tickInt) {
        const x = timeToPixel(t, W);
        if (x < 0 || x > W) continue;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
        ctx.stroke();
      }
    }

    // Color-batched span rectangles
    const batches = new Map();
    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue;
      const y = rowIdx * this.#rowH + (this.#rowH - SPAN_H) / 2;
      if (y + SPAN_H < 0 || y > H + SPAN_H) continue;
      const x = timeToPixel(span.start_ms || 0, W);
      const w = Math.max(2, timeToPixel(span.end_ms || 0, W) - x);
      if (x + w < -10 || x > W + 4) continue;
      const color = span.color || '#64748B';
      if (!batches.has(color)) batches.set(color, []);
      batches.get(color).push({ x, y, w, h: SPAN_H });
    }

    for (const [color, rects] of batches) {
      ctx.beginPath();
      for (const r of rects) ctx.rect(r.x, r.y, r.w, r.h);
      ctx.fillStyle = color;
      ctx.fill();
    }

    // Text labels on wide spans (>60 px)
    ctx.font         = '10px monospace';
    ctx.textBaseline = 'middle';
    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue;
      const x = timeToPixel(span.start_ms || 0, W);
      const w = timeToPixel(span.end_ms || 0, W) - x;
      if (w < 60) continue;
      const y = rowIdx * this.#rowH + this.#rowH / 2;
      if (y < 0 || y > H + this.#rowH) continue;
      const label = span.type === 'llm'
        ? `${span.model || ''} \u00b7 $${(span.cost_usd || 0).toFixed(3)}`
        : (span.tool_name || span.type || '');
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.save();
      ctx.rect(x + 2, y - SPAN_H / 2, w - 4, SPAN_H);
      ctx.clip();
      ctx.fillText(label, x + 4, y, w - 8);
      ctx.restore();
    }
  }

  // ── Ruler canvas draw ─────────────────────────────────────────────────────

  #drawRuler() {
    const ctx    = this.#rulerCtx;
    const canvas = this.#rulerCanvas;
    if (!ctx || !canvas) return;
    // Use CSS pixel dimensions, not canvas.width (that is DPR-scaled)
    const W = parseFloat(canvas.style.width) || canvas.width / (window.devicePixelRatio || 1);
    const H = 28;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#161b22';
    ctx.fillRect(0, 0, W, H);

    if (state.viewportEndMs <= state.viewportStartMs) return;
    const visibleMs   = state.viewportEndMs - state.viewportStartMs;
    const rawInterval = visibleMs / 8;
    const tickInterval = NICE_INTERVALS.find(v => v >= rawInterval)
                         || NICE_INTERVALS[NICE_INTERVALS.length - 1];

    const firstTick = Math.ceil(state.viewportStartMs / tickInterval) * tickInterval;
    ctx.font      = '10px monospace';
    ctx.textAlign = 'center';
    for (let t = firstTick; t <= state.viewportEndMs + tickInterval; t += tickInterval) {
      const x = timeToPixel(t, W);
      if (x < 0 || x > W) continue;
      ctx.strokeStyle = '#30363d';
      ctx.lineWidth   = 1;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 8);
      ctx.stroke();
      ctx.fillStyle = '#8b949e';
      ctx.fillText(_formatRulerLabel(t, tickInterval), x, 22);
    }
    ctx.textAlign = 'left';
  }

  // ── Canvas event handlers ─────────────────────────────────────────────────

  #wireCanvasEvents(canvas) {
    // Drag to pan viewport
    canvas.addEventListener('mousedown', e => {
      if (e.button !== 0) return;
      this.#dragStartX              = e.clientX;
      this.#dragStartViewportStart  = state.viewportStartMs;
      this.#dragStartViewportEnd    = state.viewportEndMs;
      this.#isDragging              = true;
      this.#hasDragged              = false;
      canvas.style.cursor           = 'grabbing';
      e.preventDefault();
    });

    canvas.addEventListener('mousemove', e => {
      if (!this.#isDragging) return;
      const delta = e.clientX - this.#dragStartX;
      if (Math.abs(delta) > 4) this.#hasDragged = true;
      if (this.#hasDragged) {
        const W      = canvas.width / (window.devicePixelRatio || 1);
        const msDelta = (delta / W) * (this.#dragStartViewportEnd - this.#dragStartViewportStart);
        setViewport(
          this.#dragStartViewportStart - msDelta,
          this.#dragStartViewportEnd   - msDelta,
          false,
        );
      }
    });

    const stopDrag = () => {
      this.#isDragging    = false;
      canvas.style.cursor = 'grab';
    };
    canvas.addEventListener('mouseup',    e => { if (this.#hasDragged) e.stopPropagation(); stopDrag(); });
    canvas.addEventListener('mouseleave', stopDrag);

    // Cmd/Ctrl + scroll → zoom; plain scroll → route to table-wrap
    canvas.addEventListener('wheel', e => {
      if (!e.ctrlKey && !e.metaKey) {
        // Vertical scroll: forward to the scrollable table-wrap container
        const wrap = this._root.getElementById('table-wrap');
        if (wrap) wrap.scrollTop += e.deltaY;
        e.preventDefault();
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      const factor    = e.deltaY > 0 ? 1.3 : (1 / 1.3);
      const W         = canvas.width / (window.devicePixelRatio || 1);
      const rect      = canvas.getBoundingClientRect();
      const cursorX   = e.clientX - rect.left;
      const cursorMs  = pixelToTime(cursorX, W);
      const visibleMs = state.viewportEndMs - state.viewportStartMs;
      const newVisible = Math.max(100, visibleMs * factor);
      const ratio     = (cursorMs - state.viewportStartMs) / visibleMs;
      setViewport(
        cursorMs - ratio * newVisible,
        cursorMs + (1 - ratio) * newVisible,
      );
    }, { passive: false });

    // Click to select a span
    canvas.addEventListener('click', e => {
      if (this.#hasDragged) return;
      const W        = canvas.width / (window.devicePixelRatio || 1);
      const rect     = canvas.getBoundingClientRect();
      const clickX   = e.clientX - rect.left;
      const clickMs  = pixelToTime(clickX, W);
      const clickY   = e.clientY - rect.top;
      const rowMap   = state.sessionData
        ? _rowIndexMap(state.sessionData, state.expandedSessions)
        : new Map();
      const clickRow = Math.floor(clickY / this.#rowH);
      let hit = null;
      for (const span of (state.spans || [])) {
        const rowIdx = rowMap.get(span.session_id);
        if (rowIdx !== clickRow) continue;
        if (clickMs >= (span.start_ms || 0) && clickMs <= (span.end_ms || 0)) {
          hit = span;
          break;
        }
      }
      state.selectedSpan = hit;
      renderAll();
    });
  }

  #wireRulerEvents(ruler) {
    ruler.style.cursor = 'ew-resize';
    ruler.addEventListener('wheel', e => {
      e.preventDefault();
      const factor    = e.deltaY > 0 ? 1.3 : (1 / 1.3);
      const W         = ruler.width / (window.devicePixelRatio || 1);
      const rect      = ruler.getBoundingClientRect();
      const cursorX   = e.clientX - rect.left;
      const cursorMs  = pixelToTime(cursorX, W);
      const visibleMs = state.viewportEndMs - state.viewportStartMs;
      const newVisible = Math.max(100, visibleMs * factor);
      const ratio     = cursorMs / (state.viewportEndMs - state.viewportStartMs);
      setViewport(
        cursorMs - ratio * newVisible,
        cursorMs + (1 - ratio) * newVisible,
      );
    }, { passive: false });
  }

  _onLabelClick(sid, hasChildren) {
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

customElements.define('acv-body', AcvBody);

// =============================================================================
// Section 10: Custom element — AcvDetail  (full implementation)
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

  /** Property setter: triggers re-render when selectedSpan changes. */
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
          <div class="detail-stats">
            ${this.#statsBlock(span)}
          </div>
          ${span.type !== 'thinking' ? html`
            ${this.#contentBlock('INPUT', span.input, span.type)}
            ${this.#contentBlock('OUTPUT', span.output, span.type)}
          ` : ''}
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
  // Private: stats block
  // ---------------------------------------------------------------------------

  /**
   * Renders a stats grid for the span.
   * - thinking spans: Duration only
   * - tool spans: Duration + Status
   * - LLM spans: Duration, Cost, Input tok, Output tok, optional Cache read/write
   */
  #statsBlock(span) {
    const durationMs = Math.max(0, (span.end_ms || 0) - (span.start_ms || 0));
    const dur = _formatDuration(durationMs);

    if (span.type === 'thinking') {
      return html`
        <div class="stat">
          <div class="stat-label">DURATION</div>
          <div class="stat-value">${dur}</div>
        </div>
      `;
    }

    if (span.type === 'tool') {
      const { icon, color } = this.#successDisplay(span);
      return html`
        <div class="stat">
          <div class="stat-label">DURATION</div>
          <div class="stat-value">${dur}</div>
        </div>
        <div class="stat">
          <div class="stat-label">STATUS</div>
          <div class="stat-value" style="color:${color}">${icon}</div>
        </div>
      `;
    }

    // LLM span (default)
    const inputTok  = span.input_tokens  || 0;
    const outputTok = span.output_tokens || 0;
    return html`
      <div class="stat">
        <div class="stat-label">DURATION</div>
        <div class="stat-value">${dur}</div>
      </div>
      ${span.cost_usd != null ? html`
        <div class="stat">
          <div class="stat-label">COST</div>
          <div class="stat-value">$${span.cost_usd.toFixed(4)}</div>
        </div>
      ` : ''}
      <div class="stat">
        <div class="stat-label">INPUT TOK</div>
        <div class="stat-value">${inputTok.toLocaleString()}</div>
      </div>
      <div class="stat">
        <div class="stat-label">OUTPUT TOK</div>
        <div class="stat-value">${outputTok.toLocaleString()}</div>
      </div>
      ${span.cache_read_tokens ? html`
        <div class="stat">
          <div class="stat-label">CACHE READ</div>
          <div class="stat-value">${span.cache_read_tokens.toLocaleString()}</div>
        </div>
      ` : ''}
      ${span.cache_write_tokens ? html`
        <div class="stat">
          <div class="stat-label">CACHE WRITE</div>
          <div class="stat-value">${span.cache_write_tokens.toLocaleString()}</div>
        </div>
      ` : ''}
    `;
  }

  // ---------------------------------------------------------------------------
  // Private: content blocks
  // ---------------------------------------------------------------------------

  /**
   * Renders an INPUT or OUTPUT block.
   * - Uses _renderToolInput for tool inputs, _extractContent for everything else
   * - Truncates at IO_TRUNCATE (500 chars) with 'show more' link
   * - Uses pre-wrap for content display
   */
  #contentBlock(label, value, spanType) {
    if (value == null) return '';
    const str = (spanType === 'tool' && label === 'INPUT')
      ? _renderToolInput(value)
      : _extractContent(value);
    if (!str || str === '\u2014') return '';

    const truncated = str.length > IO_TRUNCATE;
    const display   = truncated ? str.slice(0, IO_TRUNCATE) + '\u2026' : str;

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
      .detail-stats {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 8px;
        margin-bottom: 10px;
      }
      .stat {
        background: var(--surface-alt, #21262d);
        border: 1px solid var(--border, #30363d);
        border-radius: 6px;
        padding: 6px 10px;
      }
      .stat-label {
        text-transform: uppercase;
        font-size: 9px;
        color: var(--text-muted, #8b949e);
        letter-spacing: 0.06em;
        margin-bottom: 2px;
      }
      .stat-value {
        font-size: 13px;
        font-weight: 600;
        color: var(--text, #e6edf3);
      }
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
        border: 1px solid var(--border, #30363d);
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
  renderAll();

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

    // Compute total duration and set viewport to show the full session
    state.totalDurationMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1000);
    setViewport(0, state.totalDurationMs, false);
  } finally {
    state.loading = false;
    renderAll();
  }
}

// =============================================================================
// Section 11: init — entry point  (v3)
// Wires toolbar CustomEvents to state mutations and kicks off initial data load.
// Body events (toggle-expand, session-select, detail-close) are wired on acv-body.
// Keyboard shortcuts use setViewport for zoom/pan.
// =============================================================================

async function init() {
  const toolbar = document.querySelector('acv-toolbar');

  // Wire toolbar events: session-change, refresh, load-more
  if (toolbar) {
    // Wire: session-change → load the selected session
    toolbar.addEventListener('session-change', async e => {
      try {
        await loadSession(e.detail.id);
      } catch (err) {
        console.error('Failed to switch session:', err);
      }
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

  // Wire body events on acv-body: toggle-expand, session-select, detail-close, span-select
  const body = document.querySelector('acv-body');
  if (body) {
    // Wire: toggle-expand → toggle expandedSessions set membership
    body.addEventListener('toggle-expand', e => {
      const id = e.detail.id;
      if (state.expandedSessions.has(id)) {
        state.expandedSessions.delete(id);
      } else {
        state.expandedSessions.add(id);
      }
      renderAll();
    });

    // Wire: session-select → update activeSessionId
    body.addEventListener('session-select', e => {
      state.activeSessionId = e.detail.id;
      renderAll();
    });

    // Wire: detail-close → clear selectedSpan
    body.addEventListener('detail-close', () => {
      state.selectedSpan = null;
      renderAll();
    });

    // Wire: span-select → set state.selectedSpan
    body.addEventListener('span-select', e => {
      state.selectedSpan = e.detail.span;
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
      case 'Equal': { // = key (zoom in, factor 0.7^shift)
        e.preventDefault();
        const zoomInFactor = Math.pow(0.7, shift);
        const ziSpan = state.viewportEndMs - state.viewportStartMs;
        const ziMid  = (state.viewportStartMs + state.viewportEndMs) / 2;
        const ziNew  = ziSpan * zoomInFactor;
        setViewport(ziMid - ziNew / 2, ziMid + ziNew / 2);
        break;
      }

      case 'KeyS':
      case 'Minus': { // - key (zoom out, factor 1.3^shift)
        e.preventDefault();
        const zoomOutFactor = Math.pow(1.3, shift);
        const zoSpan = state.viewportEndMs - state.viewportStartMs;
        const zoMid  = (state.viewportStartMs + state.viewportEndMs) / 2;
        const zoNew  = zoSpan * zoomOutFactor;
        setViewport(zoMid - zoNew / 2, zoMid + zoNew / 2);
        break;
      }

      case 'KeyA':
      case 'ArrowLeft': { // pan left (20% * shift of visible span)
        e.preventDefault();
        const panLSpan  = state.viewportEndMs - state.viewportStartMs;
        const panLDelta = panLSpan * 0.2 * shift;
        setViewport(state.viewportStartMs - panLDelta, state.viewportEndMs - panLDelta);
        break;
      }

      case 'KeyD':
      case 'ArrowRight': { // pan right (20% * shift of visible span)
        e.preventDefault();
        const panRSpan  = state.viewportEndMs - state.viewportStartMs;
        const panRDelta = panRSpan * 0.2 * shift;
        setViewport(state.viewportStartMs + panRDelta, state.viewportEndMs + panRDelta);
        break;
      }

      case 'Escape':
        state.selectedSpan = null;
        renderAll();
        break;
    }
  });

  // Initial data load: fetchSessions then loadSession first session
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
