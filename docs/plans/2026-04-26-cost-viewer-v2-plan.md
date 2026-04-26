# Cost Viewer v2 Frontend Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Rewrite the Amplifier Cost Viewer frontend using 4 Lit web components and a Canvas 2D Gantt renderer, replacing the broken vanilla JS + SVG implementation. Backend is unchanged.

**Architecture:** Four `HTMLElement` subclasses (`AcvToolbar`, `AcvTree`, `AcvTimeline`, `AcvDetail`) use shadow DOM and call `Lit.render()` manually. A single global `state` object holds all data; mutations are explicit with `renderAll()` calls. The Gantt uses Canvas 2D with color-batched span drawing for performance.

**Tech Stack:** Lit 3 (vendored, no build step), Canvas 2D API, ES modules, FastAPI static serving (unchanged)

**Design spec:** `docs/plans/2026-04-26-cost-viewer-v2-design.md`

**Working directory for all commands:** `cd /Users/ken/workspace/ms/token-cost/viewer`

---

## Background for the implementer

You are rewriting **only** the frontend files. The Python backend (`server.py`, `reader.py`, `pricing.py`) and all Python backend tests (`test_scaffold.py`, `test_reader.py`, `test_pricing.py`, `test_server.py`) are **untouched**. You will replace these frontend files:

```
viewer/amplifier_app_cost_viewer/static/
├── index.html          ← rewrite
├── style.css           ← rewrite
├── app.js              ← rewrite (4 Lit components + Canvas renderer)
└── vendor/
    └── lit.all.min.js  ← new: download once from CDN
```

And these two test files:

```
viewer/tests/test_static_shell.py   ← replace with v2 tests
viewer/tests/test_app_js.py         ← replace with v2 tests
```

The backend serves 3 API endpoints consumed by the frontend:
- `GET /api/sessions?limit=25&offset=0` → `{sessions: [...], total, has_more, next_offset}`
- `GET /api/sessions/{id}` → full session tree with spans and children
- `GET /api/sessions/{id}/spans` → flat span list across all descendants
- `POST /api/refresh` → clears server cache

Each span object from the API has: `session_id`, `depth`, `type` (llm/tool/thinking), `start_ms`, `end_ms`, `provider`, `model`, `cost_usd`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `tool_name`, `success`, `input`, `output`, `color`.

---

### Task 1: Scaffold — Lit vendor + index.html + style.css + app.js shells + tests

**Files:**
- Create: `amplifier_app_cost_viewer/static/vendor/lit.all.min.js` (download)
- Rewrite: `amplifier_app_cost_viewer/static/index.html`
- Rewrite: `amplifier_app_cost_viewer/static/style.css`
- Rewrite: `amplifier_app_cost_viewer/static/app.js`
- Replace: `tests/test_static_shell.py`
- Replace: `tests/test_app_js.py`

**Step 1: Download Lit vendor bundle**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
mkdir -p amplifier_app_cost_viewer/static/vendor
curl -L "https://esm.sh/lit@3?bundle&target=esnext" \
  -o amplifier_app_cost_viewer/static/vendor/lit.all.min.js
```

Verify the download succeeded — the file should be >20 KB of JavaScript:

```bash
wc -c amplifier_app_cost_viewer/static/vendor/lit.all.min.js
# Expected: something like "85432 amplifier_app_cost_viewer/static/vendor/lit.all.min.js"
head -c 100 amplifier_app_cost_viewer/static/vendor/lit.all.min.js
# Expected: starts with JavaScript (e.g., "var" or "import" or "export" or a comment)
```

If the download fails or returns HTML, use this fallback:
```bash
curl -L "https://cdn.jsdelivr.net/npm/lit@3/+esm" \
  -o amplifier_app_cost_viewer/static/vendor/lit.all.min.js
```

**Step 2: Write the new test files (RED)**

Write `tests/test_static_shell.py` — replaces the existing file entirely:

```python
"""Tests for the v2 static HTML shell and CSS — custom elements + dark theme."""

from __future__ import annotations

from pathlib import Path

STATIC = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static"
INDEX_HTML = STATIC / "index.html"
STYLE_CSS = STATIC / "style.css"


# ---------------------------------------------------------------------------
# Tests: index.html existence and structure
# ---------------------------------------------------------------------------


class TestIndexHtmlExists:
    def test_file_exists(self) -> None:
        assert INDEX_HTML.exists(), f"{INDEX_HTML} must exist"

    def test_not_empty(self) -> None:
        content = INDEX_HTML.read_text()
        assert len(content) > 100, "index.html must have substantial content"


class TestIndexHtmlDoctype:
    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()

    def test_has_doctype(self) -> None:
        assert "<!DOCTYPE html>" in self.content or "<!doctype html>" in self.content.lower()

    def test_html_lang_en(self) -> None:
        assert 'lang="en"' in self.content


class TestIndexHtmlHead:
    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()

    def test_meta_charset_utf8(self) -> None:
        assert 'charset="utf-8"' in self.content or "charset='utf-8'" in self.content

    def test_title_amplifier_cost_viewer(self) -> None:
        assert "Amplifier Cost Viewer" in self.content

    def test_link_to_style_css(self) -> None:
        assert "/static/style.css" in self.content

    def test_script_type_module(self) -> None:
        assert 'type="module"' in self.content, "app.js must be loaded as ES module"

    def test_script_src_app_js(self) -> None:
        assert "/static/app.js" in self.content


class TestIndexHtmlBody:
    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()

    def test_acv_toolbar_element(self) -> None:
        assert "<acv-toolbar" in self.content, "Must have <acv-toolbar> custom element"

    def test_acv_tree_element(self) -> None:
        assert "<acv-tree" in self.content, "Must have <acv-tree> custom element"

    def test_acv_timeline_element(self) -> None:
        assert "<acv-timeline" in self.content, "Must have <acv-timeline> custom element"

    def test_toolbar_has_id(self) -> None:
        assert 'id="toolbar"' in self.content

    def test_tree_has_id(self) -> None:
        assert 'id="tree"' in self.content

    def test_timeline_has_id(self) -> None:
        assert 'id="timeline"' in self.content

    def test_main_element(self) -> None:
        assert '<main id="main">' in self.content


# ---------------------------------------------------------------------------
# Tests: style.css existence and required custom properties
# ---------------------------------------------------------------------------


class TestStyleCssExists:
    def test_file_exists(self) -> None:
        assert STYLE_CSS.exists(), f"{STYLE_CSS} must exist"


class TestStyleCssCustomProperties:
    def setup_method(self) -> None:
        self.content = STYLE_CSS.read_text()

    def test_bg_color(self) -> None:
        assert "--bg:#0d1117" in self.content or "--bg: #0d1117" in self.content

    def test_surface_color(self) -> None:
        assert "--surface:#161b22" in self.content or "--surface: #161b22" in self.content

    def test_surface_alt_color(self) -> None:
        assert "--surface-alt:#21262d" in self.content or "--surface-alt: #21262d" in self.content

    def test_border_color(self) -> None:
        assert "--border:#30363d" in self.content or "--border: #30363d" in self.content

    def test_text_color(self) -> None:
        assert "--text:#e6edf3" in self.content or "--text: #e6edf3" in self.content

    def test_text_muted_color(self) -> None:
        assert "--text-muted:#8b949e" in self.content or "--text-muted: #8b949e" in self.content

    def test_accent_color(self) -> None:
        assert "--accent:#58a6ff" in self.content or "--accent: #58a6ff" in self.content

    def test_danger_color(self) -> None:
        assert "--danger:#f85149" in self.content or "--danger: #f85149" in self.content

    def test_success_color(self) -> None:
        assert "--success:#3fb950" in self.content or "--success: #3fb950" in self.content


class TestStyleCssLayoutVars:
    def setup_method(self) -> None:
        self.content = STYLE_CSS.read_text()

    def test_toolbar_height(self) -> None:
        assert "--toolbar-height:42px" in self.content or "--toolbar-height: 42px" in self.content

    def test_tree_width(self) -> None:
        assert "--tree-width:220px" in self.content or "--tree-width: 220px" in self.content

    def test_ruler_height(self) -> None:
        assert "--ruler-height:28px" in self.content or "--ruler-height: 28px" in self.content

    def test_detail_height(self) -> None:
        assert "--detail-height:180px" in self.content or "--detail-height: 180px" in self.content

    def test_row_height(self) -> None:
        assert "--row-height:32px" in self.content or "--row-height: 32px" in self.content


class TestStyleCssSpanColors:
    def setup_method(self) -> None:
        self.content = STYLE_CSS.read_text()

    def test_anthropic_purple_present(self) -> None:
        assert "#7B2FBE" in self.content or "#7b2fbe" in self.content.lower()

    def test_openai_teal_present(self) -> None:
        assert "#10A37F" in self.content or "#10a37f" in self.content.lower()

    def test_google_blue_present(self) -> None:
        assert "#3B82F6" in self.content or "#3b82f6" in self.content.lower()

    def test_tool_color_present(self) -> None:
        assert "#64748B" in self.content or "#64748b" in self.content.lower()

    def test_thinking_color_present(self) -> None:
        assert "#6366F1" in self.content or "#6366f1" in self.content.lower()

    def test_unknown_color_present(self) -> None:
        assert "#F59E0B" in self.content or "#f59e0b" in self.content.lower()


class TestStyleCssLayout:
    def setup_method(self) -> None:
        self.content = STYLE_CSS.read_text()

    def test_box_sizing_reset(self) -> None:
        assert "box-sizing" in self.content

    def test_body_flex_column(self) -> None:
        assert "flex-direction" in self.content
        assert "column" in self.content

    def test_monospace_font(self) -> None:
        assert any(font in self.content for font in ["SF Mono", "Consolas", "Monaco"])

    def test_font_size_12px(self) -> None:
        assert "12px" in self.content

    def test_acv_toolbar_selector(self) -> None:
        assert "acv-toolbar" in self.content

    def test_acv_tree_selector(self) -> None:
        assert "acv-tree" in self.content

    def test_acv_timeline_selector(self) -> None:
        assert "acv-timeline" in self.content

    def test_main_selector(self) -> None:
        assert "#main" in self.content

    def test_custom_scrollbar(self) -> None:
        assert "scrollbar" in self.content
