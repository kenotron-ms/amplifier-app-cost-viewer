# Amplifier Cost Viewer v3 Design

## Goal

Rewrite the cost viewer frontend to replace fragile scroll-sync between two separate components with a CSS Grid layout that guarantees row alignment structurally, and replace the `timeScale`/`scrollLeft` state model with a clean millisecond viewport range.

---

## Background

The v2 frontend (`app.js`, ~1,761 lines) was built iteratively. Two separate components — `<acv-tree>` (labels) and `<acv-timeline>` (canvas) — are kept in visual sync via JavaScript scroll event listeners. This sync is fragile: any layout reflow, dynamic content change, or race condition can cause label rows to drift out of alignment with their canvas counterparts.

The zoom state (`timeScale` in ms/px, `scrollLeft` in px) is also implicitly coupled to canvas width. Changing zoom is not a single operation — it requires recomputing `scrollLeft` to keep the cursor anchored, updating the ruler, and animating all three quantities consistently. The result is multiple ad-hoc `_zoomAnimRaf` paths that are hard to reason about.

v3 eliminates both problems at the root:

1. **Layout:** One CSS Grid container owns labels + canvas in the same scroll container. Row N in labels equals row N in canvas by grid geometry, not by synchronization.
2. **Viewport state:** One pair of numbers — `viewportStartMs` and `viewportEndMs` — describes exactly what time range is visible. All coordinate math derives from this pair. Zoom and pan are both implemented by calling one function: `setViewport()`.

The Python backend (server.py, reader.py, pricing.py, all tests) is **entirely unchanged**.

---

## Approach

Replace the two-component tree+timeline layout with a single `<acv-body>` component that owns a CSS Grid containing both the labels column and the main canvas in the same scroll container. Add a new `<acv-overview>` component above the grid that gives a full-session compressed view with a draggable selection box representing the current viewport.

All viewport mutation goes through a single `setViewport(startMs, endMs, animate)` function. This becomes the single source of truth for zoom, pan, keyboard shortcuts, and overview drag gestures.

---

## Architecture

```
<div id="app">
  ┌─ <acv-toolbar> ──────────────────────────────────────┐
  │  Session picker · Total cost · ↺ Refresh             │
  └──────────────────────────────────────────────────────┘
  ┌─ <acv-overview> ─────────────────────────────────────┐
  │  Full-width canvas, 60px tall, always shows 0→total  │
  │  [░░░░████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░] │
  │        ↑ selection box = current viewport ↑          │
  └──────────────────────────────────────────────────────┘
  ┌─ <acv-body> ─────────────────────────────────────────┐
  │  ┌─ #detail-area (CSS Grid, overflow-y: auto) ──────┐│
  │  │ RULER (grid-column: 1/-1, position: sticky top:0)││
  │  │ ┌── 220px blank ──┬── ruler-canvas (ticks) ─────┐││
  │  │ └─────────────────┴─────────────────────────────┘││
  │  │ ┌── .labels-col ──┬── #main-canvas ─────────────┐││
  │  │ │ Session A       │ ████ $0.034                  │││
  │  │ │   └ Child 1     │     ████████████             │││
  │  │ │   └ Child 2     │         ████                 │││
  │  │ │ Langfuse Debug  │                  ████████    │││
  │  │ └─────────────────┴─────────────────────────────┘││
  │  └──────────────────────────────────────────────────┘│
  │  ┌─ <acv-detail> (slides up on span click) ─────────┐│
  │  │  Provider/model · Duration · Tokens · Cost · Text ││
  │  └──────────────────────────────────────────────────┘│
  └──────────────────────────────────────────────────────┘
```

---

## State Model

### What changes

| v2 | v3 | Reason |
|---|---|---|
| `state.timeScale` (ms/px) | removed | implicit coupling to canvas width |
| `state.scrollLeft` (px) | removed | coupled to timeScale, hard to animate cleanly |
| `state._zoomAnimRaf` | → `state._animRaf` | now animates ms range, not px offset |
| — | `state.totalDurationMs` | max `span.end_ms` for the loaded session |
| — | `state.viewportStartMs` | left edge of detail view in ms |
| — | `state.viewportEndMs` | right edge of detail view in ms |

### Full state shape

