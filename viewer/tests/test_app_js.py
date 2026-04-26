"""Tests for app.js v2 — written FIRST before the file is rewritten (TDD RED).

Tests verify that app.js:
- Exists and has >500 chars
- Imports html/render from the local Lit vendor bundle
- Declares a const state object with the required properties
- Defines 4 custom element classes (AcvToolbar, AcvTree, AcvTimeline, AcvDetail)
  all extending HTMLElement, all using attachShadow, all registered via
  customElements.define
- Defines async function init()
- Adds a DOMContentLoaded listener
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

STATIC = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static"
APP_JS = STATIC / "app.js"
VENDOR_LIT = STATIC / "vendor" / "lit.all.min.js"


# ---------------------------------------------------------------------------
# Tests: vendor bundle
# ---------------------------------------------------------------------------


class TestVendorLit:
    def test_vendor_dir_exists(self) -> None:
        assert (STATIC / "vendor").is_dir(), "static/vendor/ directory must exist"

    def test_lit_bundle_exists(self) -> None:
        assert VENDOR_LIT.exists(), "static/vendor/lit.all.min.js must exist"

    def test_lit_bundle_size_gt_20kb(self) -> None:
        size = VENDOR_LIT.stat().st_size
        assert size > 20_000, (
            f"lit.all.min.js must be >20KB (got {size} bytes) — download from CDN"
        )


# ---------------------------------------------------------------------------
# Tests: app.js existence
# ---------------------------------------------------------------------------


class TestAppJsExists:
    def test_file_exists(self) -> None:
        assert APP_JS.exists(), f"{APP_JS} must exist"

    def test_has_substantial_content(self) -> None:
        content = APP_JS.read_text()
        assert len(content) > 500, "app.js must have >500 chars"


# ---------------------------------------------------------------------------
# Tests: Lit import
# ---------------------------------------------------------------------------


class TestAppJsLitImport:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_imports_from_vendor_lit(self) -> None:
        assert "vendor/lit.all.min.js" in self.content, (
            "app.js must import from vendor/lit.all.min.js"
        )

    def test_imports_html(self) -> None:
        assert "html" in self.content, (
            "app.js must import 'html' from Lit vendor bundle"
        )

    def test_imports_render(self) -> None:
        assert "render" in self.content, (
            "app.js must import 'render' from Lit vendor bundle"
        )


# ---------------------------------------------------------------------------
# Tests: state object
# ---------------------------------------------------------------------------


class TestAppJsState:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_const_state_declared(self) -> None:
        assert "const state = {" in self.content or "const state={" in self.content, (
            "Must declare 'const state = {'"
        )

    def test_state_has_sessions(self) -> None:
        assert "sessions" in self.content, "state must have 'sessions' property"

    def test_state_has_active_session_id(self) -> None:
        assert "activeSessionId" in self.content, (
            "state must have 'activeSessionId' property"
        )

    def test_state_has_session_data(self) -> None:
        assert "sessionData" in self.content, "state must have 'sessionData' property"

    def test_state_has_spans(self) -> None:
        assert "spans" in self.content, "state must have 'spans' property"

    def test_state_has_expanded_sessions(self) -> None:
        assert "expandedSessions" in self.content, (
            "state must have 'expandedSessions' property"
        )

    def test_state_has_selected_span(self) -> None:
        assert "selectedSpan" in self.content, (
            "state must have 'selectedSpan' property"
        )

    def test_state_has_time_scale(self) -> None:
        assert "timeScale" in self.content, "state must have 'timeScale' property"

    def test_state_has_scroll_left(self) -> None:
        assert "scrollLeft" in self.content, "state must have 'scrollLeft' property"


# ---------------------------------------------------------------------------
# Tests: 4 custom element classes
# ---------------------------------------------------------------------------


class TestAppJsCustomElements:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- Class definitions ---

    def test_acv_toolbar_class_defined(self) -> None:
        assert "class AcvToolbar" in self.content, (
            "Must define 'class AcvToolbar' extending HTMLElement"
        )

    def test_acv_tree_class_defined(self) -> None:
        assert "class AcvTree" in self.content, (
            "Must define 'class AcvTree' extending HTMLElement"
        )

    def test_acv_timeline_class_defined(self) -> None:
        assert "class AcvTimeline" in self.content, (
            "Must define 'class AcvTimeline' extending HTMLElement"
        )

    def test_acv_detail_class_defined(self) -> None:
        assert "class AcvDetail" in self.content, (
            "Must define 'class AcvDetail' extending HTMLElement"
        )

    # --- Extend HTMLElement ---

    def test_acv_toolbar_extends_html_element(self) -> None:
        assert "AcvToolbar extends HTMLElement" in self.content, (
            "AcvToolbar must extend HTMLElement"
        )

    def test_acv_tree_extends_html_element(self) -> None:
        assert "AcvTree extends HTMLElement" in self.content, (
            "AcvTree must extend HTMLElement"
        )

    def test_acv_timeline_extends_html_element(self) -> None:
        assert "AcvTimeline extends HTMLElement" in self.content, (
            "AcvTimeline must extend HTMLElement"
        )

    def test_acv_detail_extends_html_element(self) -> None:
        assert "AcvDetail extends HTMLElement" in self.content, (
            "AcvDetail must extend HTMLElement"
        )

    # --- attachShadow ---

    def test_uses_attach_shadow(self) -> None:
        assert "attachShadow" in self.content, (
            "Custom element classes must use attachShadow for shadow DOM"
        )

    def test_attach_shadow_appears_multiple_times(self) -> None:
        count = self.content.count("attachShadow")
        assert count >= 4, (
            f"All 4 custom element classes must call attachShadow, found {count} calls"
        )

    # --- customElements.define ---

    def test_custom_elements_define_toolbar(self) -> None:
        assert (
            "customElements.define('acv-toolbar'" in self.content
            or 'customElements.define("acv-toolbar"' in self.content
        ), "Must register acv-toolbar via customElements.define"

    def test_custom_elements_define_tree(self) -> None:
        assert (
            "customElements.define('acv-tree'" in self.content
            or 'customElements.define("acv-tree"' in self.content
        ), "Must register acv-tree via customElements.define"

    def test_custom_elements_define_timeline(self) -> None:
        assert (
            "customElements.define('acv-timeline'" in self.content
            or 'customElements.define("acv-timeline"' in self.content
        ), "Must register acv-timeline via customElements.define"

    def test_custom_elements_define_detail(self) -> None:
        assert (
            "customElements.define('acv-detail'" in self.content
            or 'customElements.define("acv-detail"' in self.content
        ), "Must register acv-detail via customElements.define"


# ---------------------------------------------------------------------------
# Tests: init function and DOMContentLoaded
# ---------------------------------------------------------------------------


class TestAppJsInit:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_async_init_defined(self) -> None:
        assert "async function init()" in self.content, (
            "Must define 'async function init()'"
        )

    def test_dom_content_loaded_listener(self) -> None:
        assert "DOMContentLoaded" in self.content, (
            "Must add 'DOMContentLoaded' event listener"
        )

    def test_dom_content_loaded_calls_init(self) -> None:
        assert "init" in self.content, (
            "DOMContentLoaded listener must call init"
        )


# ---------------------------------------------------------------------------
# Tests: API functions
# ---------------------------------------------------------------------------


class TestApiCalls:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_fetch_sessions_defined(self) -> None:
        assert "async function fetchSessions" in self.content, (
            "Must define 'async function fetchSessions'"
        )

    def test_fetch_sessions_api_endpoint(self) -> None:
        assert "/api/sessions" in self.content, (
            "fetchSessions must call /api/sessions endpoint"
        )

    def test_fetch_sessions_stores_to_state(self) -> None:
        assert "state.sessions" in self.content, (
            "fetchSessions must store results to state.sessions"
        )

    def test_fetch_sessions_checks_resp_ok(self) -> None:
        assert "resp.ok" in self.content, (
            "fetchSessions must check resp.ok"
        )

    def test_fetch_sessions_throws_on_error(self) -> None:
        assert "throw new Error" in self.content, (
            "fetchSessions must throw on HTTP error"
        )

    def test_fetch_sessions_appends_on_offset(self) -> None:
        content = self.content
        assert any(
            pattern in content
            for pattern in ["...state.sessions", "state.sessions.push", "state.sessions.concat"]
        ), "fetchSessions must append (spread/push/concat) when offset > 0"

    def test_fetch_session_defined(self) -> None:
        assert "async function fetchSession(" in self.content, (
            "Must define 'async function fetchSession(id)'"
        )

    def test_fetch_session_uses_encode_uri_component(self) -> None:
        assert "encodeURIComponent" in self.content, (
            "fetchSession must use encodeURIComponent for session id"
        )

    def test_fetch_session_stores_to_state(self) -> None:
        assert "state.sessionData" in self.content, (
            "fetchSession must store result to state.sessionData"
        )

    def test_fetch_spans_defined(self) -> None:
        assert "async function fetchSpans(" in self.content, (
            "Must define 'async function fetchSpans(id)'"
        )

    def test_fetch_spans_uses_spans_endpoint(self) -> None:
        assert "/spans" in self.content, (
            "fetchSpans must call /spans endpoint"
        )

    def test_fetch_spans_stores_to_state(self) -> None:
        assert "state.spans" in self.content, (
            "fetchSpans must store result to state.spans"
        )


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_format_ms_defined(self) -> None:
        assert "function _formatMs" in self.content, (
            "Must define 'function _formatMs'"
        )

    def test_format_ms_uses_to_fixed_1(self) -> None:
        assert "toFixed(1)" in self.content, (
            "_formatMs must use toFixed(1) for formatting"
        )

    def test_format_ms_has_seconds_unit(self) -> None:
        content = self.content
        assert "'s'" in content or '"s"' in content or "`s`" in content or "/ 1000" in content, (
            "_formatMs must handle seconds unit"
        )

    def test_format_ms_has_minutes_unit(self) -> None:
        content = self.content
        assert "'min'" in content or '"min"' in content or "/ 60" in content, (
            "_formatMs must handle minutes unit"
        )

    def test_fmt_tokens_defined(self) -> None:
        assert "function _fmtTokens" in self.content, (
            "Must define 'function _fmtTokens'"
        )

    def test_format_date_defined(self) -> None:
        assert "function _formatDate" in self.content, (
            "Must define 'function _formatDate'"
        )

    def test_format_date_handles_today(self) -> None:
        assert "Today" in self.content, (
            "_formatDate must handle 'Today' case"
        )

    def test_format_date_handles_yesterday(self) -> None:
        assert "Yesterday" in self.content, (
            "_formatDate must handle 'Yesterday' case"
        )

    def test_esc_defined(self) -> None:
        assert "function _esc" in self.content, (
            "Must define 'function _esc'"
        )

    def test_esc_escapes_amp(self) -> None:
        assert "&amp;" in self.content, (
            "_esc must escape & as &amp;"
        )

    def test_esc_escapes_lt(self) -> None:
        assert "&lt;" in self.content, (
            "_esc must escape < as &lt;"
        )


# ---------------------------------------------------------------------------
# Tests: AcvToolbar — full implementation
# ---------------------------------------------------------------------------


class TestAcvToolbar:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_renders_title(self) -> None:
        assert "Amplifier Cost Viewer" in self.content, (
            "AcvToolbar must render title 'Amplifier Cost Viewer'"
        )

    def test_renders_select(self) -> None:
        assert "<select" in self.content, (
            "AcvToolbar must render a <select> element"
        )

    def test_renders_option(self) -> None:
        assert "<option" in self.content, (
            "AcvToolbar must render <option> elements"
        )

    def test_has_load_more_sentinel(self) -> None:
        assert "__load_more__" in self.content, (
            "AcvToolbar must include __load_more__ sentinel option"
        )

    def test_dispatches_session_change_event(self) -> None:
        assert "session-change" in self.content, (
            "AcvToolbar must dispatch session-change CustomEvent"
        )

    def test_dispatches_zoom_in_event(self) -> None:
        assert "zoom-in" in self.content, (
            "AcvToolbar must dispatch zoom-in CustomEvent"
        )

    def test_dispatches_zoom_out_event(self) -> None:
        assert "zoom-out" in self.content, (
            "AcvToolbar must dispatch zoom-out CustomEvent"
        )

    def test_dispatches_refresh_event(self) -> None:
        assert "CustomEvent" in self.content, (
            "AcvToolbar must use CustomEvent for dispatching"
        )
        assert "dispatchEvent" in self.content, (
            "AcvToolbar must call dispatchEvent"
        )

    def test_shows_total_cost(self) -> None:
        assert "totalCost" in self.content, (
            "AcvToolbar must show totalCost"
        )

    def test_shows_ms_px_zoom_label(self) -> None:
        assert "ms/px" in self.content, (
            "AcvToolbar must show ms/px zoom label"
        )


# ---------------------------------------------------------------------------
# Tests: init wiring
# ---------------------------------------------------------------------------


class TestInitWiring:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_render_all_defined(self) -> None:
        assert "function renderAll" in self.content, (
            "Must define 'function renderAll'"
        )

    def test_load_session_sets_active_session_id(self) -> None:
        assert "state.activeSessionId" in self.content, (
            "loadSession must set state.activeSessionId"
        )

    def test_load_session_calls_fetch_session(self) -> None:
        assert "fetchSession(" in self.content, (
            "loadSession must call fetchSession"
        )

    def test_load_session_calls_fetch_spans(self) -> None:
        assert "fetchSpans(" in self.content, (
            "loadSession must call fetchSpans"
        )

    def test_load_session_computes_time_scale(self) -> None:
        assert "state.timeScale" in self.content, (
            "loadSession must compute state.timeScale"
        )

    def test_init_fetches_sessions(self) -> None:
        assert "fetchSessions" in self.content, (
            "init must call fetchSessions"
        )

    def test_init_loads_first_session(self) -> None:
        assert "sessions[0]" in self.content, (
            "init must load sessions[0]"
        )

    def test_init_handles_errors(self) -> None:
        content = self.content
        assert ".catch(" in content or "try {" in content, (
            "init must handle errors with catch"
        )

    def test_wires_session_change_event(self) -> None:
        assert "session-change" in self.content, (
            "init must wire session-change event listener"
        )

    def test_wires_zoom_in_event(self) -> None:
        assert "zoom-in" in self.content, (
            "init must wire zoom-in event listener"
        )

    def test_wires_zoom_out_event(self) -> None:
        assert "zoom-out" in self.content, (
            "init must wire zoom-out event listener"
        )

    def test_wires_refresh_event(self) -> None:
        assert "refresh" in self.content, (
            "init must wire refresh event listener"
        )

    def test_calls_api_refresh(self) -> None:
        assert "/api/refresh" in self.content, (
            "refresh handler must call /api/refresh"
        )


# ---------------------------------------------------------------------------
# Tests: AcvTree — full implementation
# ---------------------------------------------------------------------------


class TestAcvTree:
    """Tests for the full AcvTree custom element implementation."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- tree-row elements ---

    def test_tree_row_class_present(self) -> None:
        assert "tree-row" in self.content, (
            "AcvTree must render elements with class 'tree-row'"
        )

    # --- expand/collapse triangles ---

    def test_expand_triangle_expanded(self) -> None:
        # ▾ (U+25BE) for expanded nodes
        assert "\u25be" in self.content or "▾" in self.content, (
            "AcvTree must show ▾ triangle for expanded nodes"
        )

    def test_collapse_triangle_collapsed(self) -> None:
        # ▸ (U+25B8) for collapsed nodes
        assert "\u25b8" in self.content or "▸" in self.content, (
            "AcvTree must show ▸ triangle for collapsed nodes"
        )

    # --- cost-bar inline bars ---

    def test_cost_bar_class_present(self) -> None:
        assert "cost-bar" in self.content, (
            "AcvTree must render a div with class 'cost-bar' for proportional cost display"
        )

    def test_cost_bar_opacity(self) -> None:
        assert "0.4" in self.content, (
            "AcvTree cost-bar must use opacity 0.4 for the accent color"
        )

    # --- total_cost_usd display ---

    def test_total_cost_usd_used(self) -> None:
        assert "total_cost_usd" in self.content, (
            "AcvTree must read total_cost_usd from session nodes"
        )

    # --- session-cost element ---

    def test_session_cost_class_present(self) -> None:
        assert "session-cost" in self.content, (
            "AcvTree must render span with class 'session-cost' showing cost·tokens"
        )

    # --- toggle-expand custom event ---

    def test_dispatches_toggle_expand_event(self) -> None:
        assert "toggle-expand" in self.content, (
            "AcvTree #onRowClick must dispatch 'toggle-expand' CustomEvent for nodes with children"
        )

    # --- session-select custom event ---

    def test_dispatches_session_select_event(self) -> None:
        assert "session-select" in self.content, (
            "AcvTree #onRowClick must dispatch 'session-select' CustomEvent"
        )

    # --- expandedSessions usage ---

    def test_uses_expanded_sessions(self) -> None:
        assert "expandedSessions" in self.content, (
            "AcvTree must use state.expandedSessions to track expanded nodes"
        )

    # --- session-label class ---

    def test_session_label_class_present(self) -> None:
        assert "session-label" in self.content, (
            "AcvTree must render a span with class 'session-label'"
        )

    def test_session_label_shows_name_or_agent_name(self) -> None:
        # session-label shows name||agent_name||shortId
        assert "agent_name" in self.content, (
            "AcvTree session-label must display name or agent_name or shortId"
        )

    # --- recursive children handling with depth ---

    def test_handles_children_recursively(self) -> None:
        assert "children" in self.content, (
            "AcvTree must handle children nodes recursively"
        )

    def test_depth_based_indentation(self) -> None:
        assert "depth" in self.content, (
            "AcvTree must use depth parameter for indentation"
        )

    def test_depth_uses_12px_per_level(self) -> None:
        # depth * 12px indentation
        assert "12" in self.content, (
            "AcvTree must indent tree rows by depth * 12px"
        )

    # --- #styles() private method ---

    def test_styles_method_defined(self) -> None:
        assert "#styles" in self.content, (
            "AcvTree must define private #styles() method for shadow DOM CSS"
        )

    # --- update() public method ---

    def test_update_method_defined(self) -> None:
        assert "update()" in self.content, (
            "AcvTree must define update() method to render from sessionData"
        )

    # --- #maxCostOf() private method ---

    def test_max_cost_of_method_defined(self) -> None:
        assert "maxCostOf" in self.content, (
            "AcvTree must define #maxCostOf(node) to compute max cost across root and children"
        )

    # --- #flatten() recursive private method ---

    def test_flatten_method_defined(self) -> None:
        assert "#flatten" in self.content, (
            "AcvTree must define private #flatten() recursive method for building tree rows"
        )

    # --- .toggle class with 14px width ---

    def test_toggle_class_with_width(self) -> None:
        assert ".toggle" in self.content, (
            "AcvTree styles must define .toggle class with 14px width"
        )

    # --- active class for selected row ---

    def test_active_class_for_selected_row(self) -> None:
        assert "active" in self.content, (
            "AcvTree must apply 'active' class to the currently selected session row"
        )

    # --- host styles ---

    def test_host_has_border_right(self) -> None:
        assert "border-right" in self.content, (
            "AcvTree :host must have border-right style"
        )

    def test_host_has_monospace_font(self) -> None:
        assert "monospace" in self.content, (
            "AcvTree :host must use monospace font"
        )

    def test_host_background_color(self) -> None:
        assert "#161b22" in self.content, (
            "AcvTree :host must set background to #161b22"
        )

    # --- toggle-expand wired in init() ---

    def test_toggle_expand_wired_in_init(self) -> None:
        # init() must wire toggle-expand event to toggle expandedSessions
        assert "toggle-expand" in self.content, (
            "init() must wire 'toggle-expand' event listener on acv-tree"
        )

    # --- session-select wired in init() ---

    def test_session_select_wired_in_init(self) -> None:
        # init() must wire session-select event to call renderAll()
        assert "session-select" in self.content, (
            "init() must wire 'session-select' event listener on acv-tree"
        )


