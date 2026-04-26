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

const ZOOM_MIN = 0.05;  // very zoomed in
const ZOOM_MAX = 200;   // very zoomed out

const state = {
  sessions: [],           // accumulated root-session summaries (grows with load more)
  sessionsOffset: 0,      // next offset to fetch (for load-more pagination)
  sessionsHasMore: false, // true when more sessions are available server-side
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

async function fetchSessions(offset = 0) {
  const resp = await fetch(`/api/sessions?limit=25&offset=${offset}`);
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  const data = await resp.json();
  if (offset === 0) {
    state.sessions = data.sessions;
  } else {
    state.sessions = [...state.sessions, ...data.sessions];
  }
  state.sessionsOffset = data.next_offset;
  state.sessionsHasMore = data.has_more;
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
    <span class="toolbar-title">Amplifier Cost Viewer</span>
    <select id="session-select" aria-label="Select session">
      ${state.sessions.map(s => {
        const shortId = s.session_id.slice(0, 8);
        const nameStr = s.name ? `${s.name} (${shortId})` : shortId;
        const cost = s.total_cost_usd || 0;
        const inputTok = s.total_input_tokens || 0;
        const outputTok = s.total_output_tokens || 0;
        const tokStr = (inputTok + outputTok) > 0
          ? ` (${_fmtTokens(inputTok + outputTok)} tok)`
          : '';
        return `
        <option value="${s.session_id}"
          ${s.session_id === state.activeSessionId ? 'selected' : ''}>
          ${nameStr} — ${_formatDate(s.start_ts)} — $${cost.toFixed(2)}${tokStr}
        </option>
        `;
      }).join('')}
    </select>
    <span class="cost-total">All sessions: <strong>${costStr}</strong></span>
    <button id="refresh-btn" title="Refresh session list">&#8635;</button>
    <div class="zoom-controls">
      <button id="zoom-out-btn" title="Zoom out">\u2212</button>
      <span id="zoom-label">1\u00d7</span>
      <button id="zoom-in-btn" title="Zoom in">+</button>
    </div>
  `;

  // Append "Load more" sentinel option if the server has more sessions
  const select = document.getElementById('session-select');
  if (state.sessionsHasMore) {
    const totalKnown = state.total || state.sessions.length;
    const loadMore = document.createElement('option');
    loadMore.value = '__load_more__';
    loadMore.textContent = `\u2014 Load 25 more (${state.sessions.length} of ${totalKnown}) \u2014`;
    loadMore.disabled = false;
    select.appendChild(loadMore);
  }

  select.addEventListener('change', e => {
    const id = e.target.value;
    if (id === '__load_more__') {
      fetchSessions(state.sessionsOffset).then(() => {
        renderToolbar();
      }).catch(err => {
        console.error('Failed to load more sessions:', err);
        _showError(`Error: ${err.message}`);
      });
      return;
    }
    loadSession(id).catch(err => {
      console.error('Failed to switch session:', err);
      _showError(`Error: ${err.message}`);
    });
  });

  document.getElementById('refresh-btn').addEventListener('click', async () => {
    try {
      await fetch('/api/refresh', {method: 'POST'});  // clear server cache
      await fetchSessions(0);  // reset to page 1
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

  // Zoom buttons
  const zoomInBtn = document.getElementById('zoom-in-btn');
  const zoomOutBtn = document.getElementById('zoom-out-btn');
  if (zoomInBtn) zoomInBtn.addEventListener('click', () => _applyZoom(0.5, null));
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => _applyZoom(2.0, null));
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

  // Session cost span — $X.XX · Xtok
  const costSpan = document.createElement('span');
  costSpan.className = 'session-cost';
  const cost = node.total_cost_usd || 0;
  const inputTok = node.total_input_tokens || 0;
  const outputTok = node.total_output_tokens || 0;
  const tok = inputTok + outputTok;
  costSpan.textContent = tok > 0
    ? `$${cost.toFixed(2)} \u00b7 ${_fmtTokens(tok)}`
    : `$${cost.toFixed(4)}`;
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

      // Inline text label for wide bars (> 60px)
      if (w > 60) {
        const barLabel = _svgEl('text', {
          x: x + 4,
          y: SPAN_Y_OFF + 13,
          fill: 'rgba(255,255,255,0.85)',
          'font-size': 10,
          'font-family': 'monospace',
          'pointer-events': 'none',
        });
        if (span.type === 'llm' && (span.input_tokens || span.output_tokens)) {
          barLabel.textContent = `$${(span.cost_usd||0).toFixed(3)} \u00b7 ${span.input_tokens||0}in/${span.output_tokens||0}out`;
        } else if (span.type === 'tool') {
          barLabel.textContent = `${span.tool_name || ''} \u00b7 ${_formatMs((span.end_ms||0)-(span.start_ms||0))}`;
        }
        g.appendChild(barLabel);
      }
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

  // Pick tick interval based on visible time span, not total duration
  const ganttPanel = document.getElementById('gantt-panel');
  const visibleMs = (ganttPanel ? ganttPanel.clientWidth : 800) * (state.timeScale || 1);

  let tickInterval;
  if (visibleMs < 5000) tickInterval = 500;
  else if (visibleMs < 30000) tickInterval = 5000;
  else if (visibleMs < 120000) tickInterval = 30000;
  else if (visibleMs < 600000) tickInterval = 60000;
  else if (visibleMs < 3600000) tickInterval = 300000;
  else tickInterval = 900000;

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


function _fmtTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
  return String(n);
}


function _applyZoom(factor, cursorXPx) {
  const ganttRows = document.getElementById('gantt-rows');
  const oldScale = state.timeScale;
  const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, oldScale * factor));
  if (newScale === oldScale) return;

  // If we have a cursor position, keep that point fixed on screen
  let scrollAdjust = 0;
  if (cursorXPx != null && ganttRows) {
    const msAtCursor = cursorXPx * oldScale;
    const newXPx = msAtCursor / newScale;
    scrollAdjust = newXPx - cursorXPx;
  }

  state.timeScale = newScale;
  renderGantt();  // re-render with new scale

  // Restore scroll position adjusted for zoom
  if (ganttRows && scrollAdjust !== 0) {
    ganttRows.scrollLeft += scrollAdjust;
  }

  // Update zoom label: show as Xs or Xms per pixel
  const label = document.getElementById('zoom-label');
  if (label) {
    const msPerPx = newScale;
    if (msPerPx < 1) label.textContent = `${(1/msPerPx).toFixed(1)}px/ms`;
    else label.textContent = `${msPerPx.toFixed(0)}ms/px`;
  }
}


// RAF handle for debounced zoom re-render — prevents jank on fast scroll.
let _zoomRaf = null;

function _initGanttZoom() {
  // Zoom by scrolling on the TIME RULER (no modifier needed — like Chrome DevTools).
  // The gantt-rows area scrolls horizontally as normal.
  const ruler = document.getElementById('time-ruler');
  if (!ruler) return;

  ruler.style.cursor = 'ew-resize';

  ruler.addEventListener('wheel', e => {
    e.preventDefault();
    e.stopPropagation();
    const factor = e.deltaY > 0 ? 1.3 : (1 / 1.3);
    const ganttRows = document.getElementById('gantt-rows');
    const rect = ruler.getBoundingClientRect();
    const cursorX = e.clientX - rect.left + (ganttRows ? ganttRows.scrollLeft : 0);

    // Compute new scale immediately (cheap)
    const oldScale = state.timeScale;
    const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, oldScale * factor));
    if (newScale === oldScale) return;

    // Scroll-anchor: keep cursor x fixed on screen
    let scrollAdjust = 0;
    if (ganttRows) {
      const msAtCursor = cursorX * oldScale;
      scrollAdjust = msAtCursor / newScale - cursorX;
    }

    state.timeScale = newScale;

    // Update label immediately (cheap DOM write)
    const label = document.getElementById('zoom-label');
    if (label) {
      const mpp = newScale;
      label.textContent = mpp < 1 ? `${(1/mpp).toFixed(1)}px/ms` : `${mpp.toFixed(0)}ms/px`;
    }

    // Debounce the expensive SVG re-render to one frame
    if (_zoomRaf) cancelAnimationFrame(_zoomRaf);
    _zoomRaf = requestAnimationFrame(() => {
      renderGantt();
      if (ganttRows && scrollAdjust !== 0) {
        ganttRows.scrollLeft += scrollAdjust;
      }
      _zoomRaf = null;
    });
  }, { passive: false });
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

const IO_TRUNCATE = 500;


function selectSpan(span) {
  state.selectedSpan = span;
  renderDetail(span);
}


function renderDetail(span) {
  const panel = document.getElementById('detail-panel');
  panel.classList.remove('hidden');

  // Build content HTML for this span type
  let contentHtml = '';
  if (!span) {
    panel.innerHTML = '<div class="detail-resize-handle" id="detail-resize-handle"></div>';
    initDetailResize();
    return;
  }

  // Render into a temporary container to get the HTML string
  const tmp = document.createElement('div');
  const type = span.type || '';
  if (type === 'llm') {
    _detailLlm(tmp, span);
  } else if (type === 'tool') {
    _detailTool(tmp, span);
  } else if (type === 'thinking') {
    _detailThinking(tmp, span);
  } else if (type === 'gap') {
    _detailGap(tmp, span);
  }

  // Prepend the resize handle to the panel content
  panel.innerHTML = '<div class="detail-resize-handle" id="detail-resize-handle"></div>' + tmp.innerHTML;

  // Wire .detail-show-more buttons: click replaces content with data-fullText, removes button
  panel.querySelectorAll('.detail-show-more').forEach(btn => {
    btn.addEventListener('click', () => {
      const content = btn.previousElementSibling;
      if (content) content.textContent = btn.dataset.fullText;
      btn.remove();
    });
  });

  // Wire .detail-close button to _closeDetail
  const closeBtn = panel.querySelector('.detail-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', _closeDetail);
  }

  // Re-attach resize handle listener (re-created with innerHTML)
  initDetailResize();
}


function _detailLlm(panel, span) {
  const start = _formatMs(span.start_ms || 0);
  const end = _formatMs(span.end_ms || 0);
  const duration = _formatMs((span.end_ms || 0) - (span.start_ms || 0));

  let cacheHtml = '';
  if (span.cache_read_tokens != null) {
    cacheHtml += `<div class="detail-row"><span class="detail-label">cache_read</span> <span class="detail-value">${_esc(span.cache_read_tokens.toLocaleString())}</span></div>`;
  }
  if (span.cache_write_tokens != null) {
    cacheHtml += `<div class="detail-row"><span class="detail-label">cache_write</span> <span class="detail-value">${_esc(span.cache_write_tokens.toLocaleString())}</span></div>`;
  }

  const costStr = span.cost_usd != null ? `$${span.cost_usd.toFixed(6)}` : 'n/a';

  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title">${_esc(span.provider || '')}/${_esc(span.model || '')}</span>
      <button class="detail-close">\u2715</button>
    </div>
    <div class="detail-section">
      <div class="detail-row"><span class="detail-label">time</span> <span class="detail-value">${_esc(start)} \u2192 ${_esc(end)} (${_esc(duration)})</span></div>
      <div class="detail-row"><span class="detail-label">in</span> <span class="detail-value">${span.input_tokens != null ? _esc(span.input_tokens.toLocaleString()) : 'n/a'}</span></div>
      <div class="detail-row"><span class="detail-label">out</span> <span class="detail-value">${span.output_tokens != null ? _esc(span.output_tokens.toLocaleString()) : 'n/a'}</span></div>
      ${cacheHtml}
      <div class="detail-row"><span class="detail-label">total</span> <span class="detail-value">${((span.input_tokens || 0) + (span.output_tokens || 0) + (span.cache_read_tokens || 0)).toLocaleString()} tok</span></div>
      <div class="detail-row"><span class="detail-label">cost</span> <span class="detail-value">${_esc(costStr)}</span></div>
    </div>
    ${_ioBlock('INPUT', span.input_text)}
    ${_ioBlock('OUTPUT', span.output_text)}
  `;
}


function _detailTool(panel, span) {
  const start = _formatMs(span.start_ms || 0);
  const end = _formatMs(span.end_ms || 0);
  const duration = _formatMs((span.end_ms || 0) - (span.start_ms || 0));
  const ok = span.success ? '\u2713' : '\u2717';
  const okColor = span.success ? 'green' : 'red';
  const toolName = span.tool_name || span.name || '';

  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title">${_esc(toolName)} <span style="color:${okColor}">${ok}</span></span>
      <button class="detail-close">\u2715</button>
    </div>
    <div class="detail-section">
      <div class="detail-row"><span class="detail-label">time</span> <span class="detail-value">${_esc(start)} \u2192 ${_esc(end)} (${_esc(duration)})</span></div>
    </div>
    ${_ioBlock('INPUT', span.input)}
    ${_ioBlock('OUTPUT', span.output)}
  `;
}


function _detailThinking(panel, span) {
  const start = _formatMs(span.start_ms || 0);
  const end = _formatMs(span.end_ms || 0);
  const duration = _formatMs((span.end_ms || 0) - (span.start_ms || 0));

  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title" style="color:#6366F1">thinking</span>
      <button class="detail-close">\u2715</button>
    </div>
    <div class="detail-section">
      <div class="detail-row"><span class="detail-label">time</span> <span class="detail-value">${_esc(start)} \u2192 ${_esc(end)} (${_esc(duration)})</span></div>
    </div>
  `;
}


function _detailGap(panel, span) {
  const before = span.before;
  const after = span.after;

  const beforeMs = before ? (before.end_ms || 0) : 0;
  const afterMs = after ? (after.start_ms || 0) : (span.clickMs || 0);
  const gapDuration = _formatMs(Math.max(0, afterMs - beforeMs));

  const beforeLabel = before
    ? (_formatMs(before.start_ms || 0) + '\u2013' + _formatMs(before.end_ms || 0))
    : 'start';
  const afterLabel = after
    ? (_formatMs(after.start_ms || 0) + '\u2013' + _formatMs(after.end_ms || 0))
    : 'end';

  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title" style="color:#8b949e">orchestrator overhead</span>
      <button class="detail-close">\u2715</button>
    </div>
    <div class="detail-section">
      <div class="detail-row"><span class="detail-label">duration</span> <span class="detail-value">${_esc(gapDuration)}</span></div>
      <div class="detail-row"><span class="detail-label">between</span> <span class="detail-value">${_esc(beforeLabel)} and ${_esc(afterLabel)}</span></div>
    </div>
  `;
}


function _ioBlock(label, value) {
  if (value == null) return '';
  const str = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  const truncated = str.length > IO_TRUNCATE;
  const display = truncated ? str.slice(0, IO_TRUNCATE) + '\u2026' : str;
  const showMore = truncated
    ? `<button class="detail-show-more" data-full-text="${_esc(str)}">show more (${str.length} chars)</button>`
    : '';
  return `
    <div class="detail-io-block">
      <div class="detail-io-label">${_esc(label)}</div>
      <div class="detail-io-content" data-full-text="${_esc(str)}">${_esc(display)}</div>
      ${showMore}
    </div>
  `;
}


function _closeDetail() {
  document.getElementById('detail-panel').classList.add('hidden');
  state.selectedSpan = null;
}


function initDetailResize() {
  const handle = document.getElementById('detail-resize-handle');
  const panel = document.getElementById('detail-panel');
  if (!handle || !panel) return;

  let startY = 0, startH = 0;

  handle.addEventListener('mousedown', e => {
    startY = e.clientY;
    startH = panel.offsetHeight;

    const onMove = ev => {
      const delta = startY - ev.clientY;  // drag up = bigger panel
      const newH = Math.max(80, Math.min(window.innerHeight * 0.6, startH + delta));
      panel.style.height = newH + 'px';
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    e.preventDefault();
  });
}


function _esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
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
  // Sync zoom label to the computed initial scale immediately.
  const _initLabel = document.getElementById('zoom-label');
  if (_initLabel) _initLabel.textContent = `${state.timeScale.toFixed(0)}ms/px`;

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
  initDetailResize();  // attach resize handle if panel is already visible
  _initGanttZoom();   // wire scroll-wheel zoom on the Gantt panel

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
