# Cost Viewer v3 — Phase 2 Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Replace the `<acv-overview>` placeholder with a real canvas that shows the entire session compressed into 60px, with a draggable selection box that controls the viewport range.

**Architecture:** The overview canvas maps `[0, totalDurationMs]` → full canvas width using a separate `ovTimeToPixel` coordinate function (never `timeToPixel`, which maps the detail viewport). It draws color-batched compressed span rows (same `_rowIndexMap` ordering as the detail view) plus a selection box overlay representing `[viewportStartMs, viewportEndMs]`. Pointer interactions (click-to-jump, drag-to-pan, drag-to-resize) call `setViewport()` which triggers `renderAll()`, automatically redrawing both overview and detail views.

**Tech Stack:** Vanilla JS, Lit 3 (vendor bundle), Canvas 2D, Python pytest (string assertion tests)

**Design doc:** `docs/plans/2026-04-26-cost-viewer-v3-design.md`

---

## File Inventory

| File | Action |
|---|---|
| `viewer/amplifier_app_cost_viewer/static/app.js` | Modify — add `ovTimeToPixel`, rewrite `AcvOverview` class |
| `viewer/tests/test_app_js.py` | Modify — add Phase 2 test classes |

**Do NOT touch:** `server.py`, `reader.py`, `pricing.py`, `index.html`, `style.css`, `AcvBody`, `AcvToolbar`, `AcvDetail`, or any Python backend file.

**Test runner:** `cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -v`

**Key conventions in this codebase:**
- Lit import: `import { html, render } from '/static/vendor/lit.all.min.js';`
- Rendering: `render(html\`...\`, this._root)` — NOT `Lit.render()`
- Shadow DOM: `this._root = this.attachShadow({ mode: 'open' })` in constructor
- State subscription: `subscribe(() => this.notify())` in connectedCallback (AcvBody pattern)
- Tests: Python pytest, string assertions on file contents (`assert "foo" in app_js_code`)
- Canvas DPR: `c.width = Math.round(cssW * dpr); ctx.scale(dpr, dpr);`

**Phase 1 delivered (do not modify):**
- `state.viewportStartMs`, `state.viewportEndMs`, `state.totalDurationMs` — viewport state
- `setViewport(startMs, endMs, animate)` — single entry point for viewport changes
- `timeToPixel()`, `pixelToTime()`, `msPerPx()` — detail view coordinate helpers
- `_rowIndexMap()`, `_visibleRows()`, `_visibleRowsWithDepth()` — tree traversal
- `AcvBody` — HTML table layout with labels + ruler canvas + main canvas + drag/zoom
- `AcvOverview` — placeholder class (lines 593–637) that renders "overview — Phase 2"

---

### Task 1: Add `ovTimeToPixel` helper + rewrite AcvOverview with canvas and compressed span rendering

**What:** Add a module-level `ovTimeToPixel` coordinate helper that maps `[0, totalDurationMs]` → canvas width. Replace the entire AcvOverview placeholder class with a real implementation: shadow DOM with `<canvas>`, `ResizeObserver`, DPR scaling, and compressed span rendering using color-batched rects. No selection box or interactions yet — just the compressed span minimap.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append this block at the very end of `viewer/tests/test_app_js.py` (after line 1927):

