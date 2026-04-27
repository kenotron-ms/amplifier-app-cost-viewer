# Cost Viewer v2 — UI Polish Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Four frontend-only visual polish improvements to the Amplifier Cost Viewer: sidebar ruler gap alignment, smooth animated zoom, canvas-rendered spend area graph, and beautiful detail panel formatting.

**Architecture:** All changes live in two files — `viewer/amplifier_app_cost_viewer/static/app.js` (JavaScript custom elements + state) and `viewer/amplifier_app_cost_viewer/static/style.css` (light-DOM styles, mostly unused since components use shadow DOM). Tests are grep-based Python assertions in `viewer/tests/test_app_js.py` that read `app.js` as text and check for expected code patterns. No backend changes.

**Tech Stack:** Vanilla JS (ES modules), Lit `html`/`render` for shadow DOM templating, Canvas 2D API, pytest for grep-based source verification.

---

## Key Constants & File Layout

**Working directory:** `viewer/` (all relative paths below are from here)

| Constant | Value | Location |
|---|---|---|
| `ROW_H` | `32` | `app.js:23` |
| `SPAN_H` | `20` | `app.js:24` |
| `HEATMAP_H` | `20` | `app.js:25` |
| `IO_TRUNCATE` | `500` | `app.js:26` |
| `ZOOM_MIN` | `0.05` | `app.js:21` |
| `ZOOM_MAX` | `200` | `app.js:22` |
| Ruler height (CSS) | `28px` | `app.js:1110` (`#styles()` in AcvTimeline) |

There is no `RULER_H` JS constant — the ruler height is hardcoded as `28px` in the AcvTimeline shadow CSS. We will add a `RULER_H = 28` constant.

**Files to modify:**
- `amplifier_app_cost_viewer/static/app.js` (1584 lines)
- `tests/test_app_js.py` (1698 lines — append new tests)

**Test file conventions:**
- Tests live in `viewer/tests/test_app_js.py`
- Path constant: `APP_JS = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static" / "app.js"`
- Existing fixture at line 1525: `@pytest.fixture def app_js_code() -> str: return APP_JS.read_text()`
- Pattern: free functions with `app_js_code: str` fixture param, or classes with `setup_method` reading `APP_JS`
- All tests are grep-based — they search the JS source text for expected patterns
- Run from `viewer/`: `cd viewer && python -m pytest tests/test_app_js.py -v`

---

## Task 1: Sidebar Ruler Gap (Spacer Div)

**Problem:** The `<acv-tree>` rows start at `y=0`. The `<acv-timeline>` canvas rows start below the ruler (`28px`) + heatmap strip (`20px`) = `48px` offset. So tree row 0 is visually misaligned with canvas row 0.

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` — add `RULER_H` constant (~line 23), modify `AcvTree.update()` (~line 384) and `AcvTree.#styles()` (~line 423)
- Modify: `tests/test_app_js.py` — append new tests

### Step 1: Write the failing tests

Append to the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: Task 1 — Sidebar ruler gap spacer
# ---------------------------------------------------------------------------


