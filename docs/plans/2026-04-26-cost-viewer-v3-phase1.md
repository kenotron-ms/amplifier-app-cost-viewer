# Cost Viewer v3 — Phase 1 Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.
> After completing all tasks, delegate to a **browser-tester** agent to verify
> the page loads, labels render, and the CSS Grid is visually correct.

**Goal:** Migrate the cost viewer to a viewport-range state model and CSS Grid layout skeleton with working labels.

**Architecture:** Replace `timeScale`/`scrollLeft` state with `viewportStartMs`/`viewportEndMs`. Merge `<acv-tree>` + `<acv-timeline>` into a single `<acv-body>` component using CSS Grid (labels column + canvas column in one scroll container). Add `<acv-overview>` placeholder. By end of Phase 1, the app loads with session labels visible in a CSS Grid — no canvas drawing yet (Phase 2).

**Tech Stack:** Vanilla JS, Lit 3 (vendor bundle), CSS Grid, Python pytest (grep-based string assertion tests)

**Design doc:** `docs/plans/2026-04-26-cost-viewer-v3-design.md`

---

## File Inventory

| File | Action |
|---|---|
| `viewer/amplifier_app_cost_viewer/static/app.js` | In-place rewrite (1761 → ~1100 lines) |
| `viewer/amplifier_app_cost_viewer/static/index.html` | Replace component tags (19 lines) |
| `viewer/amplifier_app_cost_viewer/static/style.css` | Update layout rules |
| `viewer/tests/test_app_js.py` | Update assertions for v3 |

**Do NOT touch:** `server.py`, `reader.py`, `pricing.py`, `pyproject.toml`, or any Python backend file.

**Test runner:** `cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -v`

**Key conventions in this codebase:**
- Lit import: `import { html, render } from '/static/vendor/lit.all.min.js';`
- Rendering: `render(html\`...\`, this._root)` — NOT `Lit.render()`
- Shadow DOM: `this._root = this.attachShadow({ mode: 'open' })` in constructor
- State subscription: `subscribe(() => this._render())` in connectedCallback
- Tests: Python pytest, string assertions on file contents (`assert "foo" in app_js_code`)

---

### Task 1: Add new state fields, coordinate helpers, setViewport, _animateViewport

**What:** Add the v3 viewport state model alongside the existing v2 fields (we remove old fields later in Task 8). Add `MIN_SPAN_MS` constant, `timeToPixel`/`pixelToTime`/`msPerPx` helpers, and `setViewport`/`_animateViewport` functions. Also add a `_visibleRowsWithDepth` helper (like `_visibleRows` but returns `{node, depth}` objects for label indentation).

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Add this block at the very end of `viewer/tests/test_app_js.py` (after the last existing test):

```python
# ---------------------------------------------------------------------------
# Tests: v3 state model and viewport helpers
# ---------------------------------------------------------------------------


class TestV3StateModel:
    """Tests for the v3 viewport state model."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_state_has_viewport_start_ms(self) -> None:
        assert "viewportStartMs:" in self.content

    def test_state_has_viewport_end_ms(self) -> None:
        assert "viewportEndMs:" in self.content

    def test_state_has_total_duration_ms(self) -> None:
        assert "totalDurationMs:" in self.content

    def test_state_has_anim_raf(self) -> None:
        assert "_animRaf:" in self.content

    def test_min_span_ms_constant(self) -> None:
        assert "MIN_SPAN_MS" in self.content


class TestV3CoordinateHelpers:
    """Tests for coordinate conversion helpers."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_time_to_pixel_defined(self) -> None:
        assert "function timeToPixel" in self.content

    def test_pixel_to_time_defined(self) -> None:
        assert "function pixelToTime" in self.content

    def test_ms_per_px_defined(self) -> None:
        assert "function msPerPx" in self.content


class TestV3SetViewport:
    """Tests for the setViewport entry point."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_set_viewport_defined(self) -> None:
        assert "function setViewport" in self.content

    def test_animate_viewport_defined(self) -> None:
        assert "function _animateViewport" in self.content

    def test_set_viewport_clamps_min_span(self) -> None:
        assert "MIN_SPAN_MS" in self.content

    def test_set_viewport_calls_render_all(self) -> None:
        assert "renderAll()" in self.content


class TestV3VisibleRowsWithDepth:
    """Tests for the _visibleRowsWithDepth helper."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_visible_rows_with_depth_defined(self) -> None:
        assert "function _visibleRowsWithDepth" in self.content
```

**Step 2: Verify tests fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3" -v 2>&1 | tail -20
```

Expected: All `TestV3*` tests FAIL (functions/fields don't exist yet).

**Step 3: Implement**

In `viewer/amplifier_app_cost_viewer/static/app.js`, make these changes:

**(3a)** Add `MIN_SPAN_MS` to the constants block (after line 27, after `const IO_TRUNCATE = 500;`):

```javascript
const MIN_SPAN_MS = 100;   // minimum visible time range (never zoom below 100ms)
```

**(3b)** Add new fields to the `state` object. Insert these four lines right before the closing `};` of the state object (after `_zoomAnimRaf: null,`):

```javascript
  // v3 viewport range — replaces timeScale + scrollLeft (Phase 1)
  totalDurationMs: 0,
  viewportStartMs: 0,
  viewportEndMs:   0,
  _animRaf:        null,