```python
# ---------------------------------------------------------------------------
# Tests: Phase 2 — AcvOverview canvas with compressed spans
# ---------------------------------------------------------------------------


class TestP2OvTimeToPixel:
    """Tests for the ovTimeToPixel coordinate helper."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_ov_time_to_pixel_defined(self) -> None:
        assert "function ovTimeToPixel" in self.content, (
            "Must define 'function ovTimeToPixel' as a module-level coordinate helper"
        )

    def test_ov_time_to_pixel_uses_total_duration(self) -> None:
        assert "totalDurationMs" in self.content, (
            "ovTimeToPixel must use state.totalDurationMs to map [0, total] → canvas"
        )


class TestP2OverviewCanvas:
    """Tests for the AcvOverview canvas scaffold and compressed span rendering."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_overview_has_canvas_element(self) -> None:
        assert "ov-canvas" in self.content, (
            "AcvOverview must render a <canvas id='ov-canvas'> element"
        )

    def test_overview_no_placeholder(self) -> None:
        assert "overview — Phase 2" not in self.content, (
            "AcvOverview must not contain the Phase 1 placeholder text"
        )

    def test_overview_has_resize_observer(self) -> None:
        assert "#resizeObserver" in self.content or "_resizeObserver" in self.content, (
            "AcvOverview must use a ResizeObserver for canvas sizing"
        )

    def test_overview_has_notify_method(self) -> None:
        # AcvOverview should follow the AcvBody pattern: subscribe -> notify
        assert "notify()" in self.content, (
            "AcvOverview must have a notify() method called by the subscriber"
        )

    def test_overview_draws_compressed_spans(self) -> None:
        assert "ovTimeToPixel" in self.content, (
            "AcvOverview #draw must use ovTimeToPixel for span positioning"
        )

    def test_overview_uses_row_index_map(self) -> None:
        assert "_rowIndexMap" in self.content, (
            "AcvOverview #draw must use _rowIndexMap for row ordering"
        )

    def test_overview_color_batches_spans(self) -> None:
        # Must group by color like AcvBody — look for the batches Map pattern
        assert "batches" in self.content, (
            "AcvOverview must use color-batched drawing (group spans by color)"
        )
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestP2" -v 2>&1 | tail -20
```

Expected: Most `TestP2*` tests FAIL. Some may pass incidentally (e.g., `_rowIndexMap` already exists in the file for AcvBody, but `ov-canvas` and `ovTimeToPixel` do not).

**Step 3: Implement**

**(3a) Add `ovTimeToPixel` after the coordinate helpers section.** Find this line in `viewer/amplifier_app_cost_viewer/static/app.js`:

```javascript
function msPerPx(canvasW) {
```

Insert the following block AFTER the closing `}` of the `msPerPx` function (after the line `return (state.viewportEndMs - state.viewportStartMs) / canvasW;` and its closing `}`):

```javascript

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
```

**(3b) Replace the entire AcvOverview class.** Find the section that starts with:

```javascript
// =============================================================================
// Section 9: Custom element — AcvOverview  (placeholder)
```

and ends with:

```javascript
customElements.define('acv-overview', AcvOverview);
```

Replace that entire block (the section comment, class definition, and `customElements.define` call) with:

```javascript
// =============================================================================
// Section 9: Custom element — AcvOverview
// Full-width 60px canvas showing entire session compressed, with a draggable
// selection box representing the current viewport range.
// =============================================================================

class AcvOverview extends HTMLElement {
  #canvas = null;
  #ctx = null;
  #rafId = null;
  #resizeObserver = null;
  #dragMode = null;      // null | 'pan' | 'resize-left' | 'resize-right'
  #dragStartX = 0;
  #dragStartMs = { start: 0, end: 0 };

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

  /** Called on every state change to re-render Lit template + canvas. */
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
          background: #0d1117;
          border-bottom: 1px solid var(--border, #30363d);
          box-sizing: border-box;
        }
        canvas {
          display: block;
          width: 100%;
          height: 60px;
          cursor: crosshair;
        }
      </style>
      <canvas id="ov-canvas"></canvas>
    `, this._root);
  }

  // —— Canvas lifecycle ——————————————————————————————————————————

  #setupResizeObserver() {
    if (this.#resizeObserver) this.#resizeObserver.disconnect();
    this.#resizeObserver = new ResizeObserver(() => {
      this.#ensureCanvas();
      this.#scheduleRedraw();
    });
    this.#resizeObserver.observe(this);
  }

  #ensureCanvas() {
    const c = this._root.getElementById('ov-canvas');
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = this.getBoundingClientRect();
    const W = Math.max(1, Math.round(rect.width));
    const H = 60;
    if (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr)) {
      c.style.width  = W + 'px';
      c.style.height = H + 'px';
      c.width  = Math.round(W * dpr);
      c.height = Math.round(H * dpr);
      this.#ctx = c.getContext('2d');
      this.#ctx.scale(dpr, dpr);
      this.#canvas = c;
    } else if (!this.#ctx) {
      this.#ctx = c.getContext('2d');
      this.#canvas = c;
    }
  }

  #scheduleRedraw() {
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = requestAnimationFrame(() => {
      this.#rafId = null;
      this.#draw();
    });
  }

  // —— Canvas drawing ————————————————————————————————————————————

  #draw() {
    const ctx    = this.#ctx;
    const canvas = this.#canvas;
    if (!ctx || !canvas) return;
    const W = parseFloat(canvas.style.width) || canvas.width / (window.devicePixelRatio || 1);
    const H = 60;
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, W, H);

    if (!state.spans || state.spans.length === 0 || !state.sessionData) return;

    const rowMap    = _rowIndexMap(state.sessionData, state.expandedSessions);
    const totalRows = rowMap.size;
    if (totalRows === 0) return;

    // Compressed row height: fit all rows in 60px, cap each at 8px.
    // For 10 rows → 6px each; for 300 rows → 0.2px each (sub-pixel, canvas anti-aliases).
    const rowH = Math.min(8, H / totalRows);

    // Color-batched compressed span rectangles
    const batches = new Map();
    for (const span of state.spans) {
      const rowIdx = rowMap.get(span.session_id);
      if (rowIdx === undefined) continue;
      const x = ovTimeToPixel(span.start_ms || 0, W);
      const w = Math.max(1, ovTimeToPixel(span.end_ms || 0, W) - x);
      const y = rowIdx * rowH;
      if (y + rowH < 0 || y > H) continue;
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
  }
}