class TestTreeRulerSpacer:
    """AcvTree must include a ruler-spacer div to align with timeline ruler+heatmap."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_ruler_h_constant_defined(self) -> None:
        """Must define RULER_H constant for ruler height."""
        assert "RULER_H" in self.content, (
            "Must define RULER_H constant (ruler height in px)"
        )

    def test_tree_has_ruler_spacer_class(self) -> None:
        """AcvTree shadow DOM must include a ruler-spacer div."""
        assert "ruler-spacer" in self.content, (
            "AcvTree must render a <div class='ruler-spacer'> to match timeline ruler+heatmap height"
        )

    def test_ruler_spacer_uses_flex_shrink_zero(self) -> None:
        """Ruler spacer must not shrink — stays fixed at top while rows scroll beneath."""
        assert "flex-shrink: 0" in self.content or "flex-shrink:0" in self.content, (
            "ruler-spacer must have flex-shrink: 0 so it doesn't compress"
        )
```

### Step 2: Run tests to verify they fail

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestTreeRulerSpacer -v
```

Expected: 3 FAILED — `RULER_H` not in source, `ruler-spacer` not in source.

### Step 3: Add `RULER_H` constant

In `amplifier_app_cost_viewer/static/app.js`, find the constants block (around line 23):

```javascript
const ROW_H       = 32;    // px per session row
```

Add immediately after it:

```javascript
const RULER_H     = 28;    // px ruler height (must match #ruler CSS)
```

### Step 4: Add spacer div to AcvTree.update()

In `AcvTree.update()`, find the render block that starts around line 403:

```javascript
    render(html`
      <style>${this.#styles()}</style>
      ${rows.map(({ node, depth, toggle, isActive, costPct }) => html`
```

Replace it with:

```javascript
    render(html`
      <style>${this.#styles()}</style>
      <div class="ruler-spacer"></div>
      ${rows.map(({ node, depth, toggle, isActive, costPct }) => html`
```

### Step 5: Add spacer styles to AcvTree.#styles()

In `AcvTree.#styles()` (starts around line 423), find the closing of the `:host` block:

```css
      }
      .panel-placeholder {
```

Insert between them:

```css
      .ruler-spacer {
        height: ${RULER_H + HEATMAP_H}px;
        flex-shrink: 0;
        background: transparent;
      }
```

**Important:** The `#styles()` method returns a template string, so `${RULER_H + HEATMAP_H}` will be evaluated as JS and interpolated to `48`. The final CSS will be `height: 48px;`.

### Step 6: Run tests to verify they pass

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestTreeRulerSpacer -v
```

Expected: 3 PASSED

### Step 7: Verify visually (manual)

Open the viewer in a browser. Tree rows should now start 48px lower, perfectly aligned with the first row of the Gantt canvas (below ruler + heatmap).

### Step 8: Commit

```bash
cd viewer && git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py && git commit -m "fix(viewer): align tree rows with timeline via ruler-spacer div"
```

---

## Task 2: Smooth Animated Zoom

**Problem:** Zoom changes `state.timeScale` instantly. Large zoom jumps look abrupt.

**Fix:** Interpolate `state.timeScale` over 100ms with ease-out cubic easing. Replace all direct `state.timeScale = ...` zoom assignments with calls to `_animateZoom(targetScale, anchorMs)`.

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` — add `_zoomAnimRaf` to state, add `_animateZoom()` function, update 6 zoom sites
- Modify: `tests/test_app_js.py` — append new tests

### Step 1: Write the failing tests

Append to the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: Task 2 — Smooth animated zoom
# ---------------------------------------------------------------------------


class TestAnimatedZoom:
    """Zoom must animate smoothly over ~100ms with easing."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_animate_zoom_function_exists(self) -> None:
        """_animateZoom function must exist for smooth zoom transitions."""
        assert "_animateZoom" in self.content, (
            "Must define _animateZoom(targetScale, anchorMs) function"
        )

    def test_zoom_uses_ease_out(self) -> None:
        """Zoom animation must use easing (not linear)."""
        assert "eased" in self.content, (
            "Zoom animation must compute an eased interpolation factor"
        )

    def test_state_has_zoom_anim_raf(self) -> None:
        """State object must track in-flight zoom animation RAF ID."""
        assert "_zoomAnimRaf" in self.content, (
            "state must have _zoomAnimRaf field to track/cancel in-flight zoom animation"
        )

    def test_zoom_animation_cancels_previous(self) -> None:
        """Starting a new zoom must cancel any in-flight animation."""
        assert "cancelAnimationFrame" in self.content, (
            "_animateZoom must cancelAnimationFrame on the previous animation"
        )

    def test_zoom_animation_uses_performance_now(self) -> None:
        """Zoom animation must use performance.now() for timing."""
        assert "performance.now" in self.content, (
            "_animateZoom must use performance.now() for frame timing"
        )
```

### Step 2: Run tests to verify they fail

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestAnimatedZoom -v
```

Expected: 5 FAILED — `_animateZoom`, `eased`, `_zoomAnimRaf`, `performance.now` not in source.

### Step 3: Add `_zoomAnimRaf` to state object

In `amplifier_app_cost_viewer/static/app.js`, find the state object (line 33–45). Add after `loading: false,`:

```javascript
  _zoomAnimRaf:  null,  // RAF ID for in-flight zoom animation
```

### Step 4: Add `_animateZoom()` function