# ---------------------------------------------------------------------------
# Tests: AcvTimeline — full implementation (heatmap + ruler + canvas)
# ---------------------------------------------------------------------------


class TestAcvTimeline:
    """Tests for the full AcvTimeline custom element implementation."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- Helper functions ---

    def test_visible_rows_helper_defined(self) -> None:
        assert "_visibleRows" in self.content, (
            "Must define '_visibleRows(node, expanded)' helper"
        )

    def test_row_index_map_helper_defined(self) -> None:
        assert "_rowIndexMap" in self.content, (
            "Must define '_rowIndexMap(sessionData, expanded)' helper"
        )

    # --- Private fields ---

    def test_canvas_private_field(self) -> None:
        assert "#canvas" in self.content, (
            "AcvTimeline must have '#canvas' private field"
        )

    def test_ctx_private_field(self) -> None:
        assert "#ctx" in self.content, (
            "AcvTimeline must have '#ctx' private field"
        )

    def test_raf_id_private_field(self) -> None:
        assert "#rafId" in self.content, (
            "AcvTimeline must have '#rafId' private field"
        )

    # --- connectedCallback and update ---

    def test_connected_callback_calls_update(self) -> None:
        # connectedCallback must call update()
        assert "connectedCallback" in self.content, (
            "AcvTimeline must define connectedCallback"
        )

    def test_update_method_defined(self) -> None:
        assert "update()" in self.content, (
            "AcvTimeline must define update() method"
        )

    # --- data setter ---

    def test_data_setter_defined(self) -> None:
        assert "set data(" in self.content, (
            "AcvTimeline must define a 'data' setter"
        )

    # --- Private methods ---

    def test_ensure_canvas_method_defined(self) -> None:
        assert "#ensureCanvas" in self.content, (
            "AcvTimeline must define '#ensureCanvas()' private method"
        )

    def test_resize_canvas_method_defined(self) -> None:
        assert "#resizeCanvas" in self.content, (
            "AcvTimeline must define '#resizeCanvas()' private method"
        )

    def test_draw_method_defined(self) -> None:
        assert "#draw" in self.content, (
            "AcvTimeline must define '#draw()' private method"
        )

    def test_render_heatmap_method_defined(self) -> None:
        assert "#renderHeatmap" in self.content, (
            "AcvTimeline must define '#renderHeatmap()' private method"
        )

    def test_render_ruler_method_defined(self) -> None:
        assert "#renderRuler" in self.content, (
            "AcvTimeline must define '#renderRuler()' private method"
        )

    def test_on_ruler_wheel_method_defined(self) -> None:
        assert "#onRulerWheel" in self.content, (
            "AcvTimeline must define '#onRulerWheel' event handler"
        )

    def test_on_canvas_click_method_defined(self) -> None:
        assert "#onCanvasClick" in self.content, (
            "AcvTimeline must define '#onCanvasClick' stub"
        )

    # --- Canvas element ---

    def test_canvas_element_rendered(self) -> None:
        assert "<canvas" in self.content, (
            "AcvTimeline update() must render a <canvas> element"
        )

    # --- Heatmap ---

    def test_heatmap_div_rendered(self) -> None:
        assert "heatmap" in self.content, (
            "AcvTimeline must render a heatmap div"
        )

    def test_heatmap_uses_anthropic_purple(self) -> None:
        assert "rgba(123,47,190" in self.content or "rgba(123, 47, 190" in self.content, (
            "AcvTimeline heatmap must use Anthropic purple rgba(123,47,190,...)"
        )

    def test_heatmap_height_20px(self) -> None:
        assert "20px" in self.content, (
            "AcvTimeline #heatmap must have 20px height"
        )

    def test_heatmap_peak_amber_border(self) -> None:
        # amber border for peak bucket
        assert "amber" in self.content or "#f59e0b" in self.content or "ffa" in self.content.lower() or "ffb" in self.content.lower(), (
            "AcvTimeline #renderHeatmap must mark peak bucket with amber border"
        )

    # --- Ruler ---

    def test_ruler_div_rendered(self) -> None:
        assert "ruler" in self.content, (
            "AcvTimeline must render a ruler div"
        )

    def test_ruler_height_28px(self) -> None:
        assert "28px" in self.content, (
            "AcvTimeline #ruler must have 28px height"
        )

    def test_ruler_has_border_bottom(self) -> None:
        assert "border-bottom" in self.content, (
            "AcvTimeline #ruler must have border-bottom"
        )

    def test_ruler_tick_interval_5000(self) -> None:
        assert "5000" in self.content, (
            "AcvTimeline #renderRuler must include 5000ms tick interval"
        )

    def test_ruler_tick_interval_30000(self) -> None:
        assert "30000" in self.content, (
            "AcvTimeline #renderRuler must include 30000ms tick interval"
        )

    def test_ruler_tick_interval_60000(self) -> None:
        assert "60000" in self.content, (
            "AcvTimeline #renderRuler must include 60000ms tick interval"
        )

    def test_tick_class_absolute_positioned(self) -> None:
        assert ".tick" in self.content, (
            "AcvTimeline must have .tick class with absolute positioning"
        )

    def test_tick_line_class(self) -> None:
        assert "tick-line" in self.content, (
            "AcvTimeline must have .tick-line class (1px wide, 8px tall)"
        )

    def test_tick_label_class(self) -> None:
        assert "tick-label" in self.content, (
            "AcvTimeline must have .tick-label class (10px font)"
        )

    # --- DPR scaling ---

    def test_device_pixel_ratio_used(self) -> None:
        assert "devicePixelRatio" in self.content, (
            "AcvTimeline #resizeCanvas must use devicePixelRatio for DPR scaling"
        )

    # --- RAF debouncing ---

    def test_request_animation_frame_used(self) -> None:
        assert "requestAnimationFrame" in self.content, (
            "AcvTimeline must use requestAnimationFrame for RAF debouncing"
        )

    # --- Wheel event ---

    def test_wheel_event_handler(self) -> None:
        assert "wheel" in self.content, (
            "AcvTimeline ruler must have @wheel handler for cursor-centered zoom"
        )

    def test_wheel_prevent_default(self) -> None:
        assert "preventDefault" in self.content, (
            "AcvTimeline #onRulerWheel must call preventDefault()"
        )

    def test_wheel_ms_at_cursor(self) -> None:
        assert "msAtCursor" in self.content, (
            "AcvTimeline #onRulerWheel must compute msAtCursor for cursor-centered zoom"
        )

    # --- Canvas-wrap ---

    def test_canvas_wrap_div(self) -> None:
        assert "canvas-wrap" in self.content, (
            "AcvTimeline must render #canvas-wrap div"
        )

    # --- Draw placeholder ---

    def test_draw_clears_to_dark_background(self) -> None:
        assert "#0d1117" in self.content, (
            "AcvTimeline #draw() must clear canvas to #0d1117 background"
        )

    def test_draw_shows_no_spans_message(self) -> None:
        assert "No spans" in self.content, (
            "AcvTimeline #draw() must show 'No spans' message when empty"
        )

    # --- Keyboard shortcuts ---

    def test_keyboard_shortcut_zoom_in_key_w(self) -> None:
        assert "KeyW" in self.content or "'w'" in self.content or '"w"' in self.content, (
            "init() must wire W key for zoom in"
        )

    def test_keyboard_shortcut_zoom_out_key_s(self) -> None:
        assert "KeyS" in self.content or "'s'" in self.content or '"s"' in self.content, (
            "init() must wire S key for zoom out"
        )

    def test_keyboard_shortcut_pan_left_key_a(self) -> None:
        assert "KeyA" in self.content or "ArrowLeft" in self.content, (
            "init() must wire A/ArrowLeft key for pan left"
        )

    def test_keyboard_shortcut_pan_right_key_d(self) -> None:
        assert "KeyD" in self.content or "ArrowRight" in self.content, (
            "init() must wire D/ArrowRight key for pan right"
        )

    def test_keyboard_shortcut_escape(self) -> None:
        assert "Escape" in self.content, (
            "init() must wire Escape key to clear selectedSpan"
        )

    def test_keyboard_shortcut_shift_modifier(self) -> None:
        assert "shiftKey" in self.content or "Shift" in self.content, (
            "init() keyboard shortcuts must support Shift modifier for 3x speed"
        )

    def test_keyboard_skips_input_elements(self) -> None:
        content = self.content
        assert "INPUT" in content or "SELECT" in content or "TEXTAREA" in content, (
            "init() keyboard handler must skip when target is INPUT/SELECT/TEXTAREA"
        )


# ---------------------------------------------------------------------------
# Tests: Canvas Gantt — color-batched span drawing + visibility culling
# ---------------------------------------------------------------------------


class TestCanvasDraw:
    """Tests for the #draw() canvas Gantt implementation in AcvTimeline."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- clearRect ---

    def test_draw_calls_clear_rect(self) -> None:
        assert "clearRect" in self.content, (
            "#draw() must call clearRect to clear the canvas before drawing"
        )

    # --- Alternating row backgrounds ---

    def test_draw_alternating_row_even_background(self) -> None:
        assert "#0d1117" in self.content, (
            "#draw() must use #0d1117 for even row backgrounds"
        )

    def test_draw_alternating_row_odd_background(self) -> None:
        assert "#161b22" in self.content, (
            "#draw() must use #161b22 for odd row backgrounds"
        )

    # --- Color-batched drawing ---

    def test_draw_uses_begin_path(self) -> None:
        assert "beginPath" in self.content, (
            "#draw() color-batched drawing must call beginPath() per color batch"
        )

    def test_draw_uses_fill_for_batches(self) -> None:
        assert "fill()" in self.content, (
            "#draw() color-batched drawing must call fill() to paint each color batch"
        )

    def test_draw_batches_by_color_map(self) -> None:
        # Batching uses a Map<color, rects[]> structure
        assert "Map" in self.content, (
            "#draw() must use a Map to batch spans by color"
        )

    # --- Text labels on wide spans ---

    def test_draw_uses_fill_text(self) -> None:
        assert "fillText" in self.content, (
            "#draw() must call fillText() to draw text labels on wide spans"
        )

    def test_draw_checks_width_for_text_label(self) -> None:
        # Must check width > 60px before drawing text
        assert "60" in self.content, (
            "#draw() must check span width > 60px before drawing text label"
        )

    def test_draw_text_label_uses_max_width(self) -> None:
        # fillText maxWidth = w - 8
        assert "maxWidth" in self.content or "w - 8" in self.content or "w-8" in self.content, (
            "#draw() fillText must use maxWidth to truncate text labels"
        )

    # --- Visibility culling ---

    def test_draw_culls_off_screen_spans(self) -> None:
        # Cull condition: x + w < -10 or x > cw + 10
        content = self.content
        assert "continue" in content, (
            "#draw() must use 'continue' to skip off-screen spans (visibility culling)"
        )

    def test_draw_cull_left_boundary(self) -> None:
        # x + w < -10
        assert "-10" in self.content, (
            "#draw() must cull spans where x + w < -10 (off screen left)"
        )

    # --- Grid lines ---

    def test_draw_draws_grid_lines(self) -> None:
        assert "strokeStyle" in self.content, (
            "#draw() must set strokeStyle for vertical grid lines"
        )

    def test_draw_grid_line_color(self) -> None:
        assert "#21262d" in self.content, (
            "#draw() grid lines must use #21262d stroke color"
        )

    def test_draw_calls_stroke(self) -> None:
        assert "stroke()" in self.content, (
            "#draw() must call stroke() to draw grid lines"
        )

    # --- ROW_H and SPAN_H constants ---

    def test_row_h_constant_defined(self) -> None:
        assert "ROW_H" in self.content, (
            "Must define ROW_H constant for row height"
        )

    def test_span_h_constant_defined(self) -> None:
        assert "SPAN_H" in self.content, (
            "Must define SPAN_H constant for span bar height"
        )

    # --- _rowIndexMap / _visibleRows ---

    def test_draw_uses_row_index_map(self) -> None:
        assert "_rowIndexMap" in self.content, (
            "#draw() must call _rowIndexMap() to build session-row mapping"
        )

    def test_draw_uses_visible_rows(self) -> None:
        assert "_visibleRows" in self.content, (
            "_rowIndexMap must use _visibleRows() to enumerate visible rows"
        )

    # --- Minimum 2px span width ---

    def test_draw_enforces_min_2px_width(self) -> None:
        content = self.content
        assert "Math.max(2" in content or "Math.max( 2" in content, (
            "#draw() must enforce minimum 2px span width with Math.max(2, ...)"
        )

    # --- Fallback color ---

    def test_draw_has_fallback_color(self) -> None:
        content = self.content
        assert "#64748B" in content or "#64748b" in content, (
            "#draw() must use '#64748B' as fallback span color"
        )

    # --- span.color usage ---

    def test_draw_uses_span_color(self) -> None:
        assert "span.color" in self.content, (
            "#draw() must read span.color to get the span's color"
        )

    # --- rowMap skip collapsed ---

    def test_draw_skips_undefined_rows(self) -> None:
        # skip if rowMap lookup is undefined (collapsed session)
        content = self.content
        assert "undefined" in content or "=== undefined" in content or "rowMap.get" in content, (
            "#draw() must skip spans whose session is not in rowMap (collapsed)"
        )

    # --- Canvas click / span-select ---

    def test_on_canvas_click_dispatches_span_select(self) -> None:
        assert "span-select" in self.content, (
            "#onCanvasClick must dispatch 'span-select' CustomEvent on hit span"
        )

    def test_init_wires_span_select(self) -> None:
        # init() wires span-select → sets state.selectedSpan and calls renderAll()
        assert "span-select" in self.content, (
            "init() must wire 'span-select' event to set state.selectedSpan and call renderAll()"
        )

    def test_init_sets_selected_span_on_span_select(self) -> None:
        assert "state.selectedSpan" in self.content, (
            "span-select handler must set state.selectedSpan"
        )

    # --- LLM span labels ---

    def test_draw_llm_span_label_uses_model(self) -> None:
        # LLM spans show model·cost
        content = self.content
        assert "model" in content, (
            "#draw() must show model name in text labels for LLM spans"
        )

    def test_draw_tool_span_label_uses_tool_name(self) -> None:
        assert "tool_name" in self.content, (
            "#draw() must show tool_name in text labels for tool spans"
        )