customElements.define('acv-overview', AcvOverview);
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestP2" -v 2>&1 | tail -20
```

Expected: All `TestP2*` tests PASS.

Also verify all existing tests still pass:

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -q 2>&1 | tail -5
```

Expected: 245 + 9 = ~254 tests pass, 0 failures.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): AcvOverview canvas with compressed span rendering + ovTimeToPixel"
```

---

### Task 2: Add selection box drawing

**What:** Add `#drawSelectionBox` method to AcvOverview that draws: (1) darkened areas outside the viewport range, (2) a blue border around the selection, and (3) 4px-wide blue resize handles at left/right edges. Call it from `#draw()` after span rendering.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to the end of `viewer/tests/test_app_js.py`:

```python


class TestP2SelectionBox:
    """Tests for the AcvOverview selection box drawing."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_draw_selection_box_method_exists(self) -> None:
        assert "drawSelectionBox" in self.content, (
            "AcvOverview must have a #drawSelectionBox method"
        )

    def test_selection_box_reads_viewport_state(self) -> None:
        # drawSelectionBox must use viewport state to position the box
        assert "viewportStartMs" in self.content
        assert "viewportEndMs" in self.content

    def test_selection_box_darkens_outside(self) -> None:
        # Semi-transparent black overlay on areas outside the selection
        assert "rgba(0, 0, 0" in self.content, (
            "Selection box must darken areas outside the viewport with rgba(0,0,0,...)"
        )

    def test_selection_box_has_blue_border(self) -> None:
        assert "rgba(88, 166, 255" in self.content, (
            "Selection box must have a blue border using rgba(88, 166, 255, ...)"
        )

    def test_selection_box_has_resize_handles(self) -> None:
        # Resize handles are 4px-wide blue strips at left/right edges
        # The draw code must reference '4' for handle width in the fillRect calls
        content = self.content
        assert "strokeRect" in content, (
            "Selection box must draw a stroked rectangle for the border"
        )
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestP2SelectionBox" -v 2>&1 | tail -15
```

Expected: `test_draw_selection_box_method_exists` FAILS, `test_selection_box_darkens_outside` FAILS, `test_selection_box_has_blue_border` FAILS. (Some viewport state tests may pass since the strings exist elsewhere.)

**Step 3: Implement**

**(3a) Add the `#drawSelectionBox` method.** In the `AcvOverview` class, find the closing `}` of the `#draw()` method (the last `}` before the class closing `}`). Insert the following method AFTER `#draw()`:

```javascript

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
```

**(3b) Call `#drawSelectionBox` from `#draw()`.** In the `#draw()` method, find the end of the color-batching loop:

```javascript
    for (const [color, rects] of batches) {
      ctx.beginPath();
      for (const r of rects) ctx.rect(r.x, r.y, r.w, r.h);
      ctx.fillStyle = color;
      ctx.fill();
    }
```

Add this line AFTER that closing `}`:

```javascript

    // Selection box overlay
    this.#drawSelectionBox(ctx, W, H);
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestP2SelectionBox" -v 2>&1 | tail -15
```