Insert this function immediately after the `_rowIndexMap()` function (after line 242, before the `// Section 6: Custom element — AcvToolbar` comment):

```javascript
// =============================================================================
// Section 5c: Animated zoom helper
// =============================================================================

/**
 * Animate state.timeScale from its current value to targetScale over 100ms.
 * Uses ease-out cubic: t * (2 - t) for a fast start and smooth finish.
 *
 * @param {number}      targetScale - desired final ms/px value
 * @param {number|null} anchorMs    - time in ms that should stay fixed on screen
 *                                    (null = no anchor, just zoom in place)
 * @param {number|null} anchorPx    - the screen-space px position of anchorMs
 */
function _animateZoom(targetScale, anchorMs, anchorPx) {
  const startScale = state.timeScale;
  const startScrollLeft = state.scrollLeft;
  const startTime = performance.now();
  const DURATION = 100; // ms

  // Cancel any in-flight zoom animation
  if (state._zoomAnimRaf) cancelAnimationFrame(state._zoomAnimRaf);

  function step(now) {
    const elapsed = now - startTime;
    const t = Math.min(elapsed / DURATION, 1);
    // Ease-out cubic: fast start, smooth finish
    const eased = t * (2 - t);
    state.timeScale = startScale + (targetScale - startScale) * eased;

    // Keep anchorMs fixed at anchorPx on screen
    if (anchorMs != null && anchorPx != null) {
      state.scrollLeft = Math.max(0, anchorMs / state.timeScale - anchorPx);
    }

    renderAll();

    if (t < 1) {
      state._zoomAnimRaf = requestAnimationFrame(step);
    } else {
      state.timeScale = targetScale; // exact final value
      if (anchorMs != null && anchorPx != null) {
        state.scrollLeft = Math.max(0, anchorMs / state.timeScale - anchorPx);
      }
      state._zoomAnimRaf = null;
      renderAll();
    }
  }
  state._zoomAnimRaf = requestAnimationFrame(step);
}
```

### Step 5: Replace zoom site 1 — ruler wheel handler

In `AcvTimeline.#onRulerWheel()` (line ~1030), find these lines:

```javascript
    // Zoom factor
    const factor = e.deltaY > 0 ? 1.15 : 0.87;
    state.timeScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, state.timeScale * factor));

    // Adjust scrollLeft so the same ms stays under cursor
    state.scrollLeft = Math.max(0, msAtCursor / state.timeScale - cursorPx);

    renderAll();
```

Replace with:

```javascript
    // Zoom factor
    const factor = e.deltaY > 0 ? 1.15 : 0.87;
    const targetScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, state.timeScale * factor));
    _animateZoom(targetScale, msAtCursor, cursorPx);
```

### Step 6: Replace zoom site 2 — canvas Ctrl+scroll handler

In the canvas wheel handler (line ~661), find these lines (inside the `canvas.addEventListener('wheel', e => { ... })` block that checks `ctrlKey`):

```javascript
        state.timeScale = newScale;

        // Keep cursor ms fixed: cursorMs / newScale - cursorX = new scrollLeft
        state.scrollLeft = Math.max(0, cursorMs / newScale - cursorX);

        // Update zoom label
        const label = this._root.querySelector('#zoom-label')
          || document.getElementById('zoom-label');
        if (label) {
          label.textContent = newScale < 1
            ? `${(1 / newScale).toFixed(1)}px/ms`
            : `${newScale.toFixed(0)}ms/px`;
        }

        // RAF-debounced redraw (same pattern as ruler zoom)
        if (this._zoomRaf) cancelAnimationFrame(this._zoomRaf);
        this._zoomRaf = requestAnimationFrame(() => {
          this.#draw();
          this._zoomRaf = null;
        });
```

Replace with:

```javascript
        _animateZoom(newScale, cursorMs, cursorX);
```

### Step 7: Replace zoom site 3 — toolbar zoom-in button

In `init()` (line ~1447), find:

```javascript
    toolbar.addEventListener('zoom-in', () => {
      state.timeScale = Math.max(ZOOM_MIN, state.timeScale / 1.5);
      renderAll();
    });
```

Replace with:

```javascript
    toolbar.addEventListener('zoom-in', () => {
      const targetScale = Math.max(ZOOM_MIN, state.timeScale / 1.5);
      _animateZoom(targetScale, null, null);
    });
```