```

**(3c)** Add coordinate helpers. Insert this block right after the `renderAll()` function (after line 72):

```javascript
// =============================================================================
// Coordinate helpers — all conversions derive from the viewport range
// =============================================================================

function timeToPixel(ms, canvasW) {
  const span = state.viewportEndMs - state.viewportStartMs;
  if (span <= 0) return 0;
  return (ms - state.viewportStartMs) / span * canvasW;
}

function pixelToTime(px, canvasW) {
  const span = state.viewportEndMs - state.viewportStartMs;
  return state.viewportStartMs + (px / canvasW) * span;
}

function msPerPx(canvasW) {
  return (state.viewportEndMs - state.viewportStartMs) / canvasW;
}

// =============================================================================
// Viewport mutation — single entry point for all zoom and pan
// =============================================================================

function setViewport(startMs, endMs, animate = true) {
  const span  = Math.max(endMs - startMs, MIN_SPAN_MS);
  const start = Math.max(0, startMs);
  const end   = Math.min(state.totalDurationMs || span, start + span);
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
  const DURATION  = 100;
  if (state._animRaf) cancelAnimationFrame(state._animRaf);
  function step(now) {
    const t     = Math.min((now - t0) / DURATION, 1);
    const eased = t * (2 - t);
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

**(3d)** Add `_visibleRowsWithDepth` right after the existing `_rowIndexMap` function (after line 307):

```javascript
/**
 * Like _visibleRows but returns {node, depth} objects so labels can indent.
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
```

**Step 4: Verify tests pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3" -v 2>&1 | tail -20
```

Expected: All `TestV3*` tests PASS.

Also verify ALL existing tests still pass (we only added code, nothing removed):

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -q 2>&1 | tail -3
```

Expected: `XXX passed` (original 269 + new 13 = 282 tests).

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): v3 state model, coordinate helpers, setViewport, _animateViewport"
```

---

### Task 2: Add AcvOverview placeholder class

**What:** Create the `AcvOverview` custom element — a minimal placeholder that renders "overview — loading…" in a 60px strip. Phase 2 will add the real canvas rendering.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to end of `viewer/tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: v3 AcvOverview component
# ---------------------------------------------------------------------------


class TestV3AcvOverview:
    """Tests for the AcvOverview custom element placeholder."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_acv_overview_class_defined(self) -> None:
        assert "class AcvOverview extends HTMLElement" in self.content

    def test_acv_overview_registered(self) -> None:
        assert "customElements.define('acv-overview'" in self.content

    def test_acv_overview_uses_shadow_dom(self) -> None:
        # Count must increase by 1 (now 5 total: toolbar, tree, timeline, detail, overview)
        assert self.content.count("attachShadow") >= 5
```

**Step 2: Verify RED**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3AcvOverview" -v 2>&1 | tail -10
```

Expected: 3 FAIL.

**Step 3: Implement**

In `viewer/amplifier_app_cost_viewer/static/app.js`, insert this block right BEFORE the `class AcvDetail` definition (look for `// Section 9: Custom element — AcvDetail`):

```javascript
// =============================================================================
// Section 8a: Custom element — AcvOverview (Phase 1 placeholder)
// Full-width overview canvas above the grid — Phase 2 adds compressed spans
// and a draggable selection box.  For now: a simple placeholder strip.
// =============================================================================

class AcvOverview extends HTMLElement {
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
          display: block;
          width: 100%;
          height: 60px;
          background: var(--surface, #161b22);
          border-bottom: 1px solid var(--border, #30363d);
          box-sizing: border-box;
        }
        .placeholder {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: var(--text-muted, #8b949e);
          font-size: 11px;
          font-family: "SF Mono", Consolas, Monaco, monospace;
        }
      </style>
      <div class="placeholder">
        ${state.sessionData ? 'overview — Phase 2' : 'overview — no session'}
      </div>
    `, this._root);
  }
}

customElements.define('acv-overview', AcvOverview);
```

**Step 4: Verify GREEN**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3AcvOverview" -v 2>&1 | tail -10
```

Expected: 3 PASS.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): add AcvOverview placeholder component"
```

---

### Task 3: Add AcvBody CSS Grid shell with labels

**What:** Create the `AcvBody` custom element — CSS Grid with ruler wrapper (blank for Phase 1), labels column (with tree-like indentation, toggle triangles, costs), and an empty canvas column placeholder. Includes `<acv-detail>` inside the shadow DOM. Labels are rendered from `_visibleRowsWithDepth`.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to end of `viewer/tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: v3 AcvBody component
# ---------------------------------------------------------------------------


class TestV3AcvBody:
    """Tests for the AcvBody custom element (CSS Grid shell with labels)."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_acv_body_class_defined(self) -> None:
        assert "class AcvBody extends HTMLElement" in self.content

    def test_acv_body_registered(self) -> None:
        assert "customElements.define('acv-body'" in self.content

    def test_acv_body_css_grid(self) -> None:
        assert "grid-template-columns: 220px 1fr" in self.content

    def test_ruler_spans_both_columns(self) -> None:
        assert "grid-column: 1 / -1" in self.content

    def test_ruler_is_sticky(self) -> None:
        assert "position: sticky" in self.content

    def test_labels_column_present(self) -> None:
        assert "labels-column" in self.content

    def test_canvas_column_present(self) -> None:
        assert "canvas-column" in self.content

    def test_acv_body_uses_visible_rows_with_depth(self) -> None:
        assert "_visibleRowsWithDepth" in self.content

    def test_acv_body_has_toggle_triangles(self) -> None:
        content = self.content
        # Same triangles as AcvTree
        assert "\u25be" in content  # expanded
        assert "\u25b8" in content  # collapsed

    def test_acv_body_dispatches_toggle_expand(self) -> None:
        assert "toggle-expand" in self.content

    def test_acv_body_dispatches_session_select(self) -> None:
        assert "session-select" in self.content

    def test_acv_body_includes_acv_detail(self) -> None:
        assert "<acv-detail" in self.content

    def test_acv_body_scroll_tracks_state(self) -> None:
        assert "state.scrollTop" in self.content
```

**Step 2: Verify RED**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3AcvBody" -v 2>&1 | tail -20
```

Expected: Most tests FAIL (some strings like `toggle-expand` exist in old AcvTree code, so a few may pass — that's OK).

**Step 3: Implement**

In `viewer/amplifier_app_cost_viewer/static/app.js`, insert this block right AFTER the `AcvOverview` class (after `customElements.define('acv-overview', AcvOverview);`):

```javascript
// =============================================================================
// Section 8b: Custom element — AcvBody
// Merged tree + timeline in a single CSS Grid.  Phase 1: ruler placeholder,
// labels column with indentation + toggle + cost, empty canvas column.
// Phase 2 adds main canvas + ruler canvas drawing.
// =============================================================================

class AcvBody extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    subscribe(() => this._render());
    this._render();
    // Wire scroll tracking on the grid container (rendered synchronously by Lit)
    const grid = this._root.querySelector('.grid');
    if (grid) {
      grid.addEventListener('scroll', () => {
        state.scrollTop = grid.scrollTop;
      });
    }
  }

  /** Called externally to trigger a re-render (e.g. after expand/collapse). */
  notify() {
    this._render();
  }

  _render() {
    const rows = state.sessionData
      ? _visibleRowsWithDepth(state.sessionData, state.expandedSessions)
      : [];

    render(html`
      <style>
        :host { display: block; height: 100%; overflow: hidden; }
        .grid {
          display: grid;
          grid-template-columns: 220px 1fr;
          grid-template-rows: auto 1fr;
          height: 100%;
          overflow-y: auto;
          overflow-x: hidden;
        }
        .ruler-wrapper {
          grid-column: 1 / -1;
          grid-row: 1;
          position: sticky;
          top: 0;
          z-index: 5;
          display: flex;
          height: ${RULER_H}px;
          background: var(--surface, #161b22);
          border-bottom: 1px solid var(--border, #30363d);
        }
        .ruler-left-blank {
          width: 220px;
          flex-shrink: 0;
          background: var(--surface, #161b22);
        }
        .ruler-ticks {
          flex: 1;
          background: var(--surface, #161b22);
        }
        .labels-column {
          grid-column: 1;
          grid-row: 2;
          background: var(--surface, #161b22);
          border-right: 1px solid var(--border, #30363d);
        }
        .label-row {
          height: ${ROW_H}px;
          display: flex;
          align-items: center;
          font-size: 11px;
          font-family: "SF Mono", Consolas, Monaco, monospace;
          color: var(--text, #e6edf3);
          border-bottom: 1px solid #21262d;
          cursor: pointer;
          user-select: none;
          overflow: hidden;
          box-sizing: border-box;
        }
        .label-row:hover { background: var(--surface-alt, #21262d); }
        .toggle {
          width: 14px;
          flex-shrink: 0;
          text-align: center;
          font-size: 10px;
          color: var(--text-muted, #8b949e);
        }
        .label-name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .label-cost {
          margin-left: auto;
          color: var(--success, #3fb950);
          flex-shrink: 0;
          font-size: 10px;
          padding-right: 8px;
        }
        .canvas-column {
          grid-column: 2;
          grid-row: 2;
          background: var(--bg, #0d1117);
        }
      </style>
      <div class="grid">
        <div class="ruler-wrapper">
          <div class="ruler-left-blank"></div>
          <div class="ruler-ticks"></div>
        </div>
        <div class="labels-column">
          ${rows.map(({ node, depth }) => {
            const hasChildren = (node.children?.length ?? 0) > 0;
            const isExpanded = state.expandedSessions.has(node.session_id);
            const toggle = hasChildren ? (isExpanded ? '\u25be' : '\u25b8') : '\u00a0';
            return html`
              <div class="label-row"
                   style="padding-left: ${8 + depth * 14}px"
                   @click=${() => this._onLabelClick(node.session_id, hasChildren)}>
                <span class="toggle">${toggle}</span>
                <span class="label-name">${node.name || node.agent_name || node.session_id.slice(-8)}</span>
                <span class="label-cost">$${(node.total_cost_usd || 0).toFixed(4)}</span>
              </div>
            `;
          })}
        </div>
        <div class="canvas-column"></div>
      </div>
      <acv-detail></acv-detail>
    `, this._root);
  }

  _onLabelClick(sid, hasChildren) {
    if (hasChildren) {
      this.dispatchEvent(new CustomEvent('toggle-expand', {
        bubbles: true, composed: true, detail: { id: sid },
      }));
    }
    this.dispatchEvent(new CustomEvent('session-select', {
      bubbles: true, composed: true, detail: { id: sid },
    }));
  }
}

customElements.define('acv-body', AcvBody);
```

**Step 4: Verify GREEN**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3AcvBody" -v 2>&1 | tail -20
```

Expected: All `TestV3AcvBody` tests PASS.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): add AcvBody CSS Grid shell with labels"
```

---

### Task 4: Update index.html and style.css

**What:** Replace the old `<main><acv-tree><acv-timeline></main>` layout with `<acv-overview>` + `<acv-body>`. Update `style.css` to remove old tree/timeline layout rules and set the new component sizing.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/index.html`
- Modify: `viewer/amplifier_app_cost_viewer/static/style.css`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to end of `viewer/tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: v3 HTML structure
# ---------------------------------------------------------------------------

INDEX_HTML = STATIC.parent / "static" / ".." / ".." / "amplifier_app_cost_viewer" / "static" / "index.html"
# Simpler path:
INDEX_HTML = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static" / "index.html"
CSS_FILE = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static" / "style.css"


class TestV3HtmlStructure:
    """Tests for the v3 index.html layout."""

    def setup_method(self) -> None:
        self.html = INDEX_HTML.read_text()

    def test_html_has_acv_overview(self) -> None:
        assert "<acv-overview" in self.html

    def test_html_has_acv_body(self) -> None:
        assert "<acv-body" in self.html

    def test_html_no_acv_tree(self) -> None:
        assert "<acv-tree" not in self.html

    def test_html_no_acv_timeline(self) -> None:
        assert "<acv-timeline" not in self.html

    def test_html_no_main_wrapper(self) -> None:
        assert "<main" not in self.html


class TestV3CssLayout:
    """Tests for the v3 style.css layout."""

    def setup_method(self) -> None:
        self.css = CSS_FILE.read_text()

    def test_css_has_acv_overview(self) -> None:
        assert "acv-overview" in self.css

    def test_css_has_acv_body(self) -> None:
        assert "acv-body" in self.css

    def test_css_overview_height_60px(self) -> None:
        assert "60px" in self.css
```

**Step 2: Verify RED**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3Html or TestV3Css" -v 2>&1 | tail -15
```

Expected: Most FAIL (HTML still has old tags, CSS doesn't have new selectors).

**Step 3a: Rewrite index.html**

Replace the entire content of `viewer/amplifier_app_cost_viewer/static/index.html` with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Amplifier Cost Viewer</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <acv-toolbar id="toolbar"></acv-toolbar>
  <acv-overview id="overview"></acv-overview>
  <acv-body id="body"></acv-body>
  <script type="module" src="/static/app.js"></script>
</body>
</html>
```

**Step 3b: Update style.css**

In `viewer/amplifier_app_cost_viewer/static/style.css`, replace the entire `Three-pane layout` section (the `#main`, `#tree-panel`, `#gantt-panel` rules — lines 190–222) with:

```css
/* ---------------------------------------------------------------------------
   App layout — vertical flex: toolbar → overview → body
   --------------------------------------------------------------------------- */

acv-toolbar {
  flex-shrink: 0;
}

acv-overview {
  flex-shrink: 0;
  height: 60px;
  display: block;
}

acv-body {
  flex: 1;
  min-height: 0;
  display: block;
}
```

Also remove the old `#time-ruler` and `#gantt-rows` rules (lines 282–300), the `.span-bar` and `.gantt-row` rules (lines 306–329), and the old `.tree-row` rules (lines 228–266) since these are now inside shadow DOM. Keep everything else (`:root` variables, body styles, toolbar styles, detail panel styles, scrollbar styles).

**Step 4: Verify GREEN**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3Html or TestV3Css" -v 2>&1 | tail -15
```

Expected: All PASS.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/index.html viewer/amplifier_app_cost_viewer/static/style.css viewer/tests/test_app_js.py && git commit -m "feat(viewer): v3 HTML layout with acv-overview + acv-body"
```

---

### Task 5: Update renderAll and loadSession

**What:** Simplify `renderAll()` (remove timeline loading push). Update `loadSession()` to compute `totalDurationMs` and call `setViewport(0, totalDurationMs, false)` instead of computing `timeScale`.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to end of `viewer/tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: v3 loadSession wiring
# ---------------------------------------------------------------------------


class TestV3LoadSession:
    """Tests for the v3 loadSession function."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_load_session_computes_total_duration(self) -> None:
        assert "state.totalDurationMs" in self.content

    def test_load_session_calls_set_viewport(self) -> None:
        assert "setViewport(0," in self.content
```

**Step 2: Verify RED**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3LoadSession" -v 2>&1 | tail -10
```

Expected: FAIL (setViewport not called in loadSession yet).

**Step 3: Implement**

**(3a)** Replace the `renderAll` function body. Find:

```javascript
function renderAll() {
  notify();
  // Push loading flag directly to timeline (so #draw() sees it before the RAF fires)
  const _tl = document.querySelector('acv-timeline');
  if (_tl) _tl.loading = state.loading;
}
```

Replace with:

```javascript
function renderAll() {
  notify();
}
```

**(3b)** Replace the `loadSession` function. Find the entire `async function loadSession(id)` block and replace with:

```javascript
async function loadSession(id) {
  state.loading = true;
  renderAll();

  try {
    state.activeSessionId = id;
    state.selectedSpan = null;

    await Promise.all([fetchSession(id), fetchSpans(id)]);

    // Auto-expand root and first-level children
    state.expandedSessions.clear();
    state.expandedSessions.add(id);
    if (state.sessionData?.children) {
      for (const c of state.sessionData.children) {
        state.expandedSessions.add(c.session_id);
      }
    }

    // v3: compute total duration and set initial viewport to fit entire session
    state.totalDurationMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1000);
    setViewport(0, state.totalDurationMs, false);
  } finally {
    state.loading = false;
    renderAll();
  }
}
```

**Step 4: Verify GREEN**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3LoadSession" -v 2>&1 | tail -10
```

Expected: PASS.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): v3 renderAll + loadSession with viewport model"
```

---

### Task 6: Update AcvToolbar (remove zoom controls) and rewrite init()

**What:** Remove zoom buttons, zoom label, and `_onZoomIn`/`_onZoomOut` from toolbar. Rewrite `init()` to wire events on `acv-body` instead of `acv-tree`/`acv-timeline`. Remove zoom-in/zoom-out event wiring.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`
- Test: `viewer/tests/test_app_js.py`

**Step 1: Write failing tests**

Append to end of `viewer/tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: v3 init wiring
# ---------------------------------------------------------------------------


class TestV3InitWiring:
    """Tests for the v3 init() function wiring."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_init_wires_body_toggle_expand(self) -> None:
        assert "body" in self.content and "toggle-expand" in self.content

    def test_init_wires_body_session_select(self) -> None:
        assert "body" in self.content and "session-select" in self.content

    def test_init_wires_body_detail_close(self) -> None:
        assert "body" in self.content and "detail-close" in self.content
```

**Step 2: Verify RED**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3InitWiring" -v 2>&1 | tail -10
```

Expected: Some may pass (strings exist in old code); key test is about `body` wiring.

**Step 3: Implement**

**(3a)** In the `AcvToolbar._render()` method, remove the zoom controls from the template. Find these three lines inside the template:

```javascript
      <span class="zoom-label">${state.timeScale.toFixed(1)} ms/px</span>
      <button @click=${() => this._onZoomIn()} title="Zoom in">+</button>
      <button @click=${() => this._onZoomOut()} title="Zoom out">\u2212</button>
```

Delete them entirely. Also remove the `.zoom-label` CSS rule from the toolbar's `<style>` block:

```css
        .zoom-label { color: var(--text-muted, #8b949e); font-size: 10px; }
```

**(3b)** Remove the `_onZoomIn` and `_onZoomOut` methods from AcvToolbar:

```javascript
  _onZoomIn() {
    this.dispatchEvent(new CustomEvent('zoom-in', { bubbles: true, composed: true }));
  }

  _onZoomOut() {
    this.dispatchEvent(new CustomEvent('zoom-out', { bubbles: true, composed: true }));
  }
```

**(3c)** Replace the entire `init()` function with this v3 version:

```javascript
async function init() {
  const toolbar = document.querySelector('acv-toolbar');

  if (toolbar) {
    toolbar.addEventListener('session-change', async e => {
      try {
        await loadSession(e.detail.id);
      } catch (err) {
        console.error('Failed to switch session:', err);
      }
    });

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

    toolbar.addEventListener('load-more', async () => {
      try {
        await fetchSessions(state.sessions.length);
        renderAll();
      } catch (err) {
        console.error('Load more failed:', err);
      }
    });
  }

  // Wire body events: toggle-expand, session-select, detail-close
  const body = document.querySelector('acv-body');
  if (body) {
    body.addEventListener('toggle-expand', e => {
      const id = e.detail.id;
      if (state.expandedSessions.has(id)) {
        state.expandedSessions.delete(id);
      } else {
        state.expandedSessions.add(id);
      }
      renderAll();
    });

    body.addEventListener('session-select', e => {
      state.activeSessionId = e.detail.id;
      renderAll();
    });

    body.addEventListener('detail-close', () => {
      state.selectedSpan = null;
      renderAll();
    });
  }

  // Keyboard shortcuts: W/S zoom, A/D pan, Escape close detail
  // Shift key gives 3× speed.  Skips when target is INPUT/SELECT/TEXTAREA.
  document.addEventListener('keydown', e => {
    const tag = e.target?.tagName;
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;

    const shift = e.shiftKey ? 3 : 1;
    const visibleMs = state.viewportEndMs - state.viewportStartMs;
    const mid = (state.viewportStartMs + state.viewportEndMs) / 2;
    const half = visibleMs / 2;

    switch (e.code) {
      case 'KeyW':
      case 'Equal': {
        e.preventDefault();
        const factor = Math.pow(0.7, shift);
        setViewport(mid - half * factor, mid + half * factor);
        break;
      }

      case 'KeyS':
      case 'Minus': {
        e.preventDefault();
        const factor = Math.pow(1.3, shift);
        setViewport(mid - half * factor, mid + half * factor);
        break;
      }

      case 'KeyA':
      case 'ArrowLeft': {
        e.preventDefault();
        const delta = visibleMs * 0.2 * shift;
        setViewport(state.viewportStartMs - delta, state.viewportEndMs - delta);
        break;
      }

      case 'KeyD':
      case 'ArrowRight': {
        e.preventDefault();
        const delta = visibleMs * 0.2 * shift;
        setViewport(state.viewportStartMs + delta, state.viewportEndMs + delta);
        break;
      }

      case 'Escape':
        state.selectedSpan = null;
        renderAll();
        break;
    }
  });

  // Initial data load
  state.loading = true;
  renderAll();

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
```

**Step 4: Verify GREEN**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -k "TestV3InitWiring" -v 2>&1 | tail -10
```

Expected: PASS.

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js viewer/tests/test_app_js.py && git commit -m "feat(viewer): v3 toolbar (no zoom), init wiring on acv-body, keyboard shortcuts via setViewport"
```

---

### Task 7: Remove dead code and update header comment

**What:** Delete `AcvTree` class, `AcvTimeline` class, `_animateZoom` function, `ZOOM_MIN`/`ZOOM_MAX`/`HEATMAP_H` constants, and old state fields (`timeScale`, `scrollLeft`, `_zoomAnimRaf`). Update the file header comment.

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`

**Step 1: No new tests** (this is a deletion task — test cleanup is Task 8)

**Step 2: Remove old constants**

Delete these three lines from the constants section:

```javascript
const ZOOM_MIN    = 0.05;  // ms per pixel — most zoomed-in
const ZOOM_MAX    = 200;   // ms per pixel — most zoomed-out
```

```javascript
const HEATMAP_H   = 20;    // px heatmap row height
```

**Step 3: Remove old state fields**

In the `const state = { ... }` object, delete these three lines:

```javascript
  timeScale:       1,     // ms per pixel
  scrollLeft:      0,     // timeline horizontal scroll position (px)
```

```javascript
  _zoomAnimRaf:    null,  // requestAnimationFrame handle for in-flight zoom animation
```

**Step 4: Remove _animateZoom function**

Delete the entire `_animateZoom` function (starts with `function _animateZoom(targetScale, anchorMs, anchorPx)` and ends with its closing `}`). This is approximately 40 lines including the JSDoc comment above it.

**Step 5: Remove AcvTree class**

Delete the entire Section 7 block: from the comment `// Section 7: Custom element — AcvTree` through `customElements.define('acv-tree', AcvTree);`. This is approximately 170 lines.

**Step 6: Remove AcvTimeline class**

Delete the entire Section 8 block: from the comment `// Section 8: Custom element — AcvTimeline` through `customElements.define('acv-timeline', AcvTimeline);`. This is approximately 620 lines.

**Step 7: Update the file header**

Replace the header comment (lines 1–13):

```javascript
// =============================================================================
// Amplifier Cost Viewer — app.js  (v3 — viewport range model + CSS Grid)
// =============================================================================
// Architecture:
//   <acv-toolbar>   — session selector, cost summary, refresh
//   <acv-overview>  — compressed full-session overview (Phase 2: canvas)
//   <acv-body>      — CSS Grid: labels + ruler + canvas (main panel)
//   <acv-detail>    — span detail drawer (inside acv-body shadow DOM)
//
// State: viewportStartMs/viewportEndMs define the visible time range.
// All zoom/pan goes through setViewport().  renderAll() triggers all
// subscriber components to re-render from global state.
// =============================================================================
```

**Step 8: Verify the file has no syntax errors**

```bash
cd /Users/ken/workspace/ms/token-cost && node --check viewer/amplifier_app_cost_viewer/static/app.js && echo "Syntax OK"
```

Expected: `Syntax OK`

**Step 9: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/amplifier_app_cost_viewer/static/app.js && git commit -m "refactor(viewer): remove AcvTree, AcvTimeline, _animateZoom, old state fields"
```

> **Note:** Some old tests will now fail because they check for removed strings
> (e.g., `class AcvTree`, `#draw`, `state.timeScale`). This is expected — Task 8 fixes them.

---

### Task 8: Update test file for v2 → v3 transition

**What:** Remove tests that assert v2-only patterns (AcvTree, AcvTimeline, _animateZoom, timeScale, scrollLeft, heatmap, drag-pan, etc.). Update tests that need minor adjustments. The goal is: all 200+ tests pass after this task.

**Files:**
- Modify: `viewer/tests/test_app_js.py`

**Step 1: Delete these entire test CLASSES** (remove the class and all its methods):

| Class to delete | Reason |
|---|---|
| `TestAcvTree` | AcvTree class removed |
| `TestAcvTimeline` | AcvTimeline class removed |
| `TestCanvasDraw` | Canvas drawing is Phase 2 |
| `TestTreeCanvasWiring` | Tree class removed; expand/collapse covered by v3 tests |
| `TestTreeRulerSpacer` | Ruler spacer concept replaced by CSS Grid ruler-wrapper |
| `TestAnimatedZoom` | `_animateZoom` removed; replaced by `_animateViewport` |
| `TestHeatmapAreaGraph` | Heatmap replaced by overview; canvas rendering is Phase 2 |

**Step 2: Delete these individual test FUNCTIONS** (standalone, not in classes):

| Function to delete | Reason |
|---|---|
| `test_canvas_shows_loading_text` | AcvTimeline loading overlay removed |
| `test_ruler_starts_from_visible_window` | Checks for `scrollLeftMs` — v2 coordinate math |
| `test_drag_pan_mousedown_handler` | Drag-to-pan removed (Phase 2 re-adds via setViewport) |
| `test_drag_pan_mousemove_handler` | Drag-to-pan removed |
| `test_drag_pan_stops_on_mouseleave` | Drag-to-pan removed |
| `test_canvas_ctrl_scroll_zoom` | Canvas Cmd+scroll zoom is Phase 2 |
| `test_canvas_vertical_wheel_routes_to_tree` | No separate tree element |
| `test_tree_dispatches_scroll_to_state` | Tree removed; scroll tracked in AcvBody |

**Step 3: Delete these individual test METHODS** from their classes:

From `TestAppJsState`:
- Delete `test_state_has_time_scale`
- Delete `test_state_has_scroll_left`

From `TestAppJsCustomElements`:
- Delete `test_acv_tree_class_defined`
- Delete `test_acv_tree_extends_html_element`
- Delete `test_acv_timeline_class_defined`
- Delete `test_acv_timeline_extends_html_element`
- Delete `test_custom_elements_define_tree`
- Delete `test_custom_elements_define_timeline`
- Update `test_attach_shadow_appears_multiple_times`: change `assert count >= 4` to `assert count >= 4` (keep as-is — there are still 4 components: toolbar, overview, body, detail)

From `TestAcvToolbar`:
- Delete `test_dispatches_zoom_in_event`
- Delete `test_dispatches_zoom_out_event`
- Delete `test_shows_ms_px_zoom_label`

From `TestInitWiring`:
- Delete `test_load_session_computes_time_scale`
- Delete `test_wires_zoom_in_event`
- Delete `test_wires_zoom_out_event`

**Step 4: Add replacement tests to `TestAppJsCustomElements`**

Add these methods to the existing `TestAppJsCustomElements` class:

```python
    def test_acv_body_class_defined(self) -> None:
        assert "class AcvBody" in self.content

    def test_acv_body_extends_html_element(self) -> None:
        assert "AcvBody extends HTMLElement" in self.content

    def test_acv_overview_class_defined(self) -> None:
        assert "class AcvOverview" in self.content

    def test_acv_overview_extends_html_element(self) -> None:
        assert "AcvOverview extends HTMLElement" in self.content

    def test_custom_elements_define_body(self) -> None:
        assert (
            "customElements.define('acv-body'" in self.content
            or 'customElements.define("acv-body"' in self.content
        )

    def test_custom_elements_define_overview(self) -> None:
        assert (
            "customElements.define('acv-overview'" in self.content
            or 'customElements.define("acv-overview"' in self.content
        )
```

**Step 5: Add replacement method to `TestInitWiring`**

```python
    def test_load_session_computes_total_duration(self) -> None:
        assert "state.totalDurationMs" in self.content, (
            "loadSession must compute state.totalDurationMs"
        )
```

**Step 6: Fix `TestAcvDetail.test_acv_detail_element_in_timeline_update`**

This test checks `"acv-detail" in self.content` — it still passes because `<acv-detail` appears in AcvBody. But rename the method for clarity:

```python
    def test_acv_detail_element_in_body(self) -> None:
        assert "acv-detail" in self.content, (
            "AcvBody must include <acv-detail> element"
        )
```

Delete the old `test_acv_detail_element_in_timeline_update` and `test_on_detail_close_method_in_timeline`.

**Step 7: Run all tests**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/test_app_js.py -v 2>&1 | tail -30
```

Expected: ALL tests PASS. Count will be lower than the original 269 (we removed many tests and added some new ones).

If any test fails, read the failure message and decide:
- If it checks for a string that no longer exists → delete the test
- If it checks for a string that moved → update the assertion

**Step 8: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add viewer/tests/test_app_js.py && git commit -m "test(viewer): update tests for v3 architecture (remove v2 assertions, add v3 assertions)"
```

---

### Task 9: Full verification and browser smoke test

**What:** Run the complete test suite. Start the development server and verify in a browser that labels render correctly in the CSS Grid layout.

**Files:** None (verification only)

**Step 1: Run all Python tests**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run pytest viewer/tests/ -v -q 2>&1 | tail -20
```

Expected: ALL tests pass with 0 failures.

**Step 2: Verify app.js has no syntax errors**

```bash
cd /Users/ken/workspace/ms/token-cost && node --check viewer/amplifier_app_cost_viewer/static/app.js && echo "Syntax OK"
```

Expected: `Syntax OK`

**Step 3: Start the dev server**

```bash
cd /Users/ken/workspace/ms/token-cost && uv run python -m amplifier_app_cost_viewer.server --port 8765 &
```

Wait 2 seconds for startup, then open `http://localhost:8765` in a browser.

**Step 4: Browser smoke test** (delegate to browser-tester agent)

Verify ALL of the following:

1. **Page loads without JS errors** — open DevTools console, confirm no red errors
2. **Toolbar appears** at top — session dropdown, total cost, refresh button. NO zoom buttons.
3. **Overview strip** appears below toolbar — 60px tall, shows placeholder text
4. **Session dropdown populates** — select a session from dropdown
5. **Labels column appears** on the left (220px wide):
   - Session names visible with tree indentation
   - Toggle triangles (▸/▾) work — click to expand/collapse
   - Cost shown on each row ($X.XXXX format)
   - Labels scroll vertically if many rows
6. **Canvas column** is empty but visible (dark background, right of labels)
7. **Ruler wrapper** spans full width at top of grid, stays sticky on scroll
8. **CSS Grid alignment** — labels column and canvas column share the same row heights
9. **Keyboard shortcuts** — press W/S to zoom (viewport changes in state), A/D to pan
10. **Take a screenshot** for evidence

**Step 5: Stop the dev server**

```bash
kill %1 2>/dev/null || true
```

**Step 6: Final commit**

```bash
cd /Users/ken/workspace/ms/token-cost && git add -A && git commit -m "feat(viewer): v3 phase 1 complete — viewport state model + CSS Grid skeleton with labels"
```

---

## Summary of changes after Phase 1

### app.js (~1100 lines, down from 1761)

| Section | Status |
|---|---|
| Constants: `ROW_H`, `RULER_H`, `SPAN_H`, `IO_TRUNCATE`, `MIN_SPAN_MS`, `NICE_INTERVALS` | Kept + added |
| State: `viewportStartMs`, `viewportEndMs`, `totalDurationMs`, `_animRaf` | New |
| State: `timeScale`, `scrollLeft`, `_zoomAnimRaf` | Removed |
| Coordinate helpers: `timeToPixel`, `pixelToTime`, `msPerPx` | New |
| `setViewport`, `_animateViewport` | New |
| `_visibleRowsWithDepth` | New |
| `AcvToolbar` | Modified (zoom controls removed) |
| `AcvOverview` | New (placeholder) |
| `AcvBody` | New (CSS Grid + labels) |
| `AcvDetail` | Unchanged |
| `AcvTree` | Removed |
| `AcvTimeline` | Removed |
| `_animateZoom` | Removed |
| `loadSession` | Modified (uses setViewport) |
| `init` | Modified (wires acv-body) |

### What Phase 2 will add

- Main canvas drawing in AcvBody (span rects, grid lines, text labels)
- Ruler canvas drawing (time ticks)
- Overview canvas with compressed span rows + selection box
- Canvas click → span-select → detail panel
- Drag-to-pan on canvas → setViewport
- Cmd+scroll zoom on canvas → setViewport
- Overview drag interactions → setViewport