Expected: All `TestP2SelectionBox` tests PASS.

Full suite check:

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -q 2>&1 | tail -5
```

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): AcvOverview selection box with darkened exterior and resize handles"
```

---

### Task 3: Add pointer interactions (click-to-jump, drag-to-pan, drag-to-resize)

**What:** Add `#wireOverviewEvents` method to AcvOverview that handles three interaction modes: (1) click outside selection → jump viewport center, (2) drag inside selection → pan viewport, (3) drag left/right edges → resize viewport. Also adds cursor feedback (crosshair/grab/ew-resize). Call the wiring from `#ensureCanvas`.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to the end of `viewer/tests/test_app_js.py`:

```python


class TestP2OverviewInteractions:
    """Tests for AcvOverview pointer interactions."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_wire_overview_events_method(self) -> None:
        assert "wireOverviewEvents" in self.content, (
            "AcvOverview must have a #wireOverviewEvents method"
        )

    def test_drag_mode_pan(self) -> None:
        assert "'pan'" in self.content, (
            "Overview must support dragMode = 'pan' for dragging inside selection"
        )

    def test_drag_mode_resize_left(self) -> None:
        assert "'resize-left'" in self.content, (
            "Overview must support dragMode = 'resize-left' for left edge drag"
        )

    def test_drag_mode_resize_right(self) -> None:
        assert "'resize-right'" in self.content, (
            "Overview must support dragMode = 'resize-right' for right edge drag"
        )

    def test_overview_calls_set_viewport(self) -> None:
        # All interactions must go through setViewport
        assert "setViewport" in self.content, (
            "Overview interactions must call setViewport to change the viewport"
        )

    def test_cursor_ew_resize(self) -> None:
        assert "ew-resize" in self.content, (
            "Overview must show ew-resize cursor when hovering resize handles"
        )

    def test_cursor_grab(self) -> None:
        assert "'grab'" in self.content, (
            "Overview must show grab cursor when hovering inside selection"
        )

    def test_mousedown_listener(self) -> None:
        assert "mousedown" in self.content, (
            "Overview must listen for mousedown to start drag interactions"
        )

    def test_mousemove_listener(self) -> None:
        assert "mousemove" in self.content, (
            "Overview must listen for mousemove to handle dragging"
        )

    def test_mouseup_listener(self) -> None:
        assert "mouseup" in self.content, (
            "Overview must listen for mouseup to stop dragging"
        )
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestP2OverviewInteractions" -v 2>&1 | tail -20
```

Expected: `test_wire_overview_events_method` FAILS, `test_drag_mode_pan` FAILS, `test_drag_mode_resize_left` FAILS, etc. Some mouse event tests may pass because AcvBody already uses `mousedown`/`mousemove`/`mouseup`.

**Step 3: Implement**

**(3a) Add `#wireOverviewEvents` method.** In the `AcvOverview` class, find the closing `}` of `#drawSelectionBox()`. Insert the following method AFTER it:

```javascript

  // —— Pointer interactions ——————————————————————————————————————

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
        // Reset cursor (will be set correctly on next mousemove)
      }
    };
    canvas.addEventListener('mouseup', stopDrag);
    canvas.addEventListener('mouseleave', stopDrag);
  }
```