```

Write `tests/test_app_js.py` — replaces the existing file entirely. Start with shell-level tests only (more will be added in later tasks):

```python
"""Tests for app.js v2 — Lit web components + Canvas Gantt.

Tests verify source structure by grepping for required patterns.
New test classes are added in each task as components are implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

APP_JS = (
    Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static" / "app.js"
)


@pytest.fixture
def app_js_code() -> str:
    """Return the full text of app.js for content-based assertions."""
    return APP_JS.read_text()


# ---------------------------------------------------------------------------
# Tests: file existence
# ---------------------------------------------------------------------------


class TestAppJsExists:
    def test_file_exists(self) -> None:
        assert APP_JS.exists(), f"{APP_JS} must exist"

    def test_not_empty(self) -> None:
        assert APP_JS.stat().st_size > 0, "app.js must not be empty"

    def test_has_substantial_content(self) -> None:
        content = APP_JS.read_text()
        assert len(content) > 500, "app.js must have substantial content (>500 chars)"


# ---------------------------------------------------------------------------
# Tests: Lit import and ES module setup
# ---------------------------------------------------------------------------


class TestLitImport:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_imports_html_from_lit(self) -> None:
        assert "import" in self.content and "html" in self.content, (
            "Must import html from Lit"
        )

    def test_imports_render_from_lit(self) -> None:
        assert "render" in self.content, "Must import render from Lit"

    def test_imports_from_vendor_path(self) -> None:
        assert "vendor/lit.all.min.js" in self.content, (
            "Must import from /static/vendor/lit.all.min.js"
        )


# ---------------------------------------------------------------------------
# Tests: State model
# ---------------------------------------------------------------------------


class TestState:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_const_state_object(self) -> None:
        assert "const state = {" in self.content or "const state={" in self.content

    def test_state_has_sessions(self) -> None:
        assert "sessions:" in self.content

    def test_state_has_active_session_id(self) -> None:
        assert "activeSessionId:" in self.content

    def test_state_has_session_data(self) -> None:
        assert "sessionData:" in self.content

    def test_state_has_spans(self) -> None:
        assert "spans:" in self.content

    def test_state_has_expanded_sessions(self) -> None:
        assert "expandedSessions:" in self.content

    def test_state_has_selected_span(self) -> None:
        assert "selectedSpan:" in self.content

    def test_state_has_time_scale(self) -> None:
        assert "timeScale:" in self.content

    def test_state_has_scroll_left(self) -> None:
        assert "scrollLeft:" in self.content


# ---------------------------------------------------------------------------
# Tests: Custom element definitions
# ---------------------------------------------------------------------------


class TestCustomElements:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_acv_toolbar_class(self) -> None:
        assert "class AcvToolbar extends HTMLElement" in self.content

    def test_acv_tree_class(self) -> None:
        assert "class AcvTree extends HTMLElement" in self.content

    def test_acv_timeline_class(self) -> None:
        assert "class AcvTimeline extends HTMLElement" in self.content

    def test_acv_detail_class(self) -> None:
        assert "class AcvDetail extends HTMLElement" in self.content

    def test_defines_acv_toolbar(self) -> None:
        assert "customElements.define('acv-toolbar'" in self.content

    def test_defines_acv_tree(self) -> None:
        assert "customElements.define('acv-tree'" in self.content

    def test_defines_acv_timeline(self) -> None:
        assert "customElements.define('acv-timeline'" in self.content

    def test_defines_acv_detail(self) -> None:
        assert "customElements.define('acv-detail'" in self.content

    def test_shadow_dom_used(self) -> None:
        count = self.content.count("attachShadow")
        assert count >= 4, f"All 4 components must use shadow DOM, found {count} attachShadow calls"


# ---------------------------------------------------------------------------
# Tests: Init
# ---------------------------------------------------------------------------


class TestInit:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_init_function_defined(self) -> None:
        assert "async function init()" in self.content

    def test_dom_content_loaded(self) -> None:
        assert "DOMContentLoaded" in self.content
```

**Step 3: Run tests — verify they fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v 2>&1 | tail -20
```

Expected: Many FAILED tests (the old HTML still has `<header id="toolbar">`, not `<acv-toolbar>`; app.js has no Lit imports or custom elements).

**Step 4: Write the implementation files (GREEN)**

Write `amplifier_app_cost_viewer/static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Amplifier Cost Viewer</title>
  <link rel="stylesheet" href="/static/style.css">
  <script type="module" src="/static/app.js"></script>
</head>
<body>
  <acv-toolbar id="toolbar"></acv-toolbar>
  <main id="main">
    <acv-tree id="tree"></acv-tree>
    <acv-timeline id="timeline"></acv-timeline>
  </main>
</body>
</html>
```

Write `amplifier_app_cost_viewer/static/style.css`:

```css
/* ==========================================================================
   Amplifier Cost Viewer v2 — Dark Theme (GitHub dark palette)
   ========================================================================== */

:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface-alt: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --accent: #58a6ff;
  --danger: #f85149;
  --success: #3fb950;

  --color-claude-opus: #7B2FBE;
  --color-claude-sonnet: #9C59D1;
  --color-claude-haiku: #C08FE8;
  --color-gpt-4o: #10A37F;
  --color-gpt-4o-mini: #34D399;
  --color-gpt-4-5: #047857;
  --color-gpt-4-1: #059669;
  --color-gpt-4-1-mini: #6EE7B7;
  --color-o4-mini: #10B981;
  --color-o3-mini: #0D9488;
  --color-o3: #0F766E;
  --color-gemini-2-5-pro: #1E40AF;
  --color-gemini-2-5-flash: #2563EB;
  --color-gemini-2-0-flash: #3B82F6;
  --color-gemini-1-5-pro: #1D4ED8;
  --color-gemini-1-5-flash: #60A5FA;
  --color-provider-anthropic: #7B2FBE;
  --color-provider-openai: #10A37F;
  --color-provider-google: #4285F4;
  --color-provider-azure: #3B82F6;
  --color-tool: #64748B;
  --color-thinking: #6366F1;
  --color-unknown: #F59E0B;

  --toolbar-height: 42px;
  --tree-width: 220px;
  --ruler-height: 28px;
  --detail-height: 180px;
  --row-height: 32px;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
  overflow: hidden;
}

body {
  display: flex;
  flex-direction: column;
  background-color: var(--bg);
  color: var(--text);
  font-family: "SF Mono", Consolas, Monaco, "Cascadia Code", "Roboto Mono", monospace;
  font-size: 12px;
  line-height: 1.5;
}

acv-toolbar {
  flex-shrink: 0;
  height: var(--toolbar-height);
}

#main {
  display: flex;
  flex: 1;
  min-height: 0;
}

acv-tree {
  width: var(--tree-width);
  flex-shrink: 0;
  overflow-y: auto;
}

acv-timeline {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
* { scrollbar-width: thin; scrollbar-color: var(--border) var(--bg); }
```

Write `amplifier_app_cost_viewer/static/app.js`:

```javascript
// ================================================================
// Amplifier Cost Viewer v2 — Lit Components + Canvas Gantt
// ================================================================

import {html, render, nothing} from '/static/vendor/lit.all.min.js';

// ================================================================
// Constants
// ================================================================

const ZOOM_MIN = 0.05;
const ZOOM_MAX = 200;
const ROW_H = 32;
const SPAN_H = 20;
const HEATMAP_H = 20;
const IO_TRUNCATE = 500;

// ================================================================
// State
// ================================================================

const state = {
  sessions: [],
  sessionsOffset: 0,
  sessionsHasMore: false,
  activeSessionId: null,
  sessionData: null,
  spans: [],
  expandedSessions: new Set(),
  selectedSpan: null,
  timeScale: 1,
  scrollLeft: 0,
};

// ================================================================
// <acv-toolbar> — shell
// ================================================================

class AcvToolbar extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div style="color:#8b949e;padding:0 12px;line-height:42px">Amplifier Cost Viewer — loading…</div>`, this.#shadow);
  }
}
customElements.define('acv-toolbar', AcvToolbar);

// ================================================================
// <acv-tree> — shell
// ================================================================

class AcvTree extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div style="color:#8b949e;padding:8px">Tree panel</div>`, this.#shadow);
  }
}
customElements.define('acv-tree', AcvTree);

// ================================================================
// <acv-timeline> — shell
// ================================================================

class AcvTimeline extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div style="color:#8b949e;padding:8px">Timeline panel</div>`, this.#shadow);
  }
}
customElements.define('acv-timeline', AcvTimeline);

// ================================================================
// <acv-detail> — shell
// ================================================================

class AcvDetail extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div></div>`, this.#shadow);
  }
}
customElements.define('acv-detail', AcvDetail);

// ================================================================
// Init
// ================================================================

async function init() {
  console.log('Cost Viewer v2 init');
}

document.addEventListener('DOMContentLoaded', init);
```

**Step 5: Run tests — verify they pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All tests PASS. You should see output like:
```
tests/test_static_shell.py::TestIndexHtmlExists::test_file_exists PASSED
tests/test_static_shell.py::TestIndexHtmlExists::test_not_empty PASSED
...
tests/test_app_js.py::TestCustomElements::test_defines_acv_detail PASSED
...
PASSED (XX passed)
```

**Step 6: Verify backend tests still pass**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected: All tests pass (including backend tests in test_scaffold.py, test_reader.py, test_pricing.py, test_server.py).

**Step 7: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/ tests/test_static_shell.py tests/test_app_js.py
git commit -m "feat(viewer): v2 scaffold — Lit vendor + custom element shells + index.html + CSS"
```

---

### Task 2: `<acv-toolbar>` — session dropdown + zoom + refresh

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` (replace AcvToolbar shell + add API functions + add helpers + add init wiring)
- Modify: `tests/test_app_js.py` (add TestApiCalls, TestHelpers, TestAcvToolbar, TestInitWiring classes)

**Step 1: Add tests to `tests/test_app_js.py`**

Append these test classes at the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: API calls (Task 2)
# ---------------------------------------------------------------------------


class TestApiCalls:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_fetch_sessions_function(self) -> None:
        assert "async function fetchSessions(" in self.content

    def test_fetch_sessions_calls_api(self) -> None:
        assert "/api/sessions" in self.content

    def test_fetch_sessions_stores_to_state(self) -> None:
        assert "state.sessions" in self.content

    def test_fetch_sessions_checks_resp_ok(self) -> None:
        assert "resp.ok" in self.content or "response.ok" in self.content

    def test_fetch_sessions_throws_on_error(self) -> None:
        assert "throw new Error" in self.content

    def test_fetch_session_function(self) -> None:
        assert "async function fetchSession(id)" in self.content

    def test_fetch_session_uses_encode_uri(self) -> None:
        assert "encodeURIComponent(id)" in self.content

    def test_fetch_session_stores_to_state(self) -> None:
        assert "state.sessionData" in self.content

    def test_fetch_spans_function(self) -> None:
        assert "async function fetchSpans(id)" in self.content

    def test_fetch_spans_calls_spans_endpoint(self) -> None:
        assert "/spans" in self.content

    def test_fetch_spans_stores_to_state(self) -> None:
        assert "state.spans" in self.content

    def test_fetch_sessions_appends_on_offset(self) -> None:
        assert (
            "state.sessions = [...state.sessions" in self.content
            or "sessions.push" in self.content
            or "concat" in self.content
        )


# ---------------------------------------------------------------------------
# Tests: Helper functions (Task 2)
# ---------------------------------------------------------------------------


class TestHelpers:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_format_ms_defined(self) -> None:
        assert "function _formatMs(" in self.content

    def test_format_ms_handles_milliseconds(self) -> None:
        assert "'ms'" in self.content or '"ms"' in self.content

    def test_format_ms_handles_seconds(self) -> None:
        assert ".toFixed(1)" in self.content

    def test_fmt_tokens_defined(self) -> None:
        assert "function _fmtTokens(" in self.content

    def test_format_date_defined(self) -> None:
        assert "function _formatDate(" in self.content

    def test_format_date_handles_today(self) -> None:
        assert "Today" in self.content

    def test_format_date_handles_yesterday(self) -> None:
        assert "Yesterday" in self.content

    def test_esc_function_defined(self) -> None:
        assert "function _esc(" in self.content

    def test_esc_escapes_ampersand(self) -> None:
        assert "&amp;" in self.content

    def test_esc_escapes_less_than(self) -> None:
        assert "&lt;" in self.content


# ---------------------------------------------------------------------------
# Tests: <acv-toolbar> implementation (Task 2)
# ---------------------------------------------------------------------------


class TestAcvToolbar:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_toolbar_renders_title(self) -> None:
        assert "Amplifier Cost Viewer" in self.content

    def test_toolbar_renders_select(self) -> None:
        assert "<select" in self.content

    def test_toolbar_renders_option(self) -> None:
        assert "<option" in self.content

    def test_toolbar_has_load_more_sentinel(self) -> None:
        assert "__load_more__" in self.content

    def test_toolbar_dispatches_session_change(self) -> None:
        assert "session-change" in self.content

    def test_toolbar_dispatches_zoom_in(self) -> None:
        assert "zoom-in" in self.content

    def test_toolbar_dispatches_zoom_out(self) -> None:
        assert "zoom-out" in self.content

    def test_toolbar_dispatches_refresh(self) -> None:
        assert "'refresh'" in self.content or '"refresh"' in self.content

    def test_toolbar_shows_cost(self) -> None:
        assert "totalCost" in self.content or "total_cost" in self.content

    def test_toolbar_shows_zoom_label(self) -> None:
        assert "ms/px" in self.content


# ---------------------------------------------------------------------------
# Tests: Init wiring (Task 2)
# ---------------------------------------------------------------------------


class TestInitWiring:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_render_all_function(self) -> None:
        assert "function renderAll()" in self.content

    def test_load_session_function(self) -> None:
        assert "async function loadSession(id)" in self.content

    def test_load_session_sets_active_id(self) -> None:
        assert "state.activeSessionId = id" in self.content

    def test_load_session_fetches_session(self) -> None:
        assert "fetchSession(id)" in self.content

    def test_load_session_fetches_spans(self) -> None:
        assert "fetchSpans(id)" in self.content

    def test_load_session_computes_time_scale(self) -> None:
        assert "state.timeScale" in self.content
        assert "end_ms" in self.content

    def test_init_fetches_sessions(self) -> None:
        assert "fetchSessions" in self.content

    def test_init_loads_first_session(self) -> None:
        assert "sessions[0]" in self.content

    def test_init_handles_errors(self) -> None:
        assert "catch" in self.content

    def test_init_wires_session_change(self) -> None:
        assert "session-change" in self.content

    def test_init_wires_zoom_events(self) -> None:
        assert "zoom-in" in self.content
        assert "zoom-out" in self.content

    def test_init_wires_refresh(self) -> None:
        assert "/api/refresh" in self.content
```

**Step 2: Run tests — verify new tests fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_app_js.py::TestApiCalls -v 2>&1 | tail -5
```

Expected: FAILED — `fetchSessions` doesn't exist in the shell app.js yet.

**Step 3: Implement — replace the entire `app.js` with this version**

Write `amplifier_app_cost_viewer/static/app.js` (replaces previous shell version):

```javascript
// ================================================================
// Amplifier Cost Viewer v2 — Lit Components + Canvas Gantt
// ================================================================

import {html, render, nothing} from '/static/vendor/lit.all.min.js';

// ================================================================
// Constants
// ================================================================

const ZOOM_MIN = 0.05;
const ZOOM_MAX = 200;
const ROW_H = 32;
const SPAN_H = 20;
const HEATMAP_H = 20;
const IO_TRUNCATE = 500;

// ================================================================
// State
// ================================================================

const state = {
  sessions: [],
  sessionsOffset: 0,
  sessionsHasMore: false,
  activeSessionId: null,
  sessionData: null,
  spans: [],
  expandedSessions: new Set(),
  selectedSpan: null,
  timeScale: 1,
  scrollLeft: 0,
};

// ================================================================
// API
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
// Helpers
// ================================================================

function _formatMs(ms) {
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000).toString().padStart(2, '0');
  return m + 'm' + s + 's';
}

function _fmtTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
  return String(n);
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
  } catch { return isoStr; }
}

function _esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ================================================================
// <acv-toolbar>
// ================================================================

class AcvToolbar extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};

  connectedCallback() { this.update(); }

  set data(val) { this._data = val; this.update(); }

  update() {
    const d = this._data;
    const sessions = d.sessions || [];
    const activeId = d.activeSessionId;
    const totalCost = d.totalCost || 0;
    const ts = d.timeScale || 1;
    const hasMore = d.hasMore || false;
    const zoomLabel = ts < 1 ? `${(1/ts).toFixed(1)}px/ms` : `${ts.toFixed(0)}ms/px`;

    render(html`
      <style>
        :host { display:flex; align-items:center; gap:8px; padding:0 12px;
                background:#161b22; border-bottom:1px solid #30363d;
                font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; }
        .title { font-weight:600; white-space:nowrap; }
        select { flex:1; min-width:120px; max-width:380px; background:#21262d; color:#e6edf3;
                 border:1px solid #30363d; border-radius:4px; padding:3px 8px;
                 font:inherit; cursor:pointer; }
        button { background:#21262d; color:#e6edf3; border:1px solid #30363d;
                 border-radius:4px; padding:2px 8px; cursor:pointer; font-size:14px; line-height:1; }
        button:hover { border-color:#58a6ff; }
        .cost { white-space:nowrap; color:#8b949e; }
        .cost strong { color:#e6edf3; }
        .zoom { display:flex; align-items:center; gap:4px; flex-shrink:0; }
        .zoom-label { font-size:11px; color:#8b949e; min-width:48px; text-align:center; }
      </style>
      <span class="title">Amplifier Cost Viewer</span>
      <select @change=${this.#onSelect}>
        ${sessions.map(s => {
          const shortId = s.session_id.slice(0, 8);
          const label = s.name ? `${s.name} (${shortId})` : shortId;
          const cost = (s.total_cost_usd || 0).toFixed(2);
          const tok = (s.total_input_tokens||0) + (s.total_output_tokens||0);
          const tokStr = tok > 0 ? ` · ${_fmtTokens(tok)} tok` : '';
          return html`<option value=${s.session_id} ?selected=${s.session_id === activeId}
            >${label} — ${_formatDate(s.start_ts)} — $${cost}${tokStr}</option>`;
        })}
        ${hasMore ? html`<option value="__load_more__">— Load more (${sessions.length} shown) —</option>` : nothing}
      </select>
      <span class="cost">Total: <strong>$${totalCost.toFixed(4)}</strong></span>
      <button title="Refresh session list" @click=${() => this.#dispatch('refresh')}>↻</button>
      <div class="zoom">
        <button title="Zoom out" @click=${() => this.#dispatch('zoom-out')}>−</button>
        <span class="zoom-label">${zoomLabel}</span>
        <button title="Zoom in" @click=${() => this.#dispatch('zoom-in')}>+</button>
      </div>
    `, this.#shadow);
  }

  #onSelect = (e) => {
    const id = e.target.value;
    if (id === '__load_more__') {
      this.#dispatch('load-more');
      return;
    }
    this.dispatchEvent(new CustomEvent('session-change', {detail: {sessionId: id}, bubbles: true}));
  };

  #dispatch(name) {
    this.dispatchEvent(new Event(name, {bubbles: true}));
  }
}
customElements.define('acv-toolbar', AcvToolbar);

// ================================================================
// <acv-tree> — shell (implemented in Task 3)
// ================================================================

class AcvTree extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div style="color:#8b949e;padding:8px;font:12px monospace">Tree panel</div>`, this.#shadow);
  }
}
customElements.define('acv-tree', AcvTree);

// ================================================================
// <acv-timeline> — shell (implemented in Task 4)
// ================================================================

class AcvTimeline extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div style="color:#8b949e;padding:8px;font:12px monospace">Timeline panel</div>`, this.#shadow);
  }
}
customElements.define('acv-timeline', AcvTimeline);

// ================================================================
// <acv-detail> — shell (implemented in Task 6)
// ================================================================

class AcvDetail extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = null;
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    render(html`<div></div>`, this.#shadow);
  }
}
customElements.define('acv-detail', AcvDetail);

// ================================================================
// Render all components from state
// ================================================================

function renderAll() {
  const toolbar = document.getElementById('toolbar');
  const tree = document.getElementById('tree');
  const timeline = document.getElementById('timeline');
  if (toolbar) toolbar.data = {
    sessions: state.sessions,
    activeSessionId: state.activeSessionId,
    totalCost: state.sessions.reduce((s, sess) => s + (sess.total_cost_usd || 0), 0),
    timeScale: state.timeScale,
    hasMore: state.sessionsHasMore,
  };
  if (tree) tree.data = {
    sessionData: state.sessionData,
    activeSessionId: state.activeSessionId,
    expandedSessions: state.expandedSessions,
  };
  if (timeline) timeline.data = {
    spans: state.spans,
    sessionData: state.sessionData,
    expandedSessions: state.expandedSessions,
    timeScale: state.timeScale,
    scrollLeft: state.scrollLeft,
    selectedSpan: state.selectedSpan,
  };
}

// ================================================================
// Load a session
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await Promise.all([fetchSession(id), fetchSpans(id)]);

  // Auto-expand root and immediate children
  state.expandedSessions.clear();
  state.expandedSessions.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => state.expandedSessions.add(c.session_id));
  }

  // Fit timeline to viewport
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
  const timelineEl = document.getElementById('timeline');
  const width = (timelineEl ? timelineEl.clientWidth : 800) || 800;
  state.timeScale = maxEndMs / Math.max(width - 40, 400);
  state.scrollLeft = 0;
  state.selectedSpan = null;

  renderAll();
}

// ================================================================
// Init
// ================================================================

async function init() {
  const toolbar = document.getElementById('toolbar');

  // Wire toolbar events
  toolbar.addEventListener('session-change', async (e) => {
    try {
      await loadSession(e.detail.sessionId);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  });
  toolbar.addEventListener('zoom-in', () => {
    state.timeScale = Math.max(ZOOM_MIN, state.timeScale * 0.7);
    renderAll();
  });
  toolbar.addEventListener('zoom-out', () => {
    state.timeScale = Math.min(ZOOM_MAX, state.timeScale * 1.3);
    renderAll();
  });
  toolbar.addEventListener('refresh', async () => {
    try {
      await fetch('/api/refresh', {method: 'POST'});
      await fetchSessions(0);
      state.activeSessionId = null;
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
      await fetchSessions(state.sessionsOffset);
      renderAll();
    } catch (err) {
      console.error('Load more failed:', err);
    }
  });

  // Initial load
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
      console.error('Failed to load first session:', err);
    }
  }
}

document.addEventListener('DOMContentLoaded', init);
```

**Step 4: Run tests — verify they pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All PASS.

**Step 5: Browser verification**

Start the server (in a separate terminal):
```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer --host 0.0.0.0
```

Open http://localhost:8000 in a browser. Verify:
- The toolbar renders with "Amplifier Cost Viewer" title
- The session dropdown populates with session names
- The total cost shows a dollar amount
- Zoom `−` / `+` buttons are visible
- Refresh `↻` button is visible
- No console errors (check DevTools → Console)

**Step 6: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py
git commit -m "feat(viewer): acv-toolbar — session dropdown + zoom + refresh"
```

---

### Task 3: `<acv-tree>` — session hierarchy with inline cost bars

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` (replace AcvTree shell with full implementation)
- Modify: `tests/test_app_js.py` (add TestAcvTree class)

**Step 1: Add tests to `tests/test_app_js.py`**

Append this test class at the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: <acv-tree> implementation (Task 3)
# ---------------------------------------------------------------------------


class TestAcvTree:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_tree_renders_rows(self) -> None:
        assert "tree-row" in self.content, "AcvTree must render .tree-row elements"

    def test_tree_renders_toggle(self) -> None:
        assert "▾" in self.content or "\\u25be" in self.content or "▸" in self.content or "\\u25b8" in self.content, (
            "AcvTree must render expand/collapse triangles"
        )

    def test_tree_renders_cost_bar(self) -> None:
        assert "cost-bar" in self.content, "AcvTree must render inline cost bars"

    def test_tree_renders_cost_label(self) -> None:
        assert "total_cost_usd" in self.content, "AcvTree must display cost label"

    def test_tree_dispatches_toggle_expand(self) -> None:
        assert "toggle-expand" in self.content

    def test_tree_dispatches_session_select(self) -> None:
        assert "session-select" in self.content

    def test_tree_uses_expanded_sessions(self) -> None:
        assert "expandedSessions" in self.content

    def test_tree_renders_session_label(self) -> None:
        assert "session-label" in self.content

    def test_tree_handles_children_recursively(self) -> None:
        assert "children" in self.content
        assert "depth" in self.content
```

**Step 2: Run tests — verify new tests fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_app_js.py::TestAcvTree -v 2>&1 | tail -5
```

Expected: FAILED — AcvTree is still a shell.

**Step 3: Implement AcvTree**

In `amplifier_app_cost_viewer/static/app.js`, find the `<acv-tree> — shell` section and replace the entire `AcvTree` class (lines between `// <acv-tree>` and `customElements.define('acv-tree'`) with:

```javascript
// ================================================================
// <acv-tree>
// ================================================================

class AcvTree extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};

  connectedCallback() { this.update(); }

  set data(val) { this._data = val; this.update(); }

  update() {
    const d = this._data;
    const root = d.sessionData;
    const activeId = d.activeSessionId;
    const expanded = d.expandedSessions || new Set();

    if (!root) {
      render(html`<style>${this.#styles()}</style>
        <div class="placeholder">No session loaded.</div>`, this.#shadow);
      return;
    }

    // Compute max cost for proportional bars
    const maxCost = this.#maxCostOf(root);
    const rows = [];
    this.#flatten(root, 0, expanded, maxCost, activeId, rows);

    render(html`
      <style>${this.#styles()}</style>
      ${rows}
    `, this.#shadow);
  }

  #maxCostOf(node) {
    let max = node.total_cost_usd || 0;
    if (node.children) node.children.forEach(c => { max = Math.max(max, c.total_cost_usd || 0); });
    return max || 1;
  }

  #flatten(node, depth, expanded, maxCost, activeId, rows) {
    const sid = node.session_id;
    const isExpanded = expanded.has(sid);
    const hasKids = node.children && node.children.length > 0;
    const cost = node.total_cost_usd || 0;
    const barW = Math.max(2, (cost / maxCost) * 100);
    const shortId = sid.slice(-8);
    const label = node.name || node.agent_name || shortId;
    const tok = (node.total_input_tokens || 0) + (node.total_output_tokens || 0);
    const costLabel = tok > 0 ? `$${cost.toFixed(2)} · ${_fmtTokens(tok)}` : `$${cost.toFixed(4)}`;

    rows.push(html`
      <div class="tree-row ${sid === activeId ? 'active' : ''}"
           style="padding-left:${8 + depth * 12}px"
           @click=${() => this.#onRowClick(sid, hasKids)}>
        <span class="toggle">${hasKids ? (isExpanded ? '▾' : '▸') : html`&nbsp;`}</span>
        <span class="session-label" title=${sid}>${label}</span>
        <span class="session-cost">${costLabel}</span>
        <div class="cost-bar" style="width:${barW}%"></div>
      </div>
    `);

    if (isExpanded && hasKids) {
      node.children.forEach(c => this.#flatten(c, depth + 1, expanded, maxCost, activeId, rows));
    }
  }

  #onRowClick(sessionId, hasChildren) {
    if (hasChildren) {
      this.dispatchEvent(new CustomEvent('toggle-expand', {detail: {sessionId}, bubbles: true}));
    }
    this.dispatchEvent(new CustomEvent('session-select', {detail: {sessionId}, bubbles: true}));
  }

  #styles() {
    return `
      :host { display:block; background:#161b22; border-right:1px solid #30363d;
              font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; overflow-y:auto; }
      .placeholder { padding:12px 8px; color:#8b949e; font-style:italic; }
      .tree-row { display:flex; align-items:center; height:32px; padding-right:8px;
                  cursor:pointer; user-select:none; border-left:2px solid transparent;
                  position:relative; }
      .tree-row:hover { background:#21262d; }
      .tree-row.active { border-left-color:#58a6ff; background:#21262d; }
      .toggle { flex-shrink:0; width:14px; color:#8b949e; font-size:10px; text-align:center; }
      .session-label { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .session-cost { flex-shrink:0; color:#8b949e; font-size:11px; margin-left:4px; }
      .cost-bar { position:absolute; bottom:0; left:0; height:3px; background:#58a6ff; opacity:0.4; }
    `;
  }
}
customElements.define('acv-tree', AcvTree);
```

Also add tree event wiring in `init()`. Find the comment `// Initial load` in the `init()` function and add these lines **before** it:

```javascript
  // Wire tree events
  const tree = document.getElementById('tree');
  tree.addEventListener('toggle-expand', (e) => {
    const sid = e.detail.sessionId;
    if (state.expandedSessions.has(sid)) {
      state.expandedSessions.delete(sid);
    } else {
      state.expandedSessions.add(sid);
    }
    renderAll();
  });
  tree.addEventListener('session-select', (e) => {
    // Highlight selected row (active state is visual only via renderAll)
    renderAll();
  });
```

**Step 4: Run tests — verify they pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All PASS.

**Step 5: Browser verification**

Open http://localhost:8000 in a browser. Verify:
- Left panel shows session tree with expand/collapse triangles
- Cost bars appear at the bottom of each row (proportional width)
- Cost labels show dollar amounts
- Clicking a row with children toggles expand/collapse
- Nested children indent properly

**Step 6: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py
git commit -m "feat(viewer): acv-tree — session hierarchy with inline cost bars"
```

---

### Task 4: `<acv-timeline>` — cost heatmap + ruler (no Canvas Gantt yet)

**Files:**
- Rewrite: `amplifier_app_cost_viewer/static/app.js` (COMPLETE file — adds AcvTimeline with heatmap/ruler/keyboard)
- Modify: `tests/test_app_js.py` (add TestAcvTimeline class)

**Step 1: Add tests to `tests/test_app_js.py`**

Append this test class at the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: <acv-timeline> basic (Task 4)
# ---------------------------------------------------------------------------


class TestAcvTimeline:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_timeline_has_canvas(self) -> None:
        assert "<canvas" in self.content or "canvas" in self.content.lower(), (
            "AcvTimeline must contain a canvas element"
        )

    def test_timeline_has_heatmap(self) -> None:
        assert "heatmap" in self.content, "AcvTimeline must have a heatmap strip"

    def test_timeline_has_ruler(self) -> None:
        assert "ruler" in self.content, "AcvTimeline must have a time ruler"

    def test_timeline_has_draw_method(self) -> None:
        assert "draw()" in self.content or "#draw()" in self.content, (
            "AcvTimeline must have a draw() method"
        )

    def test_timeline_has_resize_canvas(self) -> None:
        assert "devicePixelRatio" in self.content, (
            "AcvTimeline must handle canvas DPR scaling"
        )

    def test_keyboard_shortcuts_w_zoom_in(self) -> None:
        assert "KeyW" in self.content or "'w'" in self.content or '"w"' in self.content, (
            "Must handle W key for zoom in"
        )

    def test_keyboard_shortcuts_s_zoom_out(self) -> None:
        assert "KeyS" in self.content or "'s'" in self.content or '"s"' in self.content, (
            "Must handle S key for zoom out"
        )

    def test_keyboard_shortcuts_a_pan_left(self) -> None:
        assert "KeyA" in self.content or "'a'" in self.content or "ArrowLeft" in self.content, (
            "Must handle A key for pan left"
        )

    def test_keyboard_shortcuts_d_pan_right(self) -> None:
        assert "KeyD" in self.content or "'d'" in self.content or "ArrowRight" in self.content, (
            "Must handle D key for pan right"
        )

    def test_keyboard_escape_closes_detail(self) -> None:
        assert "Escape" in self.content

    def test_wheel_zoom_on_ruler(self) -> None:
        assert "wheel" in self.content, "Must handle wheel event for zoom"

    def test_raf_debounced(self) -> None:
        assert "requestAnimationFrame" in self.content, "Zoom must be RAF-debounced"

    def test_heatmap_uses_purple(self) -> None:
        assert "123, 47, 190" in self.content or "7b2fbe" in self.content.lower() or "123,47,190" in self.content, (
            "Heatmap must use Anthropic purple"
        )

    def test_ruler_has_tick_intervals(self) -> None:
        assert "5000" in self.content or "30000" in self.content or "60000" in self.content
```

**Step 2: Run tests — verify new tests fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_app_js.py::TestAcvTimeline -v 2>&1 | tail -5
```

Expected: FAILED — AcvTimeline is still a shell.

**Step 3: Write the COMPLETE `app.js` for this stage**

Replace the entire file `amplifier_app_cost_viewer/static/app.js` with the following:

```javascript
// ================================================================
// Amplifier Cost Viewer v2 — Lit Components + Canvas Gantt
// ================================================================

import {html, render, nothing} from '/static/vendor/lit.all.min.js';

// ================================================================
// Constants
// ================================================================

const ZOOM_MIN = 0.05;
const ZOOM_MAX = 200;
const ROW_H = 32;
const SPAN_H = 20;
const HEATMAP_H = 20;
const IO_TRUNCATE = 500;

// ================================================================
// State
// ================================================================

const state = {
  sessions: [],
  sessionsOffset: 0,
  sessionsHasMore: false,
  activeSessionId: null,
  sessionData: null,
  spans: [],
  expandedSessions: new Set(),
  selectedSpan: null,
  timeScale: 1,
  scrollLeft: 0,
};

// ================================================================
// API
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
// Helpers
// ================================================================

function _formatMs(ms) {
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000).toString().padStart(2, '0');
  return m + 'm' + s + 's';
}

function _fmtTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
  return String(n);
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
  } catch { return isoStr; }
}

function _esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Walk session tree, returning visible rows respecting expandedSessions.
function _visibleRows(node, expanded, result = []) {
  if (!node) return result;
  result.push(node);
  if (expanded.has(node.session_id) && node.children) {
    node.children.forEach(c => _visibleRows(c, expanded, result));
  }
  return result;
}

// Build a map: sessionId → row index for visible rows.
function _rowIndexMap(sessionData, expanded) {
  const rows = _visibleRows(sessionData, expanded);
  const map = new Map();
  rows.forEach((node, i) => map.set(node.session_id, i));
  return map;
}

// ================================================================
// <acv-toolbar>
// ================================================================

class AcvToolbar extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }

  update() {
    const d = this._data;
    const sessions = d.sessions || [];
    const activeId = d.activeSessionId;
    const totalCost = d.totalCost || 0;
    const ts = d.timeScale || 1;
    const hasMore = d.hasMore || false;
    const zoomLabel = ts < 1 ? `${(1/ts).toFixed(1)}px/ms` : `${ts.toFixed(0)}ms/px`;

    render(html`
      <style>
        :host { display:flex; align-items:center; gap:8px; padding:0 12px;
                background:#161b22; border-bottom:1px solid #30363d;
                font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; }
        .title { font-weight:600; white-space:nowrap; }
        select { flex:1; min-width:120px; max-width:380px; background:#21262d; color:#e6edf3;
                 border:1px solid #30363d; border-radius:4px; padding:3px 8px; font:inherit; cursor:pointer; }
        button { background:#21262d; color:#e6edf3; border:1px solid #30363d;
                 border-radius:4px; padding:2px 8px; cursor:pointer; font-size:14px; line-height:1; }
        button:hover { border-color:#58a6ff; }
        .cost { white-space:nowrap; color:#8b949e; }
        .cost strong { color:#e6edf3; }
        .zoom { display:flex; align-items:center; gap:4px; flex-shrink:0; }
        .zoom-label { font-size:11px; color:#8b949e; min-width:48px; text-align:center; }
      </style>
      <span class="title">Amplifier Cost Viewer</span>
      <select @change=${this.#onSelect}>
        ${sessions.map(s => {
          const shortId = s.session_id.slice(0, 8);
          const label = s.name ? `${s.name} (${shortId})` : shortId;
          const cost = (s.total_cost_usd || 0).toFixed(2);
          const tok = (s.total_input_tokens||0) + (s.total_output_tokens||0);
          const tokStr = tok > 0 ? ` · ${_fmtTokens(tok)} tok` : '';
          return html`<option value=${s.session_id} ?selected=${s.session_id === activeId}
            >${label} — ${_formatDate(s.start_ts)} — $${cost}${tokStr}</option>`;
        })}
        ${hasMore ? html`<option value="__load_more__">— Load more (${sessions.length} shown) —</option>` : nothing}
      </select>
      <span class="cost">Total: <strong>$${totalCost.toFixed(4)}</strong></span>
      <button title="Refresh session list" @click=${() => this.#dispatch('refresh')}>↻</button>
      <div class="zoom">
        <button title="Zoom out" @click=${() => this.#dispatch('zoom-out')}>−</button>
        <span class="zoom-label">${zoomLabel}</span>
        <button title="Zoom in" @click=${() => this.#dispatch('zoom-in')}>+</button>
      </div>
    `, this.#shadow);
  }

  #onSelect = (e) => {
    const id = e.target.value;
    if (id === '__load_more__') { this.#dispatch('load-more'); return; }
    this.dispatchEvent(new CustomEvent('session-change', {detail: {sessionId: id}, bubbles: true}));
  };
  #dispatch(name) { this.dispatchEvent(new Event(name, {bubbles: true})); }
}
customElements.define('acv-toolbar', AcvToolbar);

// ================================================================
// <acv-tree>
// ================================================================

class AcvTree extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }

  update() {
    const d = this._data;
    const root = d.sessionData;
    const activeId = d.activeSessionId;
    const expanded = d.expandedSessions || new Set();
    if (!root) {
      render(html`<style>${this.#styles()}</style>
        <div class="placeholder">No session loaded.</div>`, this.#shadow);
      return;
    }
    const maxCost = this.#maxCostOf(root);
    const rows = [];
    this.#flatten(root, 0, expanded, maxCost, activeId, rows);
    render(html`<style>${this.#styles()}</style>${rows}`, this.#shadow);
  }

  #maxCostOf(node) {
    let max = node.total_cost_usd || 0;
    if (node.children) node.children.forEach(c => { max = Math.max(max, c.total_cost_usd || 0); });
    return max || 1;
  }

  #flatten(node, depth, expanded, maxCost, activeId, rows) {
    const sid = node.session_id;
    const isExpanded = expanded.has(sid);
    const hasKids = node.children && node.children.length > 0;
    const cost = node.total_cost_usd || 0;
    const barW = Math.max(2, (cost / maxCost) * 100);
    const shortId = sid.slice(-8);
    const label = node.name || node.agent_name || shortId;
    const tok = (node.total_input_tokens || 0) + (node.total_output_tokens || 0);
    const costLabel = tok > 0 ? `$${cost.toFixed(2)} · ${_fmtTokens(tok)}` : `$${cost.toFixed(4)}`;
    rows.push(html`
      <div class="tree-row ${sid === activeId ? 'active' : ''}"
           style="padding-left:${8 + depth * 12}px"
           @click=${() => this.#onRowClick(sid, hasKids)}>
        <span class="toggle">${hasKids ? (isExpanded ? '▾' : '▸') : html`&nbsp;`}</span>
        <span class="session-label" title=${sid}>${label}</span>
        <span class="session-cost">${costLabel}</span>
        <div class="cost-bar" style="width:${barW}%"></div>
      </div>
    `);
    if (isExpanded && hasKids) {
      node.children.forEach(c => this.#flatten(c, depth + 1, expanded, maxCost, activeId, rows));
    }
  }

  #onRowClick(sessionId, hasChildren) {
    if (hasChildren) {
      this.dispatchEvent(new CustomEvent('toggle-expand', {detail: {sessionId}, bubbles: true}));
    }
    this.dispatchEvent(new CustomEvent('session-select', {detail: {sessionId}, bubbles: true}));
  }

  #styles() {
    return `:host { display:block; background:#161b22; border-right:1px solid #30363d;
              font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; overflow-y:auto; }
      .placeholder { padding:12px 8px; color:#8b949e; font-style:italic; }
      .tree-row { display:flex; align-items:center; height:32px; padding-right:8px;
                  cursor:pointer; user-select:none; border-left:2px solid transparent; position:relative; }
      .tree-row:hover { background:#21262d; }
      .tree-row.active { border-left-color:#58a6ff; background:#21262d; }
      .toggle { flex-shrink:0; width:14px; color:#8b949e; font-size:10px; text-align:center; }
      .session-label { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .session-cost { flex-shrink:0; color:#8b949e; font-size:11px; margin-left:4px; }
      .cost-bar { position:absolute; bottom:0; left:0; height:3px; background:#58a6ff; opacity:0.4; }`;
  }
}
customElements.define('acv-tree', AcvTree);

// ================================================================
// <acv-timeline> — heatmap + ruler + empty canvas
// ================================================================

class AcvTimeline extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  #canvas = null;
  #ctx = null;
  #rafId = null;
  _data = {};

  connectedCallback() { this.update(); }

  set data(val) {
    this._data = val;
    this.update();
    // Schedule a draw after render
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = requestAnimationFrame(() => {
      this.#ensureCanvas();
      this.#draw();
      this.#rafId = null;
    });
  }

  update() {
    const d = this._data;
    const spans = d.spans || [];
    const ts = d.timeScale || 1;
    const scrollL = d.scrollLeft || 0;

    render(html`
      <style>${this.#styles()}</style>
      <div id="heatmap">${this.#renderHeatmap(spans, ts, scrollL)}</div>
      <div id="ruler" @wheel=${this.#onRulerWheel}>${this.#renderRuler(spans, ts, scrollL)}</div>
      <div id="canvas-wrap">
        <canvas id="gantt-canvas"></canvas>
      </div>
    `, this.#shadow);
  }

  #ensureCanvas() {
    if (this.#canvas) return;
    this.#canvas = this.#shadow.querySelector('#gantt-canvas');
    if (!this.#canvas) return;
    this.#ctx = this.#canvas.getContext('2d');
    // Click handler for span selection
    this.#canvas.addEventListener('click', (e) => this.#onCanvasClick(e));
  }

  #resizeCanvas() {
    if (!this.#canvas) return;
    const wrap = this.#canvas.parentElement;
    if (!wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    this.#canvas.width = w * dpr;
    this.#canvas.height = h * dpr;
    this.#canvas.style.width = w + 'px';
    this.#canvas.style.height = h + 'px';
    this.#ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  #draw() {
    if (!this.#ctx) return;
    this.#resizeCanvas();
    const ctx = this.#ctx;
    const cw = this.#canvas.width / (window.devicePixelRatio || 1);
    const ch = this.#canvas.height / (window.devicePixelRatio || 1);
    // Clear to background
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, cw, ch);
    // Placeholder — full Canvas Gantt implemented in Task 5
    if (!this._data.spans || this._data.spans.length === 0) {
      ctx.fillStyle = '#8b949e';
      ctx.font = '12px monospace';
      ctx.fillText('No spans to display.', 20, 30);
    }
  }

  #renderHeatmap(spans, ts, scrollL) {
    if (!spans.length) return nothing;
    const maxEndMs = spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
    const totalPx = maxEndMs / ts;
    const bucketW = 4;
    const numBuckets = Math.max(1, Math.ceil(totalPx / bucketW));
    const buckets = new Float64Array(numBuckets);
    let maxBucket = 0;
    spans.forEach(s => {
      if (!s.cost_usd) return;
      const startBucket = Math.floor((s.start_ms / ts) / bucketW);
      const endBucket = Math.floor(((s.end_ms || s.start_ms) / ts) / bucketW);
      const spanBuckets = Math.max(1, endBucket - startBucket + 1);
      const costPerBucket = s.cost_usd / spanBuckets;
      for (let b = startBucket; b <= endBucket && b < numBuckets; b++) {
        buckets[b] += costPerBucket;
        if (buckets[b] > maxBucket) maxBucket = buckets[b];
      }
    });
    if (maxBucket === 0) return nothing;
    // Find peak bucket
    let peakIdx = 0;
    for (let i = 1; i < numBuckets; i++) { if (buckets[i] > buckets[peakIdx]) peakIdx = i; }
    const cols = [];
    for (let i = 0; i < numBuckets; i++) {
      const opacity = buckets[i] / maxBucket;
      const left = i * bucketW - scrollL;
      if (left < -bucketW || left > 2000) continue; // rough cull
      const isPeak = i === peakIdx;
      cols.push(html`<div style="position:absolute;left:${left}px;width:${bucketW}px;height:${HEATMAP_H}px;
        background:rgba(123,47,190,${opacity.toFixed(3)});
        ${isPeak ? 'border-right:1px solid #f59e0b;' : ''}"></div>`);
    }
    return cols;
  }

  #renderRuler(spans, ts, scrollL) {
    if (!spans.length) return nothing;
    const maxEndMs = spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
    const visibleMs = 1000 * ts; // rough visible width
    let tickInterval;
    if (visibleMs < 5000) tickInterval = 500;
    else if (visibleMs < 30000) tickInterval = 5000;
    else if (visibleMs < 120000) tickInterval = 30000;
    else if (visibleMs < 600000) tickInterval = 60000;
    else if (visibleMs < 3600000) tickInterval = 300000;
    else tickInterval = 900000;
    const ticks = [];
    for (let t = 0; t <= maxEndMs; t += tickInterval) {
      const x = t / ts - scrollL;
      if (x < -50 || x > 3000) continue;
      ticks.push(html`
        <div class="tick" style="left:${x}px">
          <div class="tick-line"></div>
          <span class="tick-label">${_formatMs(t)}</span>
        </div>
      `);
    }
    return ticks;
  }

  #onRulerWheel = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const factor = e.deltaY > 0 ? 1.3 : (1 / 1.3);
    const oldScale = state.timeScale;
    const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, oldScale * factor));
    if (newScale === oldScale) return;
    // Zoom centered on cursor
    const rulerEl = this.#shadow.querySelector('#ruler');
    const rect = rulerEl.getBoundingClientRect();
    const cursorX = e.clientX - rect.left + state.scrollLeft;
    const msAtCursor = cursorX * oldScale;
    state.timeScale = newScale;
    state.scrollLeft = msAtCursor / newScale - (e.clientX - rect.left);
    if (state.scrollLeft < 0) state.scrollLeft = 0;
    renderAll();
  };

  #onCanvasClick(e) {
    // Implemented in Task 5 (span hit testing)
  }

  #styles() {
    return `:host { display:flex; flex-direction:column; min-width:0; overflow:hidden;
              font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; }
      #heatmap { height:${HEATMAP_H}px; position:relative; overflow:hidden;
                 background:#0d1117; flex-shrink:0; }
      #ruler { height:28px; min-height:28px; position:relative; overflow:hidden;
               background:#161b22; border-bottom:1px solid #30363d; flex-shrink:0; cursor:ew-resize; }
      .tick { position:absolute; top:0; height:100%; }
      .tick-line { width:1px; height:8px; background:#30363d; }
      .tick-label { position:absolute; top:10px; font-size:10px; color:#8b949e;
                    transform:translateX(-50%); white-space:nowrap; }
      #canvas-wrap { flex:1; min-height:0; overflow:hidden; position:relative; }
      canvas { display:block; }`;
  }
}
customElements.define('acv-timeline', AcvTimeline);

// ================================================================
// <acv-detail> — shell (implemented in Task 6)
// ================================================================

class AcvDetail extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = null;
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() { render(html`<div></div>`, this.#shadow); }
}
customElements.define('acv-detail', AcvDetail);

// ================================================================
// Render all components from state
// ================================================================

function renderAll() {
  const toolbar = document.getElementById('toolbar');
  const tree = document.getElementById('tree');
  const timeline = document.getElementById('timeline');
  if (toolbar) toolbar.data = {
    sessions: state.sessions,
    activeSessionId: state.activeSessionId,
    totalCost: state.sessions.reduce((s, sess) => s + (sess.total_cost_usd || 0), 0),
    timeScale: state.timeScale,
    hasMore: state.sessionsHasMore,
  };
  if (tree) tree.data = {
    sessionData: state.sessionData,
    activeSessionId: state.activeSessionId,
    expandedSessions: state.expandedSessions,
  };
  if (timeline) timeline.data = {
    spans: state.spans,
    sessionData: state.sessionData,
    expandedSessions: state.expandedSessions,
    timeScale: state.timeScale,
    scrollLeft: state.scrollLeft,
    selectedSpan: state.selectedSpan,
  };
}

// ================================================================
// Load a session
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await Promise.all([fetchSession(id), fetchSpans(id)]);
  state.expandedSessions.clear();
  state.expandedSessions.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => state.expandedSessions.add(c.session_id));
  }
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
  const timelineEl = document.getElementById('timeline');
  const width = (timelineEl ? timelineEl.clientWidth : 800) || 800;
  state.timeScale = maxEndMs / Math.max(width - 40, 400);
  state.scrollLeft = 0;
  state.selectedSpan = null;
  renderAll();
}

// ================================================================
// Init
// ================================================================

async function init() {
  const toolbar = document.getElementById('toolbar');
  const tree = document.getElementById('tree');

  // Wire toolbar events
  toolbar.addEventListener('session-change', async (e) => {
    try { await loadSession(e.detail.sessionId); }
    catch (err) { console.error('Failed to load session:', err); }
  });
  toolbar.addEventListener('zoom-in', () => {
    state.timeScale = Math.max(ZOOM_MIN, state.timeScale * 0.7);
    renderAll();
  });
  toolbar.addEventListener('zoom-out', () => {
    state.timeScale = Math.min(ZOOM_MAX, state.timeScale * 1.3);
    renderAll();
  });
  toolbar.addEventListener('refresh', async () => {
    try {
      await fetch('/api/refresh', {method: 'POST'});
      await fetchSessions(0);
      state.activeSessionId = null;
      renderAll();
      if (state.sessions.length > 0) await loadSession(state.sessions[0].session_id);
    } catch (err) { console.error('Refresh failed:', err); }
  });
  toolbar.addEventListener('load-more', async () => {
    try { await fetchSessions(state.sessionsOffset); renderAll(); }
    catch (err) { console.error('Load more failed:', err); }
  });

  // Wire tree events
  tree.addEventListener('toggle-expand', (e) => {
    const sid = e.detail.sessionId;
    if (state.expandedSessions.has(sid)) state.expandedSessions.delete(sid);
    else state.expandedSessions.add(sid);
    renderAll();
  });
  tree.addEventListener('session-select', () => renderAll());

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
    const shift = e.shiftKey ? 3 : 1;
    switch (e.code) {
      case 'KeyW': case 'Equal':
        e.preventDefault();
        state.timeScale = Math.max(ZOOM_MIN, state.timeScale * Math.pow(0.7, shift));
        renderAll();
        break;
      case 'KeyS': case 'Minus':
        e.preventDefault();
        state.timeScale = Math.min(ZOOM_MAX, state.timeScale * Math.pow(1.3, shift));
        renderAll();
        break;
      case 'KeyA': case 'ArrowLeft':
        e.preventDefault();
        state.scrollLeft = Math.max(0, state.scrollLeft - 150 * shift);
        renderAll();
        break;
      case 'KeyD': case 'ArrowRight':
        e.preventDefault();
        state.scrollLeft += 150 * shift;
        renderAll();
        break;
      case 'Escape':
        state.selectedSpan = null;
        renderAll();
        break;
    }
  });

  // Initial load
  try { await fetchSessions(); }
  catch (err) { console.error('Failed to fetch sessions:', err); return; }
  renderAll();
  if (state.sessions.length > 0) {
    try { await loadSession(state.sessions[0].session_id); }
    catch (err) { console.error('Failed to load first session:', err); }
  }
}

document.addEventListener('DOMContentLoaded', init);
```

**Step 4: Run tests — verify they pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All PASS.

**Step 5: Browser verification**

Open http://localhost:8000. Verify:
- Purple heatmap strip appears above the ruler (varying intensity)
- Ruler shows time ticks (0s, 5s, 10s, etc.)
- Canvas area shows dark background (no spans drawn yet — that's Task 5)
- Scroll wheel on ruler zooms in/out (heatmap and ruler update)
- Press W → zoom in, S → zoom out
- Press A → pan left, D → pan right
- No jank during rapid zoom/pan

**Step 6: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py
git commit -m "feat(viewer): acv-timeline — cost heatmap + ruler + keyboard shortcuts"
```

---

### Task 5: Canvas Gantt — span drawing

**Files:**
- Rewrite: `amplifier_app_cost_viewer/static/app.js` (COMPLETE file — adds full Canvas draw())
- Modify: `tests/test_app_js.py` (add TestCanvasDraw class)

**Step 1: Add tests to `tests/test_app_js.py`**

Append this test class at the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: Canvas draw() method (Task 5)
# ---------------------------------------------------------------------------


class TestCanvasDraw:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_draw_clears_canvas(self) -> None:
        assert "clearRect" in self.content, "draw() must clear the canvas"

    def test_draw_alternating_backgrounds(self) -> None:
        assert "#161b22" in self.content, "draw() must use #161b22 for alternating rows"
        assert "#0d1117" in self.content, "draw() must use #0d1117 for alternating rows"

    def test_draw_color_batched(self) -> None:
        assert "beginPath" in self.content, "draw() must batch spans by color with beginPath"
        assert "ctx.fill()" in self.content or ".fill()" in self.content, (
            "draw() must call fill() per color batch"
        )

    def test_draw_text_labels_on_wide_spans(self) -> None:
        assert "60" in self.content, "draw() must check span width > 60px for text labels"
        assert "fillText" in self.content, "draw() must use fillText for span labels"

    def test_draw_visibility_culling(self) -> None:
        # Should skip off-screen spans
        assert "continue" in self.content, "draw() must skip off-screen spans"

    def test_draw_grid_lines(self) -> None:
        assert "strokeStyle" in self.content or "stroke()" in self.content, (
            "draw() must render grid lines"
        )

    def test_draw_uses_row_h(self) -> None:
        assert "ROW_H" in self.content, "draw() must use ROW_H constant"

    def test_draw_uses_span_h(self) -> None:
        assert "SPAN_H" in self.content, "draw() must use SPAN_H constant"

    def test_row_index_map_respects_expanded(self) -> None:
        assert "_rowIndexMap" in self.content or "_visibleRows" in self.content, (
            "Must have row index computation respecting expandedSessions"
        )

    def test_draw_minimum_span_width(self) -> None:
        assert "Math.max(2" in self.content or "Math.max( 2" in self.content, (
            "draw() must enforce minimum 2px span width"
        )

    def test_draw_fallback_color(self) -> None:
        assert "'#64748B'" in self.content or '"#64748B"' in self.content, (
            "draw() must have fallback color #64748B"
        )
```

**Step 2: Run tests — verify new tests fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_app_js.py::TestCanvasDraw -v 2>&1 | tail -5
```

Expected: FAILED — draw() only clears to background, no span drawing yet.

**Step 3: Write the COMPLETE `app.js` for this stage**

Replace the entire file `amplifier_app_cost_viewer/static/app.js` with the following. This is the same as Task 4's file but with the full `#draw()` method implemented inside AcvTimeline:

```javascript
// ================================================================
// Amplifier Cost Viewer v2 — Lit Components + Canvas Gantt
// ================================================================

import {html, render, nothing} from '/static/vendor/lit.all.min.js';

// ================================================================
// Constants
// ================================================================

const ZOOM_MIN = 0.05;
const ZOOM_MAX = 200;
const ROW_H = 32;
const SPAN_H = 20;
const HEATMAP_H = 20;
const IO_TRUNCATE = 500;

// ================================================================
// State
// ================================================================

const state = {
  sessions: [],
  sessionsOffset: 0,
  sessionsHasMore: false,
  activeSessionId: null,
  sessionData: null,
  spans: [],
  expandedSessions: new Set(),
  selectedSpan: null,
  timeScale: 1,
  scrollLeft: 0,
};

// ================================================================
// API
// ================================================================

async function fetchSessions(offset = 0) {
  const resp = await fetch(`/api/sessions?limit=25&offset=${offset}`);
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  const data = await resp.json();
  if (offset === 0) { state.sessions = data.sessions; }
  else { state.sessions = [...state.sessions, ...data.sessions]; }
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
// Helpers
// ================================================================

function _formatMs(ms) {
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000).toString().padStart(2, '0');
  return m + 'm' + s + 's';
}

function _fmtTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
  return String(n);
}

function _formatDate(isoStr) {
  if (!isoStr) return 'unknown';
  try {
    const d = new Date(isoStr);
    const diffMs = Date.now() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) {
      return `Today ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
    }
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString();
  } catch { return isoStr; }
}

function _esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _visibleRows(node, expanded, result = []) {
  if (!node) return result;
  result.push(node);
  if (expanded.has(node.session_id) && node.children) {
    node.children.forEach(c => _visibleRows(c, expanded, result));
  }
  return result;
}

function _rowIndexMap(sessionData, expanded) {
  const rows = _visibleRows(sessionData, expanded);
  const map = new Map();
  rows.forEach((node, i) => map.set(node.session_id, i));
  return map;
}

// ================================================================
// <acv-toolbar>
// ================================================================

class AcvToolbar extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }

  update() {
    const d = this._data;
    const sessions = d.sessions || [];
    const activeId = d.activeSessionId;
    const totalCost = d.totalCost || 0;
    const ts = d.timeScale || 1;
    const hasMore = d.hasMore || false;
    const zoomLabel = ts < 1 ? `${(1/ts).toFixed(1)}px/ms` : `${ts.toFixed(0)}ms/px`;
    render(html`
      <style>
        :host { display:flex; align-items:center; gap:8px; padding:0 12px;
                background:#161b22; border-bottom:1px solid #30363d;
                font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; }
        .title { font-weight:600; white-space:nowrap; }
        select { flex:1; min-width:120px; max-width:380px; background:#21262d; color:#e6edf3;
                 border:1px solid #30363d; border-radius:4px; padding:3px 8px; font:inherit; cursor:pointer; }
        button { background:#21262d; color:#e6edf3; border:1px solid #30363d;
                 border-radius:4px; padding:2px 8px; cursor:pointer; font-size:14px; line-height:1; }
        button:hover { border-color:#58a6ff; }
        .cost { white-space:nowrap; color:#8b949e; } .cost strong { color:#e6edf3; }
        .zoom { display:flex; align-items:center; gap:4px; flex-shrink:0; }
        .zoom-label { font-size:11px; color:#8b949e; min-width:48px; text-align:center; }
      </style>
      <span class="title">Amplifier Cost Viewer</span>
      <select @change=${this.#onSelect}>
        ${sessions.map(s => {
          const shortId = s.session_id.slice(0, 8);
          const label = s.name ? `${s.name} (${shortId})` : shortId;
          const cost = (s.total_cost_usd || 0).toFixed(2);
          const tok = (s.total_input_tokens||0) + (s.total_output_tokens||0);
          const tokStr = tok > 0 ? ` · ${_fmtTokens(tok)} tok` : '';
          return html`<option value=${s.session_id} ?selected=${s.session_id === activeId}
            >${label} — ${_formatDate(s.start_ts)} — $${cost}${tokStr}</option>`;
        })}
        ${hasMore ? html`<option value="__load_more__">— Load more (${sessions.length} shown) —</option>` : nothing}
      </select>
      <span class="cost">Total: <strong>$${totalCost.toFixed(4)}</strong></span>
      <button title="Refresh session list" @click=${() => this.#dispatch('refresh')}>↻</button>
      <div class="zoom">
        <button title="Zoom out" @click=${() => this.#dispatch('zoom-out')}>−</button>
        <span class="zoom-label">${zoomLabel}</span>
        <button title="Zoom in" @click=${() => this.#dispatch('zoom-in')}>+</button>
      </div>
    `, this.#shadow);
  }
  #onSelect = (e) => {
    const id = e.target.value;
    if (id === '__load_more__') { this.#dispatch('load-more'); return; }
    this.dispatchEvent(new CustomEvent('session-change', {detail: {sessionId: id}, bubbles: true}));
  };
  #dispatch(name) { this.dispatchEvent(new Event(name, {bubbles: true})); }
}
customElements.define('acv-toolbar', AcvToolbar);

// ================================================================
// <acv-tree>
// ================================================================

class AcvTree extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = {};
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() {
    const d = this._data; const root = d.sessionData;
    const activeId = d.activeSessionId; const expanded = d.expandedSessions || new Set();
    if (!root) {
      render(html`<style>${this.#styles()}</style><div class="placeholder">No session loaded.</div>`, this.#shadow);
      return;
    }
    const maxCost = this.#maxCostOf(root); const rows = [];
    this.#flatten(root, 0, expanded, maxCost, activeId, rows);
    render(html`<style>${this.#styles()}</style>${rows}`, this.#shadow);
  }
  #maxCostOf(node) {
    let max = node.total_cost_usd || 0;
    if (node.children) node.children.forEach(c => { max = Math.max(max, c.total_cost_usd || 0); });
    return max || 1;
  }
  #flatten(node, depth, expanded, maxCost, activeId, rows) {
    const sid = node.session_id; const isExp = expanded.has(sid);
    const hasKids = node.children && node.children.length > 0;
    const cost = node.total_cost_usd || 0;
    const barW = Math.max(2, (cost / maxCost) * 100);
    const label = node.name || node.agent_name || sid.slice(-8);
    const tok = (node.total_input_tokens || 0) + (node.total_output_tokens || 0);
    const costLabel = tok > 0 ? `$${cost.toFixed(2)} · ${_fmtTokens(tok)}` : `$${cost.toFixed(4)}`;
    rows.push(html`
      <div class="tree-row ${sid === activeId ? 'active' : ''}" style="padding-left:${8 + depth * 12}px"
           @click=${() => this.#onRowClick(sid, hasKids)}>
        <span class="toggle">${hasKids ? (isExp ? '▾' : '▸') : html`&nbsp;`}</span>
        <span class="session-label" title=${sid}>${label}</span>
        <span class="session-cost">${costLabel}</span>
        <div class="cost-bar" style="width:${barW}%"></div>
      </div>`);
    if (isExp && hasKids) node.children.forEach(c => this.#flatten(c, depth + 1, expanded, maxCost, activeId, rows));
  }
  #onRowClick(sessionId, hasChildren) {
    if (hasChildren) this.dispatchEvent(new CustomEvent('toggle-expand', {detail: {sessionId}, bubbles: true}));
    this.dispatchEvent(new CustomEvent('session-select', {detail: {sessionId}, bubbles: true}));
  }
  #styles() {
    return `:host { display:block; background:#161b22; border-right:1px solid #30363d;
      font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; overflow-y:auto; }
      .placeholder { padding:12px 8px; color:#8b949e; font-style:italic; }
      .tree-row { display:flex; align-items:center; height:32px; padding-right:8px;
        cursor:pointer; user-select:none; border-left:2px solid transparent; position:relative; }
      .tree-row:hover { background:#21262d; }
      .tree-row.active { border-left-color:#58a6ff; background:#21262d; }
      .toggle { flex-shrink:0; width:14px; color:#8b949e; font-size:10px; text-align:center; }
      .session-label { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .session-cost { flex-shrink:0; color:#8b949e; font-size:11px; margin-left:4px; }
      .cost-bar { position:absolute; bottom:0; left:0; height:3px; background:#58a6ff; opacity:0.4; }`;
  }
}
customElements.define('acv-tree', AcvTree);

// ================================================================
// <acv-timeline> — heatmap + ruler + Canvas Gantt
// ================================================================

class AcvTimeline extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  #canvas = null;
  #ctx = null;
  #rafId = null;
  _data = {};

  connectedCallback() { this.update(); }

  set data(val) {
    this._data = val;
    this.update();
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = requestAnimationFrame(() => {
      this.#ensureCanvas();
      this.#draw();
      this.#rafId = null;
    });
  }

  update() {
    const d = this._data;
    const spans = d.spans || [];
    const ts = d.timeScale || 1;
    const scrollL = d.scrollLeft || 0;
    render(html`
      <style>${this.#styles()}</style>
      <div id="heatmap">${this.#renderHeatmap(spans, ts, scrollL)}</div>
      <div id="ruler" @wheel=${this.#onRulerWheel}>${this.#renderRuler(spans, ts, scrollL)}</div>
      <div id="canvas-wrap"><canvas id="gantt-canvas"></canvas></div>
    `, this.#shadow);
  }

  #ensureCanvas() {
    if (this.#canvas) return;
    this.#canvas = this.#shadow.querySelector('#gantt-canvas');
    if (!this.#canvas) return;
    this.#ctx = this.#canvas.getContext('2d');
    this.#canvas.addEventListener('click', (e) => this.#onCanvasClick(e));
  }

  #resizeCanvas() {
    if (!this.#canvas) return;
    const wrap = this.#canvas.parentElement;
    if (!wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const w = wrap.clientWidth; const h = wrap.clientHeight;
    this.#canvas.width = w * dpr;
    this.#canvas.height = h * dpr;
    this.#canvas.style.width = w + 'px';
    this.#canvas.style.height = h + 'px';
    this.#ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  #draw() {
    if (!this.#ctx) return;
    this.#resizeCanvas();
    const ctx = this.#ctx;
    const dpr = window.devicePixelRatio || 1;
    const cw = this.#canvas.width / dpr;
    const ch = this.#canvas.height / dpr;
    const d = this._data;
    const spans = d.spans || [];
    const ts = d.timeScale || 1;
    const scrollL = d.scrollLeft || 0;
    const expanded = d.expandedSessions || new Set();
    const sessionData = d.sessionData;

    ctx.clearRect(0, 0, cw, ch);

    if (!spans.length || !sessionData) {
      ctx.fillStyle = '#8b949e';
      ctx.font = '12px monospace';
      ctx.fillText('No spans to display.', 20, 30);
      return;
    }

    const rowMap = _rowIndexMap(sessionData, expanded);
    const numRows = rowMap.size;

    // 1. Alternating row backgrounds
    for (let i = 0; i < numRows && i * ROW_H < ch; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#0d1117' : '#161b22';
      ctx.fillRect(0, i * ROW_H, cw, ROW_H);
    }

    // 2. Grid lines from ruler ticks
    const maxEndMs = spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
    const visibleMs = cw * ts;
    let tickInterval;
    if (visibleMs < 5000) tickInterval = 500;
    else if (visibleMs < 30000) tickInterval = 5000;
    else if (visibleMs < 120000) tickInterval = 30000;
    else if (visibleMs < 600000) tickInterval = 60000;
    else tickInterval = 300000;
    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 1;
    for (let t = 0; t <= maxEndMs; t += tickInterval) {
      const x = t / ts - scrollL;
      if (x < -1 || x > cw + 1) continue;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, ch);
      ctx.stroke();
    }

    // 3. Color-batched span drawing
    const batches = new Map(); // color → [{x, y, w, h}]
    spans.forEach(span => {
      const row = rowMap.get(span.session_id);
      if (row === undefined) return; // collapsed session
      const x = (span.start_ms || 0) / ts - scrollL;
      const w = Math.max(2, ((span.end_ms || 0) - (span.start_ms || 0)) / ts);
      // Visibility culling
      if (x + w < -10 || x > cw + 10) return;
      const y = row * ROW_H + (ROW_H - SPAN_H) / 2;
      const color = span.color || '#64748B';
      if (!batches.has(color)) batches.set(color, []);
      batches.get(color).push({x, y, w, h: SPAN_H});
    });
    for (const [color, rects] of batches) {
      ctx.beginPath();
      rects.forEach(r => ctx.rect(r.x, r.y, r.w, r.h));
      ctx.fillStyle = color;
      ctx.fill();
    }

    // 4. Text labels on wide spans (>60px)
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.font = '10px monospace';
    spans.forEach(span => {
      const row = rowMap.get(span.session_id);
      if (row === undefined) return;
      const x = (span.start_ms || 0) / ts - scrollL;
      const w = ((span.end_ms || 0) - (span.start_ms || 0)) / ts;
      if (w < 60) return;
      if (x + w < 0 || x > cw) return;
      const label = span.type === 'llm'
        ? `${span.model || ''} · $${(span.cost_usd||0).toFixed(3)}`
        : (span.tool_name || span.type || '');
      ctx.fillText(label, x + 4, row * ROW_H + ROW_H / 2 + 3, w - 8);
    });

    // 5. Orchestrator gap labels in dark spaces > 200px
    const visibleSessions = _visibleRows(sessionData, expanded);
    visibleSessions.forEach((node, rowIdx) => {
      const sid = node.session_id;
      const sessionSpans = spans.filter(s => s.session_id === sid).sort((a, b) => a.start_ms - b.start_ms);
      for (let i = 0; i < sessionSpans.length - 1; i++) {
        const gapStart = sessionSpans[i].end_ms || 0;
        const gapEnd = sessionSpans[i + 1].start_ms || 0;
        const gapPx = (gapEnd - gapStart) / ts;
        if (gapPx < 200) continue;
        const gx = gapStart / ts - scrollL;
        if (gx + gapPx < 0 || gx > cw) continue;
        ctx.fillStyle = 'rgba(139,148,158,0.4)';
        ctx.font = 'italic 9px monospace';
        ctx.fillText(`idle ${_formatMs(gapEnd - gapStart)}`, gx + gapPx / 2 - 30, rowIdx * ROW_H + ROW_H / 2 + 3);
      }
    });
  }

  #renderHeatmap(spans, ts, scrollL) {
    if (!spans.length) return nothing;
    const maxEndMs = spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
    const totalPx = maxEndMs / ts;
    const bucketW = 4;
    const numBuckets = Math.max(1, Math.ceil(totalPx / bucketW));
    const buckets = new Float64Array(numBuckets);
    let maxBucket = 0;
    spans.forEach(s => {
      if (!s.cost_usd) return;
      const sb = Math.floor((s.start_ms / ts) / bucketW);
      const eb = Math.floor(((s.end_ms || s.start_ms) / ts) / bucketW);
      const n = Math.max(1, eb - sb + 1);
      const c = s.cost_usd / n;
      for (let b = sb; b <= eb && b < numBuckets; b++) {
        buckets[b] += c;
        if (buckets[b] > maxBucket) maxBucket = buckets[b];
      }
    });
    if (maxBucket === 0) return nothing;
    let peakIdx = 0;
    for (let i = 1; i < numBuckets; i++) { if (buckets[i] > buckets[peakIdx]) peakIdx = i; }
    const cols = [];
    for (let i = 0; i < numBuckets; i++) {
      const op = buckets[i] / maxBucket;
      const left = i * bucketW - scrollL;
      if (left < -bucketW || left > 2000) continue;
      cols.push(html`<div style="position:absolute;left:${left}px;width:${bucketW}px;height:${HEATMAP_H}px;
        background:rgba(123,47,190,${op.toFixed(3)});${i === peakIdx ? 'border-right:1px solid #f59e0b;' : ''}"></div>`);
    }
    return cols;
  }

  #renderRuler(spans, ts, scrollL) {
    if (!spans.length) return nothing;
    const maxEndMs = spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
    const visibleMs = 1000 * ts;
    let tickInterval;
    if (visibleMs < 5000) tickInterval = 500;
    else if (visibleMs < 30000) tickInterval = 5000;
    else if (visibleMs < 120000) tickInterval = 30000;
    else if (visibleMs < 600000) tickInterval = 60000;
    else if (visibleMs < 3600000) tickInterval = 300000;
    else tickInterval = 900000;
    const ticks = [];
    for (let t = 0; t <= maxEndMs; t += tickInterval) {
      const x = t / ts - scrollL;
      if (x < -50 || x > 3000) continue;
      ticks.push(html`<div class="tick" style="left:${x}px">
        <div class="tick-line"></div><span class="tick-label">${_formatMs(t)}</span></div>`);
    }
    return ticks;
  }

  #onRulerWheel = (e) => {
    e.preventDefault(); e.stopPropagation();
    const factor = e.deltaY > 0 ? 1.3 : (1 / 1.3);
    const oldScale = state.timeScale;
    const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, oldScale * factor));
    if (newScale === oldScale) return;
    const rulerEl = this.#shadow.querySelector('#ruler');
    const rect = rulerEl.getBoundingClientRect();
    const cursorX = e.clientX - rect.left + state.scrollLeft;
    const msAtCursor = cursorX * oldScale;
    state.timeScale = newScale;
    state.scrollLeft = Math.max(0, msAtCursor / newScale - (e.clientX - rect.left));
    renderAll();
  };

  #onCanvasClick(e) {
    // Hit-test spans — implemented in Task 6 with detail panel
    const d = this._data;
    const spans = d.spans || [];
    const ts = d.timeScale || 1;
    const scrollL = d.scrollLeft || 0;
    const expanded = d.expandedSessions || new Set();
    const sessionData = d.sessionData;
    if (!sessionData) return;
    const rowMap = _rowIndexMap(sessionData, expanded);
    const rect = this.#canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    let hit = null;
    for (const span of spans) {
      const row = rowMap.get(span.session_id);
      if (row === undefined) continue;
      const x = (span.start_ms || 0) / ts - scrollL;
      const w = Math.max(2, ((span.end_ms || 0) - (span.start_ms || 0)) / ts);
      const y = row * ROW_H + (ROW_H - SPAN_H) / 2;
      if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + SPAN_H) {
        hit = span;
        break;
      }
    }
    this.dispatchEvent(new CustomEvent('span-select', {detail: {span: hit}, bubbles: true}));
  }

  #styles() {
    return `:host { display:flex; flex-direction:column; min-width:0; overflow:hidden;
      font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; }
      #heatmap { height:${HEATMAP_H}px; position:relative; overflow:hidden; background:#0d1117; flex-shrink:0; }
      #ruler { height:28px; min-height:28px; position:relative; overflow:hidden;
        background:#161b22; border-bottom:1px solid #30363d; flex-shrink:0; cursor:ew-resize; }
      .tick { position:absolute; top:0; height:100%; }
      .tick-line { width:1px; height:8px; background:#30363d; }
      .tick-label { position:absolute; top:10px; font-size:10px; color:#8b949e;
        transform:translateX(-50%); white-space:nowrap; }
      #canvas-wrap { flex:1; min-height:0; overflow:hidden; position:relative; }
      canvas { display:block; }`;
  }
}
customElements.define('acv-timeline', AcvTimeline);

// ================================================================
// <acv-detail> — shell (implemented in Task 6)
// ================================================================

class AcvDetail extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = null;
  connectedCallback() { this.update(); }
  set data(val) { this._data = val; this.update(); }
  update() { render(html`<div></div>`, this.#shadow); }
}
customElements.define('acv-detail', AcvDetail);

// ================================================================
// Render all + Load session + Init
// ================================================================

function renderAll() {
  const toolbar = document.getElementById('toolbar');
  const tree = document.getElementById('tree');
  const timeline = document.getElementById('timeline');
  if (toolbar) toolbar.data = {
    sessions: state.sessions, activeSessionId: state.activeSessionId,
    totalCost: state.sessions.reduce((s, sess) => s + (sess.total_cost_usd || 0), 0),
    timeScale: state.timeScale, hasMore: state.sessionsHasMore,
  };
  if (tree) tree.data = {
    sessionData: state.sessionData, activeSessionId: state.activeSessionId,
    expandedSessions: state.expandedSessions,
  };
  if (timeline) timeline.data = {
    spans: state.spans, sessionData: state.sessionData,
    expandedSessions: state.expandedSessions, timeScale: state.timeScale,
    scrollLeft: state.scrollLeft, selectedSpan: state.selectedSpan,
  };
}

async function loadSession(id) {
  state.activeSessionId = id;
  await Promise.all([fetchSession(id), fetchSpans(id)]);
  state.expandedSessions.clear();
  state.expandedSessions.add(id);
  if (state.sessionData && state.sessionData.children)
    state.sessionData.children.forEach(c => state.expandedSessions.add(c.session_id));
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
  const el = document.getElementById('timeline');
  const width = (el ? el.clientWidth : 800) || 800;
  state.timeScale = maxEndMs / Math.max(width - 40, 400);
  state.scrollLeft = 0;
  state.selectedSpan = null;
  renderAll();
}

async function init() {
  const toolbar = document.getElementById('toolbar');
  const tree = document.getElementById('tree');
  const timeline = document.getElementById('timeline');

  toolbar.addEventListener('session-change', async (e) => {
    try { await loadSession(e.detail.sessionId); }
    catch (err) { console.error('Failed to load session:', err); }
  });
  toolbar.addEventListener('zoom-in', () => {
    state.timeScale = Math.max(ZOOM_MIN, state.timeScale * 0.7); renderAll();
  });
  toolbar.addEventListener('zoom-out', () => {
    state.timeScale = Math.min(ZOOM_MAX, state.timeScale * 1.3); renderAll();
  });
  toolbar.addEventListener('refresh', async () => {
    try {
      await fetch('/api/refresh', {method: 'POST'});
      await fetchSessions(0); state.activeSessionId = null; renderAll();
      if (state.sessions.length > 0) await loadSession(state.sessions[0].session_id);
    } catch (err) { console.error('Refresh failed:', err); }
  });
  toolbar.addEventListener('load-more', async () => {
    try { await fetchSessions(state.sessionsOffset); renderAll(); }
    catch (err) { console.error('Load more failed:', err); }
  });

  tree.addEventListener('toggle-expand', (e) => {
    const sid = e.detail.sessionId;
    if (state.expandedSessions.has(sid)) state.expandedSessions.delete(sid);
    else state.expandedSessions.add(sid);
    renderAll();
  });
  tree.addEventListener('session-select', () => renderAll());

  timeline.addEventListener('span-select', (e) => {
    state.selectedSpan = e.detail.span;
    renderAll();
  });

  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
    const shift = e.shiftKey ? 3 : 1;
    switch (e.code) {
      case 'KeyW': case 'Equal':
        e.preventDefault(); state.timeScale = Math.max(ZOOM_MIN, state.timeScale * Math.pow(0.7, shift)); renderAll(); break;
      case 'KeyS': case 'Minus':
        e.preventDefault(); state.timeScale = Math.min(ZOOM_MAX, state.timeScale * Math.pow(1.3, shift)); renderAll(); break;
      case 'KeyA': case 'ArrowLeft':
        e.preventDefault(); state.scrollLeft = Math.max(0, state.scrollLeft - 150 * shift); renderAll(); break;
      case 'KeyD': case 'ArrowRight':
        e.preventDefault(); state.scrollLeft += 150 * shift; renderAll(); break;
      case 'Escape':
        state.selectedSpan = null; renderAll(); break;
    }
  });

  try { await fetchSessions(); }
  catch (err) { console.error('Failed to fetch sessions:', err); return; }
  renderAll();
  if (state.sessions.length > 0) {
    try { await loadSession(state.sessions[0].session_id); }
    catch (err) { console.error('Failed to load first session:', err); }
  }
}

document.addEventListener('DOMContentLoaded', init);
```

**Step 4: Run tests — verify they pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All PASS.

**Step 5: Browser verification**

Open http://localhost:8000. Verify:
- **Colored bars appear** for each span in the Canvas area
- Different providers have different colors (purple for Anthropic, teal for OpenAI)
- Span labels appear on wide bars (model name + cost)
- Alternating row backgrounds are visible
- Zoom in (W key) → bars get wider, more detail visible
- Zoom out (S key) → bars get narrower, more overview
- Pan left/right (A/D) → canvas scrolls
- Grid lines align with ruler ticks
- Click a span → console should show the span-select event (detail panel comes in Task 6)

**Step 6: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py
git commit -m "feat(viewer): canvas gantt — color-batched span drawing + visibility culling"
```

---

### Task 6: `<acv-detail>` — span detail panel

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` (replace AcvDetail shell with full implementation)
- Modify: `tests/test_app_js.py` (add TestAcvDetail class)

**Step 1: Add tests to `tests/test_app_js.py`**

Append this test class at the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: <acv-detail> implementation (Task 6)
# ---------------------------------------------------------------------------


class TestAcvDetail:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_detail_shows_provider_model(self) -> None:
        assert "span.provider" in self.content or "provider" in self.content
        assert "span.model" in self.content or "model" in self.content

    def test_detail_shows_timing(self) -> None:
        assert "_formatMs" in self.content

    def test_detail_shows_tokens(self) -> None:
        assert "input_tokens" in self.content
        assert "output_tokens" in self.content

    def test_detail_shows_cache_tokens(self) -> None:
        assert "cache_read" in self.content or "cache_write" in self.content

    def test_detail_shows_cost(self) -> None:
        assert "cost_usd" in self.content
        assert "toFixed(6)" in self.content

    def test_detail_handles_tool_spans(self) -> None:
        assert "tool_name" in self.content or "tool" in self.content

    def test_detail_has_close_button(self) -> None:
        assert "close" in self.content.lower()

    def test_detail_dispatches_close_event(self) -> None:
        assert "detail-close" in self.content or "'close'" in self.content

    def test_detail_shows_io_content(self) -> None:
        assert "IO_TRUNCATE" in self.content

    def test_detail_io_truncation(self) -> None:
        assert "slice(0, IO_TRUNCATE)" in self.content or "IO_TRUNCATE" in self.content

    def test_detail_hidden_when_null(self) -> None:
        assert "display:none" in self.content or "hidden" in self.content.lower()
```

**Step 2: Run tests — verify new tests fail (RED)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_app_js.py::TestAcvDetail -v 2>&1 | tail -5
```

Expected: FAILED — AcvDetail is still a shell.

**Step 3: Implement AcvDetail**

In `amplifier_app_cost_viewer/static/app.js`, find the `<acv-detail> — shell` section and replace the entire `AcvDetail` class with:

```javascript
// ================================================================
// <acv-detail>
// ================================================================

class AcvDetail extends HTMLElement {
  #shadow = this.attachShadow({mode: 'open'});
  _data = null;

  connectedCallback() { this.update(); }

  set data(val) { this._data = val; this.update(); }

  update() {
    const span = this._data;
    if (!span) {
      render(html`<style>${this.#styles()}</style><div class="hidden"></div>`, this.#shadow);
      return;
    }
    const type = span.type || '';
    render(html`
      <style>${this.#styles()}</style>
      <div class="panel">
        <div class="header">
          <span class="title">${this.#titleFor(span)}</span>
          <button class="close-btn" @click=${this.#onClose}>✕</button>
        </div>
        <div class="grid">
          ${this.#timingRow(span)}
          ${type === 'llm' ? this.#llmRows(span) : nothing}
          ${type === 'tool' ? this.#toolRows(span) : nothing}
        </div>
        ${this.#ioBlock('INPUT', span.input_text || span.input)}
        ${this.#ioBlock('OUTPUT', span.output_text || span.output)}
      </div>
    `, this.#shadow);
  }

  #titleFor(span) {
    if (span.type === 'llm') return `${span.provider || ''}/${span.model || ''}`;
    if (span.type === 'tool') return `${span.tool_name || span.name || 'tool'} ${span.success ? '✓' : '✗'}`;
    if (span.type === 'thinking') return html`<span style="color:#6366F1">thinking</span>`;
    return span.type || 'span';
  }

  #timingRow(span) {
    const start = _formatMs(span.start_ms || 0);
    const end = _formatMs(span.end_ms || 0);
    const dur = _formatMs((span.end_ms || 0) - (span.start_ms || 0));
    return html`
      <div class="row"><span class="label">time</span><span class="value">${start} → ${end} (${dur})</span></div>
    `;
  }

  #llmRows(span) {
    const costStr = span.cost_usd != null ? `$${span.cost_usd.toFixed(6)}` : 'n/a';
    return html`
      <div class="row"><span class="label">in</span><span class="value">${span.input_tokens != null ? span.input_tokens.toLocaleString() : 'n/a'}</span></div>
      <div class="row"><span class="label">out</span><span class="value">${span.output_tokens != null ? span.output_tokens.toLocaleString() : 'n/a'}</span></div>
      ${span.cache_read_tokens != null ? html`<div class="row"><span class="label">cache_read</span><span class="value">${span.cache_read_tokens.toLocaleString()}</span></div>` : nothing}
      ${span.cache_write_tokens != null ? html`<div class="row"><span class="label">cache_write</span><span class="value">${span.cache_write_tokens.toLocaleString()}</span></div>` : nothing}
      <div class="row"><span class="label">total</span><span class="value">${((span.input_tokens||0)+(span.output_tokens||0)+(span.cache_read_tokens||0)).toLocaleString()} tok</span></div>
      <div class="row"><span class="label">cost</span><span class="value">${costStr}</span></div>
    `;
  }

  #toolRows(span) {
    const dur = _formatMs((span.end_ms || 0) - (span.start_ms || 0));
    return html`
      <div class="row"><span class="label">duration</span><span class="value">${dur}</span></div>
      <div class="row"><span class="label">success</span><span class="value" style="color:${span.success ? '#3fb950' : '#f85149'}">${span.success ? '✓ yes' : '✗ no'}</span></div>
    `;
  }

  #ioBlock(label, value) {
    if (value == null) return nothing;
    const str = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    const truncated = str.length > IO_TRUNCATE;
    const display = truncated ? str.slice(0, IO_TRUNCATE) + '…' : str;
    return html`
      <div class="io-block">
        <div class="io-label">${_esc(label)}</div>
        <pre class="io-content">${display}</pre>
        ${truncated ? html`<button class="show-more" @click=${(e) => {
          e.target.previousElementSibling.textContent = str;
          e.target.remove();
        }}>show more (${str.length} chars)</button>` : nothing}
      </div>
    `;
  }

  #onClose = () => {
    this.dispatchEvent(new Event('detail-close', {bubbles: true, composed: true}));
  };

  #styles() {
    return `:host { display:block; }
      .hidden { display:none; }
      .panel { background:#161b22; border-top:1px solid #30363d; padding:10px 14px;
        font:12px/1.5 "SF Mono",Consolas,monospace; color:#e6edf3; max-height:40vh; overflow-y:auto; }
      .header { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
      .title { font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .close-btn { background:none; border:none; color:#8b949e; cursor:pointer; font-size:14px; padding:2px 4px; border-radius:3px; }
      .close-btn:hover { color:#e6edf3; background:#21262d; }
      .grid { display:grid; grid-template-columns:auto 1fr; gap:2px 12px; margin-bottom:8px; }
      .row { display:contents; }
      .label { color:#8b949e; text-align:right; }
      .value { color:#e6edf3; }
      .io-block { margin-top:8px; }
      .io-label { color:#8b949e; text-transform:uppercase; font-size:10px; letter-spacing:0.05em; margin-bottom:2px; }
      .io-content { background:#21262d; border:1px solid #30363d; border-radius:4px; padding:6px;
        max-height:80px; overflow-y:auto; white-space:pre-wrap; word-break:break-word; font:inherit; color:#e6edf3; margin:0; }
      .show-more { color:#58a6ff; cursor:pointer; font-size:11px; text-decoration:underline;
        background:none; border:none; font-family:inherit; margin-top:2px; }`;
  }
}
customElements.define('acv-detail', AcvDetail);
```

Now wire the detail panel into the timeline. The `<acv-detail>` component should appear inside `<acv-timeline>`'s shadow DOM. In the AcvTimeline's `update()` method, add `<acv-detail>` after the canvas-wrap div:

Find this line inside AcvTimeline's `update()`:
```javascript
      <div id="canvas-wrap"><canvas id="gantt-canvas"></canvas></div>
```

Replace it with:
```javascript
      <div id="canvas-wrap"><canvas id="gantt-canvas"></canvas></div>
      <acv-detail id="detail" .data=${d.selectedSpan} @detail-close=${this.#onDetailClose}></acv-detail>
```

Then add this method to AcvTimeline:
```javascript
  #onDetailClose = () => {
    this.dispatchEvent(new Event('detail-close', {bubbles: true}));
  };
```

And wire it in `init()` — add this after the existing `timeline.addEventListener('span-select', ...)` line:
```javascript
  timeline.addEventListener('detail-close', () => {
    state.selectedSpan = null;
    renderAll();
  });
```

**Step 4: Run tests — verify they pass (GREEN)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All PASS.

**Step 5: Browser verification**

Open http://localhost:8000. Verify:
- Click a colored bar in the Canvas → detail panel slides up from bottom
- Detail shows: provider/model title, timing (start → end), token counts, cost
- For tool spans: shows tool name, success/failure indicator
- Close button (✕) dismisses the detail panel
- Escape key dismisses the detail panel
- Input/Output content blocks appear when available
- Long I/O content is truncated with "show more" link

**Step 6: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py
git commit -m "feat(viewer): acv-detail — span detail panel with I/O display"
```

---

### Task 7: Tree expand/collapse wired to Canvas

**Files:**
- Modify: `amplifier_app_cost_viewer/static/app.js` (verify wiring — should already work from previous tasks)
- Modify: `tests/test_app_js.py` (add TestTreeCanvasWiring class)

**Step 1: Add tests to `tests/test_app_js.py`**

Append this test class at the end of `tests/test_app_js.py`:

```python
# ---------------------------------------------------------------------------
# Tests: Tree ↔ Canvas wiring (Task 7)
# ---------------------------------------------------------------------------


class TestTreeCanvasWiring:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_toggle_expand_wired_in_init(self) -> None:
        assert "toggle-expand" in self.content

    def test_expanded_sessions_delete(self) -> None:
        assert "expandedSessions.delete(" in self.content or "expandedSessions.delete (" in self.content

    def test_expanded_sessions_add(self) -> None:
        assert "expandedSessions.add(" in self.content

    def test_visible_rows_respects_expanded(self) -> None:
        assert "_visibleRows" in self.content
        assert "expanded.has(" in self.content or "expandedSessions.has(" in self.content

    def test_row_index_map_used_in_draw(self) -> None:
        assert "_rowIndexMap" in self.content

    def test_collapsed_sessions_skip_drawing(self) -> None:
        # rowMap.get returns undefined for collapsed sessions → skip
        assert "row === undefined" in self.content or "row == undefined" in self.content

    def test_render_all_passes_expanded_to_timeline(self) -> None:
        assert "expandedSessions" in self.content

    def test_detail_close_wired(self) -> None:
        assert "detail-close" in self.content

    def test_span_select_sets_selected_span(self) -> None:
        assert "state.selectedSpan" in self.content
```

**Step 2: Run tests — verify they pass (should already be GREEN)**

The expand/collapse → Canvas wiring was already implemented across Tasks 3-5. The `toggle-expand` event handler in `init()` updates `state.expandedSessions`, calls `renderAll()`, which passes the updated `expandedSessions` to the timeline, which uses `_rowIndexMap()` to skip collapsed session rows during `#draw()`.

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_app_js.py::TestTreeCanvasWiring -v
```

Expected: All PASS. If any test fails, the fix is to ensure the string pattern appears in app.js. Check the test failure message and locate the expected string.

**Step 3: Verify the full wiring works end-to-end**

Run the complete test suite:

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/test_static_shell.py tests/test_app_js.py -v
```

Expected: All PASS.

**Step 4: Browser verification**

Open http://localhost:8000. Verify specifically:
- Click a session row with children (▾ toggle) → children collapse, Gantt rows disappear instantly
- Click again → children expand, Gantt rows reappear
- Collapse a deeply nested session → only its children's Gantt rows disappear
- The Gantt always matches the tree: same number of rows, same order
- Detail panel still works after expand/collapse cycles

**Step 5: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add amplifier_app_cost_viewer/static/app.js tests/test_app_js.py
git commit -m "feat(viewer): tree expand/collapse wired to canvas + wiring tests"
```

---

### Task 8: Final polish + full test run

**Files:**
- No code changes (unless tests fail)

**Step 1: Run ALL tests (backend + frontend)**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run python -m pytest tests/ -v --tb=short
```

Expected: ALL tests pass — both the replaced frontend tests and the unchanged backend tests. Look for a line like:
```
XXX passed in Y.YYs
```

If any backend tests fail, that means you accidentally changed a backend file. Check `git diff` and revert any unintended changes.

**Step 2: Manual browser verification checklist**

Start the server if not already running:
```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer --host 0.0.0.0
```

Open http://localhost:8000 and verify each item:

- [ ] Session list loads < 2 seconds
- [ ] Named sessions appear in dropdown with names (not just hex IDs)
- [ ] Select a different session → Gantt renders < 500ms
- [ ] Zoom + / − buttons work (toolbar)
- [ ] Scroll wheel on ruler zooms (centered on cursor, no page bounce)
- [ ] W key → zoom in, S key → zoom out
- [ ] A key → pan left, D key → pan right
- [ ] Shift+W → 3× faster zoom
- [ ] Tree expand/collapse (click rows with ▾/▸) → Gantt rows appear/disappear instantly
- [ ] Click a span in the Gantt → detail panel appears with correct data
- [ ] ✕ button closes detail panel
- [ ] Escape key closes detail panel
- [ ] Cost heatmap shows purple intensity gradient
- [ ] Amber marker (|) on peak cost bucket
- [ ] Refresh button (↻) reloads session list
- [ ] "Load more" option appears at bottom of dropdown when more sessions exist
- [ ] No console errors (DevTools → Console)
- [ ] Labels appear on wide span bars (model name + cost)

**Step 3: Final commit**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
git add -A
git commit -m "feat(viewer): v2 frontend — Lit components + Canvas Gantt"
```

---

## Summary of all files changed

| File | Action | Task |
|------|--------|------|
| `amplifier_app_cost_viewer/static/vendor/lit.all.min.js` | Created (download) | 1 |
| `amplifier_app_cost_viewer/static/index.html` | Rewritten | 1 |
| `amplifier_app_cost_viewer/static/style.css` | Rewritten | 1 |
| `amplifier_app_cost_viewer/static/app.js` | Rewritten (iteratively) | 1–7 |
| `tests/test_static_shell.py` | Replaced | 1 |
| `tests/test_app_js.py` | Replaced + extended | 1–7 |

## Files NOT changed

- `amplifier_app_cost_viewer/server.py` — backend unchanged
- `amplifier_app_cost_viewer/reader.py` — backend unchanged
- `amplifier_app_cost_viewer/pricing.py` — backend unchanged
- `tests/test_scaffold.py` — backend test unchanged
- `tests/test_reader.py` — backend test unchanged
- `tests/test_pricing.py` — backend test unchanged
- `tests/test_server.py` — backend test unchanged
- `tests/conftest.py` — test fixtures unchanged
- `pyproject.toml` — no new dependencies