### Step 8: Replace zoom site 4 — toolbar zoom-out button

In `init()` (line ~1453), find:

```javascript
    toolbar.addEventListener('zoom-out', () => {
      state.timeScale = Math.min(ZOOM_MAX, state.timeScale * 1.5);
      renderAll();
    });
```

Replace with:

```javascript
    toolbar.addEventListener('zoom-out', () => {
      const targetScale = Math.min(ZOOM_MAX, state.timeScale * 1.5);
      _animateZoom(targetScale, null, null);
    });
```

### Step 9: Replace zoom site 5 — W/= key (zoom in)

In the keydown handler (line ~1533), find:

```javascript
      case 'KeyW':
      case 'Equal': // = key (zoom in)
        e.preventDefault();
        state.timeScale = Math.max(ZOOM_MIN, state.timeScale * Math.pow(0.7, shift));
        renderAll();
        break;
```

Replace with:

```javascript
      case 'KeyW':
      case 'Equal': // = key (zoom in)
        e.preventDefault();
        _animateZoom(Math.max(ZOOM_MIN, state.timeScale * Math.pow(0.7, shift)), null, null);
        break;
```

### Step 10: Replace zoom site 6 — S/- key (zoom out)

In the keydown handler (line ~1540), find:

```javascript
      case 'KeyS':
      case 'Minus': // - key (zoom out)
        e.preventDefault();
        state.timeScale = Math.min(ZOOM_MAX, state.timeScale * Math.pow(1.3, shift));
        renderAll();
        break;
```

Replace with:

```javascript
      case 'KeyS':
      case 'Minus': // - key (zoom out)
        e.preventDefault();
        _animateZoom(Math.min(ZOOM_MAX, state.timeScale * Math.pow(1.3, shift)), null, null);
        break;
```

**Do NOT change** the `loadSession()` initial zoom assignment at line ~1418 (`state.timeScale = maxEndMs / ...`). That's a one-time fit-to-view, not an interactive zoom.

### Step 11: Run tests to verify they pass

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestAnimatedZoom -v
```

Expected: 5 PASSED

### Step 12: Run full test suite for regression

```bash
cd viewer && python -m pytest tests/test_app_js.py -v
```

Expected: All existing tests still pass. (The existing zoom tests check for `ctrlKey`, `metaKey`, `passive: false`, etc. — those are all still present.)

### Step 13: Commit

```bash
cd viewer && git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py && git commit -m "feat(viewer): smooth animated zoom with ease-out cubic easing"
```

---

## Task 3: Spend Area Graph (Canvas Heatmap)

**Problem:** The current cost heatmap uses CSS div bars (`el.innerHTML = ...` with absolute-positioned divs). It works but looks crude. Replace with a Canvas-rendered filled area chart with gradient fill and peak marker.

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` — rewrite `AcvTimeline.#renderHeatmap()`, change heatmap element from `<div>` to `<canvas>` in `update()`, update `#styles()`
- Modify: `tests/test_app_js.py` — append new tests

### Step 1: Write the failing tests

Append to the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: Task 3 — Spend area graph (canvas heatmap)
# ---------------------------------------------------------------------------