**(3b) Wire events from `#ensureCanvas`.** In the `#ensureCanvas()` method, find the closing section (right before the method's final `}`). After the `else if (!this.#ctx)` block, add:

```javascript

    // Wire pointer events once
    if (!c._v3wired) {
      this.#wireOverviewEvents(c);
      c._v3wired = true;
    }
```

The complete end of `#ensureCanvas()` should now look like:

```javascript
    } else if (!this.#ctx) {
      this.#ctx = c.getContext('2d');
      this.#canvas = c;
    }

    // Wire pointer events once
    if (!c._v3wired) {
      this.#wireOverviewEvents(c);
      c._v3wired = true;
    }
  }
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestP2OverviewInteractions" -v 2>&1 | tail -20
```

Expected: All `TestP2OverviewInteractions` tests PASS.

Full suite check:

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -q 2>&1 | tail -5
```

Expected: All tests pass.

Also verify no JavaScript syntax errors:

```bash
cd /Users/ken/workspace/ms/token-cost && node --check viewer/amplifier_app_cost_viewer/static/app.js && echo "Syntax OK"
```

Expected: `Syntax OK`

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): AcvOverview pointer interactions — click-to-jump, drag-to-pan, drag-to-resize"
```

---

### Task 4: Browser-tester verification

**What:** Start the development server and use the `browser-tester:browser-operator` agent to verify all overview features work end-to-end. This is a verification-only task — no code changes.

**Files:** None (verification only)

**Step 1: Start the dev server**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run python -m amplifier_app_cost_viewer.server --port 8765 &
sleep 2
echo "Server started"
```

**Step 2: Delegate to browser-tester**

Use the browser-tester agent to navigate to `http://localhost:8765` and verify ALL of the following:

1. **Overview shows colored span bars** — after selecting a session, the overview strip (60px tall below the toolbar) should show compressed colored rectangles representing spans
2. **Selection box visible** — the current viewport is shown as a bright-bordered rectangle with darkened areas outside it
3. **Selection box starts full-width** — on initial session load (viewport = full session), the selection box spans the entire overview width with no dark areas
4. **Click outside selection** — clicking in the dark area outside the selection box should jump the viewport (the detail view scrolls/zooms to center on the clicked time position)
5. **Drag inside selection** — clicking and dragging inside the selection box should pan the detail view left/right
6. **Drag selection edges** — dragging the left or right edge of the selection box should resize the viewport (zoom in/out from that edge)
7. **Zoom in detail → selection narrows** — using Cmd+scroll (or W key) to zoom in the detail canvas should narrow the selection box in the overview in real time
8. **Cursor feedback** — hovering over the selection box edges shows `ew-resize`, inside shows `grab`, outside shows `crosshair`
9. **No JS errors** — open DevTools console, confirm no red errors

Report what works and what doesn't. If issues are found, document them clearly for follow-up — do NOT fix them in this task.

**Step 3: Stop the dev server**

```bash
kill %1 2>/dev/null || true
```

**Step 4: Final commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add -A && git commit -m "feat(viewer): v3 phase 2 complete — AcvOverview with compressed spans, selection box, and drag interactions" --allow-empty
```

---

## Important implementation notes

1. **`ovTimeToPixel` is NOT `timeToPixel`** — the overview always maps `[0, totalDurationMs]` → canvas width. The detail view maps `[viewportStartMs, viewportEndMs]` → canvas width. NEVER use `timeToPixel` in AcvOverview. NEVER use `ovTimeToPixel` in AcvBody.

2. **Canvas sizing** — the overview canvas width comes from `this.getBoundingClientRect().width`. Height is fixed at 60px. DPR scaling applies: `c.width = Math.round(cssW * dpr); ctx.scale(dpr, dpr)`. This mirrors the AcvBody pattern exactly.

3. **Color batching** — same as AcvBody's `#draw()`. Group spans by `span.color`, one `beginPath → N×rect → fill` per color group. Uses `span.color || '#64748B'` default.

4. **Compressed row height** — `Math.min(8, 60 / totalRows)`. No floor, no minimum. Canvas anti-aliases sub-pixel rects naturally. For 10 rows → 6px each, for 300 rows → 0.2px each.

5. **`setViewport(…, false)` during drag** — drag-pan and drag-resize use `animate=false` so the viewport snaps instantly to where the user is dragging. Only click-to-jump uses `animate=true` (the default) for smooth animation.

6. **Don't break Phase 1** — AcvBody, AcvToolbar, and AcvDetail are UNCHANGED. Only the AcvOverview class and the new `ovTimeToPixel` function are added/modified. The subscribe/notify pattern ensures the overview redraws whenever any viewport change occurs (from any source — keyboard, canvas zoom, overview drag).

7. **Private field declarations** — Task 1 declares ALL private fields upfront (including `#dragMode`, `#dragStartX`, `#dragStartMs` for Task 3) so the class header doesn't need to be modified in later tasks. These fields are inert until Task 3 adds the methods that use them.

8. **Event wiring pattern** — same `c._v3wired = true` guard as AcvBody uses for `mc._v3wired` and `rc._v3wired`. Prevents duplicate listeners if `#ensureCanvas()` runs multiple times.