```javascript
const state = {
  // Unchanged from v2
  sessions,          // paginated session list
  sessionsOffset,    // pagination cursor
  sessionsHasMore,   // bool
  total,             // total cost across all sessions
  activeSessionId,   // currently selected session
  sessionData,       // raw API response for active session
  spans,             // processed flat span list
  expandedSessions,  // Set of expanded session IDs
  selectedSpan,      // span shown in detail panel
  scrollTop,         // vertical scroll position (px)
  loading,           // bool

  // NEW — replaces timeScale + scrollLeft + _zoomAnimRaf
  totalDurationMs: 0,      // full session duration (max span.end_ms)
  viewportStartMs: 0,      // left edge of the detail view in ms
  viewportEndMs:   0,      // right edge of the detail view in ms
  _animRaf:        null,   // RAF handle for in-flight viewport animation
};
```

### Coordinate math

All coordinate conversion derives from the viewport range. These are the only functions that should touch raw pixel ↔ ms conversion:

```javascript
// ms → canvas CSS pixel (detail view)
function timeToPixel(ms, canvasW) {
  return (ms - state.viewportStartMs)
       / (state.viewportEndMs - state.viewportStartMs)
       * canvasW;
}

// canvas CSS pixel → ms (detail view)
function pixelToTime(px, canvasW) {
  return state.viewportStartMs
       + (px / canvasW)
       * (state.viewportEndMs - state.viewportStartMs);
}

// ruler tick density (ms per pixel in detail view)
const msPerPx = (state.viewportEndMs - state.viewportStartMs) / canvasWidth;

// overview selection box — fractional positions in [0, 1]
const startFrac = state.viewportStartMs / state.totalDurationMs;
const endFrac   = state.viewportEndMs   / state.totalDurationMs;
```

**Important:** The overview canvas uses a completely separate coordinate space — `overviewPx / overviewWidth × totalDurationMs` — with no relationship to the detail canvas coordinate system. Never mix them.

---

## Components

### `<acv-toolbar>` — unchanged

Session picker dropdown (paginated, 25 per page + load-more), total cost display, refresh (↺) button. Zoom controls removed — zoom is now gesture-native. API and rendering identical to v2.

---

### `<acv-overview>` — NEW

Full-width canvas, fixed 60px height. Always renders the **entire session** (0 → `totalDurationMs`) at full canvas width. Not scrollable, not zoomable. Purpose: navigation only.

**Rendering:**

1. **Compressed span rows** — same `_rowIndexMap` ordering as the detail view, squashed to ~8px per row. Each span drawn as a provider-colored rectangle at proportional x position:
   ```javascript
   x = span.start_ms / state.totalDurationMs * canvasWidth
   w = (span.end_ms - span.start_ms) / state.totalDurationMs * canvasWidth
   ```

2. **Selection box overlay** — a translucent rectangle drawn on top showing the current viewport:
   ```javascript
   boxX = state.viewportStartMs / state.totalDurationMs * canvasWidth
   boxW = (state.viewportEndMs - state.viewportStartMs) / state.totalDurationMs * canvasWidth
   ```

**Pointer interactions:**

| Gesture | Effect |
|---|---|
| Drag **inside** the selection box | Pan: shift `viewportStartMs` and `viewportEndMs` together |
| Drag **left edge** of selection box | Move `viewportStartMs` only |
| Drag **right edge** of selection box | Move `viewportEndMs` only |
| Click **outside** the selection box | Jump viewport center to that ms position |

All interactions call `setViewport()`. The selection box redraws automatically on every `renderAll()` call.

**Bidirectional sync:** Any viewport change (Cmd+scroll in detail, keyboard shortcut, canvas drag) triggers `renderAll()`, which redraws the overview selection box. One source of truth.

---

### `<acv-body>` — REPLACES `<acv-tree>` + `<acv-timeline>`

Owns the CSS Grid layout and all children inside it: ruler, labels column, main canvas, and the detail panel. This is the key architectural change — label rows and canvas rows live in the same scroll container and are aligned by grid geometry.

**Shadow DOM structure:**

```html
<div class="grid">
  <!-- Ruler: spans both columns, sticks to top during vertical scroll -->
  <div class="ruler-wrapper">
    <div class="ruler-left-blank"></div>       <!-- 220px, matches labels column -->
    <canvas id="ruler-canvas"></canvas>        <!-- ticks for [viewportStartMs, viewportEndMs] -->
  </div>

  <!-- Labels: left column, scrolls with grid -->
  <div class="labels-column">
    <div class="label-row">Session A</div>
    <div class="label-row">  └ Child 1</div>
    <!-- one 32px-tall div per visible row, same ordering as _rowIndexMap -->
  </div>

  <!-- Main canvas: right column, height = numRows × ROW_H -->
  <canvas id="main-canvas"></canvas>
</div>

<!-- Detail panel: below grid, slides up on span click -->
<acv-detail></acv-detail>
```