class TestHeatmapAreaGraph:
    """Heatmap must be a canvas-rendered area graph, not CSS div bars."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_heatmap_uses_canvas_element(self) -> None:
        """Heatmap must use a canvas element, not divs."""
        assert "heatmap-canvas" in self.content, (
            "Heatmap must use a <canvas id='heatmap-canvas'> element"
        )

    def test_heatmap_has_gradient_fill(self) -> None:
        """Heatmap area must use gradient fill."""
        assert "createLinearGradient" in self.content, (
            "Heatmap must use createLinearGradient for area fill"
        )

    def test_heatmap_has_peak_marker(self) -> None:
        """Heatmap must mark the peak cost bucket with amber."""
        assert "f59e0b" in self.content, (
            "Heatmap must use amber (#f59e0b) for peak cost marker"
        )

    def test_heatmap_uses_float64_buckets(self) -> None:
        """Heatmap must use Float64Array for cost buckets."""
        assert "Float64Array" in self.content, (
            "Heatmap must use Float64Array for cost accumulation buckets"
        )

    def test_heatmap_uses_purple_gradient(self) -> None:
        """Heatmap area must use Anthropic purple gradient."""
        assert "123, 47, 190" in self.content or "7b2fbe" in self.content.lower(), (
            "Heatmap must use purple (rgb 123,47,190) for area fill"
        )
```

### Step 2: Run tests to verify they fail

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestHeatmapAreaGraph -v
```

Expected: At least 3 FAILED — `heatmap-canvas` not in source, `createLinearGradient` not in source. (`Float64Array` and `f59e0b` already exist in the old heatmap but `heatmap-canvas` and `createLinearGradient` do not.)

### Step 3: Change heatmap element from div to canvas in `update()`

In `AcvTimeline.update()` (line ~582), find:

```javascript
      <div id="heatmap"></div>
```

Replace with:

```javascript
      <canvas id="heatmap-canvas"></canvas>
```

### Step 4: Update the `#renderHeatmap()` selector

Replace the entire `#renderHeatmap()` method (lines ~938–981) with:

```javascript
  /**
   * Canvas-rendered spend area graph.
   * Bucketizes spans by cost into 4px-wide columns, draws a filled area
   * chart with purple gradient and amber peak marker.
   */
  #renderHeatmap(spans, ts, scrollL) {
    const canvas = this._root.querySelector('#heatmap-canvas');
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || 800;
    const height = HEATMAP_H;

    // Resize canvas for DPR
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, width, height);

    if (!spans || spans.length === 0) return;

    // Bucketize: one bucket per 4px
    const N = Math.max(1, Math.ceil(width / 4));
    const buckets = new Float64Array(N);

    // Total session duration in ms
    const totalMs = spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
    const msPerBucket = totalMs / N;

    for (const s of spans) {
      const cost = s.cost_usd || 0;
      if (cost <= 0) continue;
      const b = Math.floor((s.start_ms || 0) / msPerBucket);
      if (b >= 0 && b < N) buckets[b] += cost;
    }

    // Find peak
    let maxBucket = 0;
    let peakIdx = 0;
    for (let i = 0; i < N; i++) {
      if (buckets[i] > maxBucket) { maxBucket = buckets[i]; peakIdx = i; }
    }
    if (maxBucket <= 0) return;

    // Draw filled area path
    ctx.beginPath();
    ctx.moveTo(0, height);
    for (let i = 0; i < N; i++) {
      const x = (i / N) * width;
      const y = height - (buckets[i] / maxBucket) * (height - 2);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(width, height);
    ctx.closePath();

    // Gradient fill: Anthropic purple at top → transparent at bottom
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, 'rgba(123, 47, 190, 0.8)');
    grad.addColorStop(1, 'rgba(123, 47, 190, 0.1)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Peak marker: amber dot at highest bucket
    const peakX = (peakIdx / N) * width;
    const peakY = height - (buckets[peakIdx] / maxBucket) * (height - 2);
    ctx.beginPath();
    ctx.arc(peakX, peakY, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#f59e0b';
    ctx.fill();
  }
```

### Step 5: Update heatmap styles in `AcvTimeline.#styles()`

In `AcvTimeline.#styles()` (line ~1088), find:

```css
      #heatmap {
        height: 20px;
        position: relative;
        overflow: hidden;
        flex-shrink: 0;
        background: var(--bg, #0d1117);
      }
```

Replace with:

```css
      #heatmap-canvas {
        display: block;
        width: 100%;
        height: 20px;
        flex-shrink: 0;
        background: var(--bg, #0d1117);
      }
```

### Step 6: Run tests to verify they pass

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestHeatmapAreaGraph -v
```

Expected: 5 PASSED

### Step 7: Run full test suite for regression

```bash
cd viewer && python -m pytest tests/test_app_js.py -v
```

Expected: All tests pass. Some old heatmap tests in `TestAcvTimeline` may reference `#heatmap` or `innerHTML` — check for failures and update those specific assertions if needed. The key old tests to check:

- Look for any test asserting `#heatmap` or `innerHTML` in the heatmap section — these would need updating to reference `#heatmap-canvas` and `getContext` instead.

If any old test fails because it asserts `#heatmap` (without `-canvas`), update that test to assert `heatmap-canvas` instead. If a test asserts `innerHTML` specifically for heatmap, remove or update it since we no longer use innerHTML for the heatmap.

### Step 8: Commit

```bash
cd viewer && git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py && git commit -m "feat(viewer): canvas-rendered spend area graph replaces CSS div heatmap"
```

---

## Task 4: Beautiful Detail Panel

**Problem:** The detail panel shows raw JSON for input/output and uses raw numbers for tokens. Duration shows raw `start → end` format. The detail panel needs human-readable formatting.

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` — rewrite `AcvDetail` methods: `#llmRows()`, `#toolRows()`, `#ioBlock()`, add `_formatDuration()`, `_extractContent()`, `_renderToolInput()`
- Modify: `tests/test_app_js.py` — append new tests

### Step 1: Write the failing tests

Append to the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: Task 4 — Beautiful detail panel
# ---------------------------------------------------------------------------


class TestDetailPanelFormatting:
    """Detail panel must format content beautifully — no raw JSON."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_detail_has_format_duration_helper(self) -> None:
        """Detail panel must have a dedicated duration formatting helper."""
        assert "_formatDuration" in self.content, (
            "Must define _formatDuration(ms) helper for human-readable durations"
        )

    def test_detail_has_extract_content_helper(self) -> None:
        """Detail panel must extract text from message arrays."""
        assert "_extractContent" in self.content, (
            "Must define _extractContent(value) to extract readable text from "
            "message arrays and structured output objects"
        )

    def test_detail_uses_locale_string_for_tokens(self) -> None:
        """Token counts must use toLocaleString for comma-separated formatting."""
        assert "toLocaleString" in self.content, (
            "Token counts must use .toLocaleString() for human-friendly formatting "
            "(e.g., 52,495 not 52495)"
        )

    def test_detail_has_render_tool_input_helper(self) -> None:
        """Tool detail must render input dict as key: value lines."""
        assert "_renderToolInput" in self.content, (
            "Must define _renderToolInput(input) to render tool input as "
            "key: value lines instead of raw JSON"
        )

    def test_detail_handles_tool_use_output(self) -> None:
        """LLM output must handle tool_use content blocks."""
        assert "tool_use" in self.content, (
            "Detail panel must detect and format tool_use content blocks in LLM output"
        )

    def test_detail_panel_has_stats_grid(self) -> None:
        """Detail panel must use a stats grid layout for duration/cost/tokens."""
        assert "detail-stats" in self.content or "stats-grid" in self.content, (
            "Detail panel must use a stats grid for the duration/cost/tokens row"
        )

    def test_detail_panel_uses_pre_wrap(self) -> None:
        """I/O content must use pre-wrap for formatted text display."""
        assert "pre-wrap" in self.content, (
            "I/O content blocks must use white-space: pre-wrap"
        )
```

### Step 2: Run tests to verify they fail

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestDetailPanelFormatting -v
```

Expected: At least 4 FAILED — `_formatDuration`, `_extractContent`, `_renderToolInput`, `toLocaleString` not in source. (`pre-wrap` already exists; `tool_use` may not.)

### Step 3: Add helper functions

In `amplifier_app_cost_viewer/static/app.js`, insert these three helpers right after the existing `_fmtTokens()` function (after line ~174, before the `_formatDate` function):

```javascript
/**
 * Format a duration in ms as a short human-readable string for the detail panel.
 * < 1000 ms → "342ms"
 * < 60s     → "4.2s"
 * else      → "2m 15s"
 */
function _formatDuration(ms) {
  if (ms == null || ms < 0) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.round((ms % 60000) / 1000);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

/**
 * Extract human-readable text from an LLM input or output value.
 *
 * Handles these shapes:
 * - string → return as-is
 * - array of messages [{role, content}] → extract last user message content
 * - {role, content: [{type:'text', text:'...'}]} → extract text
 * - {role, content: [{type:'tool_use', name:'...'}]} → "[called: name]"
 * - null/undefined → "—"
 */
function _extractContent(value) {
  if (value == null) return '—';
  if (typeof value === 'string') return value;

  // Array of messages: extract last user message
  if (Array.isArray(value)) {
    // Find the last user message
    for (let i = value.length - 1; i >= 0; i--) {
      const msg = value[i];
      if (msg && msg.role === 'user') {
        const c = msg.content;
        if (typeof c === 'string') return c;
        if (Array.isArray(c)) {
          const textBlock = c.find(b => b.type === 'text');
          if (textBlock) return textBlock.text || '—';
        }
        return typeof c === 'object' ? JSON.stringify(c) : String(c);
      }
    }
    // No user message found — try last assistant message
    const last = value[value.length - 1];
    if (last?.content) {
      const c = last.content;
      if (typeof c === 'string') return c;
      if (Array.isArray(c)) {
        const textBlock = c.find(b => b.type === 'text');
        if (textBlock) return textBlock.text || '—';
        const toolBlock = c.find(b => b.type === 'tool_use');
        if (toolBlock) return `[called: ${toolBlock.name || 'unknown'}]`;
      }
    }
    return '—';
  }

  // Single message object: {role, content: [...]}
  if (value.content) {
    const c = value.content;
    if (typeof c === 'string') return c;
    if (Array.isArray(c)) {
      const textBlock = c.find(b => b.type === 'text');
      if (textBlock) return textBlock.text || '—';
      const toolBlock = c.find(b => b.type === 'tool_use');
      if (toolBlock) return `[called: ${toolBlock.name || 'unknown'}]`;
    }
  }

  return '—';
}

/**
 * Render a tool input value as "key: value" lines.
 * If the input is a dict/object, renders each key on its own line.
 * If it's a string, returns it as-is.
 * If null, returns "—".
 */
function _renderToolInput(input) {
  if (input == null) return '—';
  if (typeof input === 'string') return input;
  if (typeof input === 'object' && !Array.isArray(input)) {
    return Object.entries(input)
      .map(([k, v]) => {
        const val = typeof v === 'string' ? v : JSON.stringify(v);
        return `${k}: ${val}`;
      })
      .join('\n');
  }
  return JSON.stringify(input, null, 2);
}
```