**CSS:**

```css
.grid {
  display: grid;
  grid-template-columns: 220px 1fr;
  grid-template-rows: auto 1fr;   /* ruler row | content row */
  overflow-y: auto;
  flex: 1;                        /* fills remaining app height */
}

.ruler-wrapper {
  grid-column: 1 / -1;           /* spans both columns */
  position: sticky;
  top: 0;
  display: flex;
  z-index: 10;
}

.ruler-left-blank {
  width: 220px;
  flex-shrink: 0;
  background: #161b22;            /* matches labels column bg */
}

#ruler-canvas {
  flex: 1;
}

.labels-column {
  grid-column: 1;
}

.label-row {
  height: 32px;                   /* ROW_H constant */
  display: flex;
  align-items: center;
  padding-left: 8px;
}

#main-canvas {
  grid-column: 2;
  /* height set in JS: numRows × 32 */
}
```

**Responsibilities:**
- Canvas drawing (ruler ticks, span rectangles, hover highlight)
- Keyboard shortcuts (W/A/S/D, ←/→, +/−, Cmd+scroll — all call `setViewport()`)
- Vertical scroll position tracking (`state.scrollTop`)
- Span hit testing on canvas click → sets `state.selectedSpan`, shows `<acv-detail>`

---

### `<acv-detail>` — unchanged

Slides up on span click. Renders: provider/model, formatted duration, token counts (in/out/cache read/cache write), cost, extracted input/output content. API and rendering identical to v2.

---

## Data Flow

```
Session select
    │
    ▼
fetch /api/sessions/{id}
    │
    ▼
Build spans[] + _rowIndexMap()
    │
    ├─► state.totalDurationMs = max(span.end_ms)
    │
    └─► setViewport(0, totalDurationMs, animate=false)
            │
            ▼
        state.viewportStartMs = 0
        state.viewportEndMs   = totalDurationMs
            │
            ▼
        renderAll()
         ├─ overview.render()    → draws compressed rows + selection box
         ├─ ruler.render()       → draws time ticks for [startMs, endMs]
         ├─ labels.render()      → renders label-row divs
         └─ canvas.render()      → draws span rects via timeToPixel()

User gesture (zoom/pan/keyboard/overview drag)
    │
    ▼
setViewport(newStart, newEnd)
    │
    ├─ clamp: span ≥ 100ms, start ≥ 0, end ≤ totalDurationMs
    │
    └─► _animateViewport() or direct state update
            │
            ▼
        renderAll()  (same render path as above)
```

---

## Viewport Operations

### `setViewport`

Single entry point for all zoom and pan in the detail view:

```javascript
function setViewport(startMs, endMs, animate = true) {
  const MIN_SPAN_MS = 100;       // never show less than 100ms
  const span  = Math.max(endMs - startMs, MIN_SPAN_MS);
  const start = Math.max(0, startMs);
  const end   = Math.min(state.totalDurationMs, start + span);

  if (animate) {
    _animateViewport(start, end);
  } else {
    state.viewportStartMs = start;
    state.viewportEndMs   = end;
    renderAll();
  }
}

function _animateViewport(targetStart, targetEnd) {
  const fromStart = state.viewportStartMs;
  const fromEnd   = state.viewportEndMs;
  const t0        = performance.now();
  const DURATION  = 100; // ms

  if (state._animRaf) cancelAnimationFrame(state._animRaf);

  function step(now) {
    const t     = Math.min((now - t0) / DURATION, 1);
    const eased = t * (2 - t);   // ease-out quadratic
    state.viewportStartMs = fromStart + (targetStart - fromStart) * eased;
    state.viewportEndMs   = fromEnd   + (targetEnd   - fromEnd)   * eased;
    renderAll();
    if (t < 1) {
      state._animRaf = requestAnimationFrame(step);
    } else {
      state.viewportStartMs = targetStart;
      state.viewportEndMs   = targetEnd;
      state._animRaf        = null;
      renderAll();
    }
  }
  state._animRaf = requestAnimationFrame(step);
}
```

### Gesture translation table

| Gesture | Computation |
|---|---|
| **Cmd+scroll** (zoom, cursor at detailPx X) | `cursorMs = pixelToTime(X, canvasW)`; narrow/widen range keeping `cursorMs` fixed |
| **Drag canvas** (pan) | shift both ends by `ΔpxDrag × msPerPx` |
| **Drag overview selection box** | shift both ends by `ΔpxDrag / overviewWidth × totalDurationMs` |
| **Drag overview left edge** | move `viewportStartMs` only |
| **Drag overview right edge** | move `viewportEndMs` only |
| **Click outside overview box** | center viewport on `clickPx / overviewWidth × totalDurationMs` |
| **W or = key** | zoom in: `mid ± visibleMs × 0.35` |
| **S or − key** | zoom out: `mid ± visibleMs × 0.65` |
| **A or ← key** | pan left: `start − visibleMs × 0.2`, `end − visibleMs × 0.2` |
| **D or → key** | pan right: `start + visibleMs × 0.2`, `end + visibleMs × 0.2` |
| **Initial session load** | `setViewport(0, totalDurationMs, false)` |

---

## Error Handling

Unchanged from v2:
- Fetch failures show inline error messages via existing `renderError()` path
- Empty session data (no spans) renders empty canvas with "No spans" message
- `setViewport` clamps inputs — callers do not need to validate bounds
- Canvas resize observer re-renders on layout change without re-fetching

---

## Testing Strategy

- **Unit tests** for `timeToPixel`, `pixelToTime`, `setViewport` clamping math — pure functions, no DOM needed
- **Integration tests** for `setViewport` → `renderAll()` call chain using `sinon` stubs (same pattern as existing v2 tests)
- **Regression tests** for row count / `_rowIndexMap` ordering — these are backend-computed, unchanged
- **Visual smoke test:** load a session with ≥3 levels of nesting, confirm label row 5 visually aligns with canvas row 5 at multiple zoom levels
- All existing Python backend tests (`pytest`) pass unchanged — no backend modifications

---

## What Stays the Same (from v2)

| Item | Notes |
|---|---|
| All Python backend | server.py, reader.py, pricing.py — untouched |
| All API endpoints and response shapes | no contract changes |
| `_rowIndexMap()` session ordering logic | same traversal, same output |
| `ROW_H = 32` | row height constant unchanged |
| Provider color system | `PROVIDER_COLORS`, saturation mapping logic |
| `_formatDuration()`, `_extractContent()`, `_fmtTokens()` | unchanged helpers |
| Color-batched canvas drawing | `beginPath → N×rect → fill` per color group |
| Lit 3 via `vendor/lit.all.min.js` | no build step |
| W/A/S/D keyboard shortcuts | now call `setViewport()` instead of mutating `timeScale` |

---

## What Changes

| v2 | v3 |
|---|---|
| `state.timeScale`, `state.scrollLeft`, `state._zoomAnimRaf` | removed; replaced by `viewportStartMs`, `viewportEndMs`, `_animRaf` |
| `<acv-tree>` + `<acv-timeline>` (2 components) | merged into `<acv-body>` with CSS Grid |
| Scroll sync via JS event listeners | structural alignment via CSS Grid — no sync code |
| `ms / timeScale - scrollLeft` coordinate math | `timeToPixel()` / `pixelToTime()` |
| Ruler div with absolute-positioned tick `<span>`s | ruler `<canvas>` element |
| Cost heatmap strip above timeline | `<acv-overview>` canvas with compressed span rows |
| `_animateZoom()` interpolating `timeScale` | `_animateViewport()` interpolating ms range |
| Separate scroll containers requiring sync | single `overflow-y: auto` grid container |

---

## Success Criteria

| Criterion | How it's verified |
|---|---|
| Label row N always aligns with canvas row N | Structural (CSS Grid) — no test needed; verified visually |
| Overview selection box reflects viewport in real time | `renderAll()` always redraws overview; inspect on scroll |
| All zoom/pan paths use `setViewport()` | Code review — grep for any direct mutation of `viewportStartMs`/`viewportEndMs` outside `setViewport` and `_animateViewport` |
| Session list loads < 2s | Unchanged perf path — existing network timing |
| Gantt renders < 500ms after session select | Same canvas draw path, same data; time `renderAll()` in DevTools |
| Smooth animated zoom (100ms ease-out) | Visual inspection; 6 frames at 60fps is sufficient |

---

## Open Questions

None — design fully validated with user.