### Step 4: Rewrite `AcvDetail.update()` method

Replace the entire `update()` method in `AcvDetail` (lines ~1176–1196) with:

```javascript
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
          ${span.type === 'thinking' ? '' : html`
            ${this.#contentBlock('INPUT', span.input, span.type)}
            ${this.#contentBlock('OUTPUT', span.output, span.type)}
          `}
        </div>
      ` : html`<div class="hidden"></div>`}
    `, this._root);
  }
```

### Step 5: Replace `#timingRow()`, `#llmRows()`, `#toolRows()` with `#statsBlock()`

Remove the existing `#timingRow()` (lines ~1232–1239), `#llmRows()` (lines ~1243–1254), and `#toolRows()` (lines ~1258–1264) methods. Replace all three with a single `#statsBlock()`:

```javascript
  // ---------------------------------------------------------------------------
  // Private: stats block — two-column grid of duration, cost, tokens
  // ---------------------------------------------------------------------------

  #statsBlock(span) {
    const startMs  = span.start_ms || 0;
    const endMs    = span.end_ms   || 0;
    const duration = Math.max(0, endMs - startMs);

    if (span.type === 'thinking') {
      return html`
        <div class="stat"><span class="stat-label">Duration</span><span class="stat-value">${_formatDuration(duration)}</span></div>
      `;
    }

    if (span.type === 'tool') {
      const { icon, color } = this.#successDisplay(span);
      return html`
        <div class="stat"><span class="stat-label">Duration</span><span class="stat-value">${_formatDuration(duration)}</span></div>
        <div class="stat"><span class="stat-label">Status</span><span class="stat-value" style="color:${color}">${icon} ${span.success !== false ? 'Success' : 'Failed'}</span></div>
      `;
    }

    // LLM span
    const inputTok  = span.input_tokens  || 0;
    const outputTok = span.output_tokens || 0;
    const stats = [
      html`<div class="stat"><span class="stat-label">Duration</span><span class="stat-value">${_formatDuration(duration)}</span></div>`,
      span.cost_usd != null
        ? html`<div class="stat"><span class="stat-label">Cost</span><span class="stat-value">$${span.cost_usd.toFixed(4)}</span></div>`
        : '',
      html`<div class="stat"><span class="stat-label">Input tok</span><span class="stat-value">${inputTok.toLocaleString()}</span></div>`,
      html`<div class="stat"><span class="stat-label">Output tok</span><span class="stat-value">${outputTok.toLocaleString()}</span></div>`,
    ];
    if (span.cache_read_tokens) {
      stats.push(html`<div class="stat"><span class="stat-label">Cache read</span><span class="stat-value">${span.cache_read_tokens.toLocaleString()}</span></div>`);
    }
    if (span.cache_write_tokens) {
      stats.push(html`<div class="stat"><span class="stat-label">Cache write</span><span class="stat-value">${span.cache_write_tokens.toLocaleString()}</span></div>`);
    }
    return stats;
  }
```

### Step 6: Replace `#ioBlock()` with `#contentBlock()`

Remove the existing `#ioBlock()` method (lines ~1277–1299). Replace with:

```javascript
  // ---------------------------------------------------------------------------
  // Private: content blocks — INPUT / OUTPUT with smart extraction
  // ---------------------------------------------------------------------------

  #contentBlock(label, value, spanType) {
    if (value == null) return '';

    // Extract readable content based on span type
    let text;
    if (label === 'INPUT' && spanType === 'tool') {
      text = _renderToolInput(value);
    } else {
      text = _extractContent(value);
    }

    if (!text || text === '—') return '';

    const truncated = text.length > IO_TRUNCATE;
    const display   = truncated ? text.slice(0, IO_TRUNCATE) + '…' : text;

    const handleShowMore = (e) => {
      e.preventDefault();
      const block = e.target.closest('.io-block');
      const pre   = block?.querySelector('pre');
      if (pre) pre.textContent = text;
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
```

### Step 7: Update `AcvDetail.#styles()` for the stats grid

Replace the existing `#styles()` method in AcvDetail (lines ~1318–1386) with:

```javascript
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
        gap: 6px 16px;
        margin-bottom: 10px;
        padding: 8px 0;
        border-bottom: 1px solid var(--border, #30363d);
      }
      .stat {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .stat-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted, #8b949e);
      }
      .stat-value {
        font-size: 13px;
        font-weight: 500;
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
        padding: 8px 10px;
        border-radius: 4px;
        overflow: auto;
        max-height: 120px;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 11px;
        line-height: 1.5;
        color: var(--text, #e6edf3);
        border: 1px solid var(--border, #30363d);
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
```

### Step 8: Run tests to verify they pass

```bash
cd viewer && python -m pytest tests/test_app_js.py::TestDetailPanelFormatting -v
```

Expected: 7 PASSED

### Step 9: Run full test suite for regression

```bash
cd viewer && python -m pytest tests/test_app_js.py -v
```

Expected: Most tests pass. Check for failures in `TestAcvDetail` — some old tests may assert on `#timingRow`, `#llmRows`, `#toolRows`, `#ioBlock`, or the old `.grid` CSS class. For each failure:

- If a test asserts `#timingRow` → it still exists conceptually inside `#statsBlock()`. The old `#timingRow` private method name is gone. Update the test to check for `#statsBlock` or `_formatDuration` instead.
- If a test asserts `#llmRows` → update to check for `toLocaleString` or `#statsBlock`.
- If a test asserts `#ioBlock` → update to check for `#contentBlock`.
- The string `"grid"` still appears (in `detail-stats` grid CSS), so `.grid` class tests may pass or need minor adjustment.

**Important:** Preserve the intent of each old test — only change the specific assertion string, not the test's purpose. If a test checked "llmRows shows token counts," change it to verify `toLocaleString` is used.

### Step 10: Commit

```bash
cd viewer && git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py && git commit -m "feat(viewer): beautiful detail panel with formatted durations, tokens, and content extraction"
```

---

## Final Verification

After all 4 tasks are complete, run the full test suite one final time:

```bash
cd viewer && python -m pytest tests/test_app_js.py -v
```

Expected: ALL tests pass (existing + 20 new tests across 4 new test classes).

### New test class summary

| Class | Tests | Task |
|---|---|---|
| `TestTreeRulerSpacer` | 3 | Task 1 |
| `TestAnimatedZoom` | 5 | Task 2 |
| `TestHeatmapAreaGraph` | 5 | Task 3 |
| `TestDetailPanelFormatting` | 7 | Task 4 |
| **Total new** | **20** | |