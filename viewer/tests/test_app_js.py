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

import pytest
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
        assert "selectedSpan" in self.content, "state must have 'selectedSpan' property"

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
        assert "init" in self.content, "DOMContentLoaded listener must call init"


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
        assert "resp.ok" in self.content, "fetchSessions must check resp.ok"

    def test_fetch_sessions_throws_on_error(self) -> None:
        assert "throw new Error" in self.content, (
            "fetchSessions must throw on HTTP error"
        )

    def test_fetch_sessions_appends_on_offset(self) -> None:
        content = self.content
        assert any(
            pattern in content
            for pattern in [
                "...state.sessions",
                "state.sessions.push",
                "state.sessions.concat",
            ]
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
        assert "/spans" in self.content, "fetchSpans must call /spans endpoint"

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
        assert "function _formatMs" in self.content, "Must define 'function _formatMs'"

    def test_format_ms_uses_to_fixed_1(self) -> None:
        assert "toFixed(1)" in self.content, (
            "_formatMs must use toFixed(1) for formatting"
        )

    def test_format_ms_has_seconds_unit(self) -> None:
        content = self.content
        assert (
            "'s'" in content
            or '"s"' in content
            or "`s`" in content
            or "/ 1000" in content
        ), "_formatMs must handle seconds unit"

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
        assert "Today" in self.content, "_formatDate must handle 'Today' case"

    def test_format_date_handles_yesterday(self) -> None:
        assert "Yesterday" in self.content, "_formatDate must handle 'Yesterday' case"

    def test_esc_defined(self) -> None:
        assert "function _esc" in self.content, "Must define 'function _esc'"

    def test_esc_escapes_amp(self) -> None:
        assert "&amp;" in self.content, "_esc must escape & as &amp;"

    def test_esc_escapes_lt(self) -> None:
        assert "&lt;" in self.content, "_esc must escape < as &lt;"


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
        assert "<select" in self.content, "AcvToolbar must render a <select> element"

    def test_renders_option(self) -> None:
        assert "<option" in self.content, "AcvToolbar must render <option> elements"

    def test_has_load_more_sentinel(self) -> None:
        assert "__load_more__" in self.content, (
            "AcvToolbar must include __load_more__ sentinel option"
        )

    def test_dispatches_session_change_event(self) -> None:
        assert "session-change" in self.content, (
            "AcvToolbar must dispatch session-change CustomEvent"
        )

    def test_dispatches_zoom_in_event(self) -> None:
        assert "zoom-in" in self.content, "AcvToolbar must dispatch zoom-in CustomEvent"

    def test_dispatches_zoom_out_event(self) -> None:
        assert "zoom-out" in self.content, (
            "AcvToolbar must dispatch zoom-out CustomEvent"
        )

    def test_dispatches_refresh_event(self) -> None:
        assert "CustomEvent" in self.content, (
            "AcvToolbar must use CustomEvent for dispatching"
        )
        assert "dispatchEvent" in self.content, "AcvToolbar must call dispatchEvent"

    def test_shows_total_cost(self) -> None:
        assert "totalCost" in self.content, "AcvToolbar must show totalCost"

    def test_shows_ms_px_zoom_label(self) -> None:
        assert "ms/px" in self.content, "AcvToolbar must show ms/px zoom label"


# ---------------------------------------------------------------------------
# Tests: init wiring
# ---------------------------------------------------------------------------


class TestInitWiring:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_render_all_defined(self) -> None:
        assert "function renderAll" in self.content, "Must define 'function renderAll'"

    def test_load_session_sets_active_session_id(self) -> None:
        assert "state.activeSessionId" in self.content, (
            "loadSession must set state.activeSessionId"
        )

    def test_load_session_calls_fetch_session(self) -> None:
        assert "fetchSession(" in self.content, "loadSession must call fetchSession"

    def test_load_session_calls_fetch_spans(self) -> None:
        assert "fetchSpans(" in self.content, "loadSession must call fetchSpans"

    def test_load_session_computes_time_scale(self) -> None:
        assert "state.timeScale" in self.content, (
            "loadSession must compute state.timeScale"
        )

    def test_init_fetches_sessions(self) -> None:
        assert "fetchSessions" in self.content, "init must call fetchSessions"

    def test_init_loads_first_session(self) -> None:
        assert "sessions[0]" in self.content, "init must load sessions[0]"

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
        assert "zoom-in" in self.content, "init must wire zoom-in event listener"

    def test_wires_zoom_out_event(self) -> None:
        assert "zoom-out" in self.content, "init must wire zoom-out event listener"

    def test_wires_refresh_event(self) -> None:
        assert "refresh" in self.content, "init must wire refresh event listener"

    def test_calls_api_refresh(self) -> None:
        assert "/api/refresh" in self.content, "refresh handler must call /api/refresh"


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
        assert "12" in self.content, "AcvTree must indent tree rows by depth * 12px"

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
        assert "monospace" in self.content, "AcvTree :host must use monospace font"

    def test_host_background_color(self) -> None:
        assert "#161b22" in self.content, "AcvTree :host must set background to #161b22"

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
        assert "#ctx" in self.content, "AcvTimeline must have '#ctx' private field"

    def test_raf_id_private_field(self) -> None:
        assert "#rafId" in self.content, "AcvTimeline must have '#rafId' private field"

    # --- connectedCallback and update ---

    def test_connected_callback_calls_update(self) -> None:
        # connectedCallback must call update()
        assert "connectedCallback" in self.content, (
            "AcvTimeline must define connectedCallback"
        )

    def test_update_method_defined(self) -> None:
        assert "update()" in self.content, "AcvTimeline must define update() method"

    # --- data setter ---

    def test_data_setter_defined(self) -> None:
        assert "set data(" in self.content, "AcvTimeline must define a 'data' setter"

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
        assert "heatmap" in self.content, "AcvTimeline must render a heatmap div"

    def test_heatmap_uses_anthropic_purple(self) -> None:
        assert (
            "rgba(123,47,190" in self.content or "rgba(123, 47, 190" in self.content
        ), "AcvTimeline heatmap must use Anthropic purple rgba(123,47,190,...)"

    def test_heatmap_height_20px(self) -> None:
        assert "20px" in self.content, "AcvTimeline #heatmap must have 20px height"

    def test_heatmap_peak_amber_border(self) -> None:
        # amber border for peak bucket
        assert (
            "amber" in self.content
            or "#f59e0b" in self.content
            or "ffa" in self.content.lower()
            or "ffb" in self.content.lower()
        ), "AcvTimeline #renderHeatmap must mark peak bucket with amber border"

    # --- Ruler ---

    def test_ruler_div_rendered(self) -> None:
        assert "ruler" in self.content, "AcvTimeline must render a ruler div"

    def test_ruler_height_28px(self) -> None:
        assert "28px" in self.content, "AcvTimeline #ruler must have 28px height"

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
        assert "canvas-wrap" in self.content, "AcvTimeline must render #canvas-wrap div"

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
        assert (
            "KeyW" in self.content or "'w'" in self.content or '"w"' in self.content
        ), "init() must wire W key for zoom in"

    def test_keyboard_shortcut_zoom_out_key_s(self) -> None:
        assert (
            "KeyS" in self.content or "'s'" in self.content or '"s"' in self.content
        ), "init() must wire S key for zoom out"

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
        assert "Map" in self.content, "#draw() must use a Map to batch spans by color"

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
        assert (
            "maxWidth" in self.content
            or "w - 8" in self.content
            or "w-8" in self.content
        ), "#draw() fillText must use maxWidth to truncate text labels"

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
        assert "ROW_H" in self.content, "Must define ROW_H constant for row height"

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
        assert (
            "undefined" in content
            or "=== undefined" in content
            or "rowMap.get" in content
        ), "#draw() must skip spans whose session is not in rowMap (collapsed)"

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


# ---------------------------------------------------------------------------
# Tests: AcvDetail — span detail panel with I/O display
# ---------------------------------------------------------------------------


class TestAcvDetail:
    """Tests for the full AcvDetail custom element implementation."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- IO_TRUNCATE constant ---

    def test_io_truncate_constant_defined(self) -> None:
        assert "IO_TRUNCATE" in self.content, (
            "Must define IO_TRUNCATE constant for I/O truncation"
        )

    def test_io_truncate_value_500(self) -> None:
        assert (
            "IO_TRUNCATE = 500" in self.content or "IO_TRUNCATE=500" in self.content
        ), "IO_TRUNCATE must be set to 500 chars"

    # --- update() / hidden when null ---

    def test_update_renders_hidden_when_null(self) -> None:
        content = self.content
        # Must render hidden div (display:none or .hidden class) when span is null
        assert (
            "display:none" in content
            or "display: none" in content
            or ".hidden" in content
        ), "AcvDetail update() must render hidden/display:none when span is null"

    def test_update_uses_div_hidden(self) -> None:
        # The spec requires div.hidden with display:none
        assert "hidden" in self.content, (
            "AcvDetail update() must use 'hidden' class for null span state"
        )

    # --- #titleFor() method ---

    def test_title_for_method_defined(self) -> None:
        assert "#titleFor" in self.content, (
            "AcvDetail must define private #titleFor(span) method"
        )

    def test_title_for_returns_provider_model_for_llm(self) -> None:
        # For LLM spans, returns provider/model
        content = self.content
        assert "provider" in content, (
            "AcvDetail #titleFor must return provider/model for LLM spans"
        )

    def test_title_for_returns_tool_name_for_tool(self) -> None:
        # For tool spans, returns tool_name with checkmark/cross
        content = self.content
        assert "tool_name" in content, (
            "AcvDetail #titleFor must use tool_name for tool spans"
        )

    def test_title_for_tool_success_checkmark(self) -> None:
        # checkmark (U+2713) for successful tool
        assert "\u2713" in self.content or "checkmark" in self.content, (
            "AcvDetail #titleFor must show checkmark for successful tool spans"
        )

    def test_title_for_tool_failure_cross(self) -> None:
        # cross mark (U+2717) for failed tool
        assert "\u2717" in self.content or "cross" in self.content, (
            "AcvDetail #titleFor must show cross for failed tool spans"
        )

    def test_title_for_thinking_type_colored(self) -> None:
        # For thinking type, shows colored 'thinking' label
        assert "thinking" in self.content, (
            "AcvDetail #titleFor must handle 'thinking' span type"
        )

    # --- #statsBlock() method (replaces #timingRow / #llmRows / #toolRows) ---

    def test_timing_row_method_defined(self) -> None:
        # Updated: #timingRow replaced by #statsBlock; check for stats block or duration helper
        assert "#statsBlock" in self.content or "_formatDuration" in self.content, (
            "AcvDetail must define #statsBlock(span) or use _formatDuration for span durations"
        )

    def test_timing_row_uses_format_ms(self) -> None:
        # Updated: detail panel now uses _formatDuration (not _formatMs) for span durations
        assert "_formatDuration" in self.content, (
            "AcvDetail detail panel must use _formatDuration for span duration display"
        )

    def test_timing_row_shows_arrow_between_start_end(self) -> None:
        # Updated: detail panel now shows formatted duration via _formatDuration, not start→end arrow
        content = self.content
        assert "_formatDuration" in content, (
            "AcvDetail detail panel must use _formatDuration to show span durations"
        )

    # --- #llmRows() method ---

    def test_llm_rows_method_defined(self) -> None:
        # Updated: #llmRows replaced by #statsBlock; check for stats block or toLocaleString
        assert "#statsBlock" in self.content or "toLocaleString" in self.content, (
            "AcvDetail must define #statsBlock(span) or use toLocaleString for token counts"
        )

    def test_llm_rows_shows_input_tokens(self) -> None:
        assert "input_tokens" in self.content, (
            "AcvDetail #llmRows must show input_tokens"
        )

    def test_llm_rows_shows_output_tokens(self) -> None:
        assert "output_tokens" in self.content, (
            "AcvDetail #llmRows must show output_tokens"
        )

    def test_llm_rows_shows_cache_read_tokens_conditional(self) -> None:
        # cache_read_tokens shown conditionally (only when > 0 or present)
        assert "cache_read" in self.content, (
            "AcvDetail #llmRows must conditionally show cache_read tokens"
        )

    def test_llm_rows_shows_cache_write_tokens_conditional(self) -> None:
        # cache_write_tokens shown conditionally
        assert "cache_write" in self.content, (
            "AcvDetail #llmRows must conditionally show cache_write tokens"
        )

    def test_llm_rows_shows_cost_with_to_fixed_6(self) -> None:
        # Updated: cost_usd now shown with toFixed(4) ($X.XXXX format) via #statsBlock
        assert "toFixed(4)" in self.content or "toLocaleString" in self.content, (
            "AcvDetail #statsBlock must show cost_usd with toFixed(4) for $X.XXXX format"
        )

    # --- #toolRows() method ---

    def test_tool_rows_method_defined(self) -> None:
        # Updated: #toolRows replaced by #statsBlock; check for stats block method
        assert "#statsBlock" in self.content, (
            "AcvDetail must define private #statsBlock(span) method (replaces #toolRows)"
        )

    def test_tool_rows_shows_duration(self) -> None:
        # Updated: #toolRows replaced by #statsBlock; duration shown via _formatDuration
        assert "_formatDuration" in self.content, (
            "AcvDetail #statsBlock must show duration via _formatDuration helper"
        )

    def test_tool_rows_shows_success_indicator(self) -> None:
        # Success indicator checkmark or cross
        content = self.content
        assert "\u2713" in content or "success" in content, (
            "AcvDetail #toolRows must show success indicator"
        )

    # --- #contentBlock() method (replaces #ioBlock) ---

    def test_io_block_method_defined(self) -> None:
        # Updated: #ioBlock replaced by #contentBlock with smart content extraction
        assert "#contentBlock" in self.content, (
            "AcvDetail must define private #contentBlock(label, value, spanType) method"
        )

    def test_io_block_stringifies_non_string_values(self) -> None:
        # Non-string values are JSON.stringify'd
        assert "JSON.stringify" in self.content, (
            "AcvDetail #ioBlock must JSON.stringify non-string values"
        )

    def test_io_block_truncates_at_io_truncate(self) -> None:
        # Truncates at IO_TRUNCATE (500 chars)
        content = self.content
        assert "IO_TRUNCATE" in content and (
            "slice" in content or "substring" in content
        ), "AcvDetail #ioBlock must truncate content at IO_TRUNCATE chars"

    def test_io_block_slice_uses_io_truncate(self) -> None:
        # slice(0, IO_TRUNCATE) specifically
        content = self.content
        assert (
            "slice(0, IO_TRUNCATE)" in content or "slice(0,IO_TRUNCATE)" in content
        ), "AcvDetail #ioBlock must use slice(0, IO_TRUNCATE) for truncation"

    def test_io_block_adds_ellipsis_suffix(self) -> None:
        # ellipsis suffix for truncated content (U+2026)
        assert "\u2026" in self.content or "\\u2026" in self.content, (
            "AcvDetail #ioBlock must add ellipsis suffix to truncated content"
        )

    def test_io_block_has_show_more_button(self) -> None:
        # 'show more' button that replaces truncated text with full text
        content = self.content
        assert "show more" in content or "show-more" in content, (
            "AcvDetail #ioBlock must provide a 'show more' button for truncated content"
        )

    # --- Close button and #onClose ---

    def test_close_button_x_char(self) -> None:
        # close button with X/times character (U+2715 or U+00D7)
        content = self.content
        assert (
            "\u2715" in content or "\u00d7" in content or "close" in content.lower()
        ), "AcvDetail must render a close button"

    def test_on_close_method_defined(self) -> None:
        assert "#onClose" in self.content, (
            "AcvDetail must define private #onClose() method"
        )

    def test_on_close_dispatches_detail_close_event(self) -> None:
        assert "detail-close" in self.content, (
            "AcvDetail #onClose must dispatch 'detail-close' CustomEvent"
        )

    def test_on_close_event_bubbles_and_composed(self) -> None:
        # The detail-close event must bubble and be composed
        content = self.content
        assert "bubbles" in content and "composed" in content, (
            "AcvDetail #onClose 'detail-close' event must be bubbles:true and composed:true"
        )

    # --- Styles ---

    def test_hidden_class_display_none(self) -> None:
        # .hidden { display: none }
        content = self.content
        assert "display:none" in content or "display: none" in content, (
            "AcvDetail styles must have display:none for hidden state"
        )

    def test_panel_class_background(self) -> None:
        # .panel with background #161b22
        assert "#161b22" in self.content, (
            "AcvDetail .panel must have background #161b22"
        )

    def test_panel_class_max_height_40vh(self) -> None:
        # .panel with max-height 40vh
        assert "40vh" in self.content, "AcvDetail .panel must have max-height 40vh"

    def test_panel_class_overflow_y_auto(self) -> None:
        # .panel with overflow-y auto
        assert "overflow-y" in self.content, (
            "AcvDetail .panel must have overflow-y style"
        )

    def test_header_class_flex(self) -> None:
        # .header with display flex
        content = self.content
        assert "header" in content and "flex" in content, (
            "AcvDetail .header must use flex layout"
        )

    def test_grid_class_defined(self) -> None:
        # Updated: .grid replaced by .detail-stats with auto-fill grid layout
        assert "detail-stats" in self.content or ".grid" in self.content, (
            "AcvDetail must define .detail-stats (or .grid) CSS class with grid template columns"
        )

    def test_io_block_class_defined(self) -> None:
        # .io-block class
        assert "io-block" in self.content, "AcvDetail must define .io-block CSS class"

    def test_io_label_class_uppercase(self) -> None:
        # .io-label uppercase
        assert "io-label" in self.content, (
            "AcvDetail must define .io-label CSS class (uppercase)"
        )

    def test_io_content_pre_element(self) -> None:
        # .io-content pre with max-height 80px overflow
        assert "io-content" in self.content, (
            "AcvDetail must define .io-content class with pre element"
        )

    def test_show_more_accent_color(self) -> None:
        # .show-more link in accent color (#58a6ff or var(--accent))
        content = self.content
        assert "show-more" in content, (
            "AcvDetail must define .show-more CSS class in accent color"
        )

    # --- Wiring into AcvTimeline ---

    def test_acv_detail_element_in_timeline_update(self) -> None:
        # AcvTimeline update() must include <acv-detail in its shadow DOM
        assert "acv-detail" in self.content, (
            "AcvTimeline update() must include <acv-detail> element"
        )

    def test_on_detail_close_method_in_timeline(self) -> None:
        # AcvTimeline must define #onDetailClose method
        assert "#onDetailClose" in self.content, (
            "AcvTimeline must define #onDetailClose method"
        )

    def test_detail_close_wired_in_init(self) -> None:
        # init() wires detail-close event on timeline
        assert "detail-close" in self.content, (
            "init() must wire 'detail-close' event listener on timeline"
        )

    def test_detail_close_sets_selected_span_null(self) -> None:
        # detail-close handler sets state.selectedSpan = null
        assert "state.selectedSpan" in self.content, (
            "detail-close handler must set state.selectedSpan = null"
        )


# ---------------------------------------------------------------------------
# Tests: Tree-Canvas wiring — expand/collapse integrated with Canvas draw
# ---------------------------------------------------------------------------


class TestTreeCanvasWiring:
    """Verification tests for tree expand/collapse → canvas wiring.

    The toggle-expand event handler in init() updates state.expandedSessions,
    calls renderAll(), which triggers AcvTimeline.update() → #draw().
    #draw() calls _rowIndexMap(state.sessionData, state.expandedSessions) to
    build a session→rowIndex map, skipping collapsed session rows.
    """

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- toggle-expand wired in init ---

    def test_toggle_expand_wired_in_init(self) -> None:
        """init() must addEventListener for 'toggle-expand' on acv-tree."""
        content = self.content
        assert (
            "addEventListener('toggle-expand'" in content
            or 'addEventListener("toggle-expand"' in content
        ), "init() must wire 'toggle-expand' event listener on acv-tree"

    # --- expandedSessions.delete() called in toggle handler ---

    def test_expanded_sessions_delete_called(self) -> None:
        """toggle-expand handler calls expandedSessions.delete() to collapse a node."""
        assert "expandedSessions.delete(" in self.content, (
            "toggle-expand handler must call expandedSessions.delete() to collapse a node"
        )

    # --- expandedSessions.add() called in toggle handler ---

    def test_expanded_sessions_add_called(self) -> None:
        """toggle-expand handler calls expandedSessions.add() to expand a node."""
        assert "expandedSessions.add(" in self.content, (
            "toggle-expand handler must call expandedSessions.add() to expand a node"
        )

    # --- _visibleRows respects expanded via expanded.has() ---

    def test_visible_rows_uses_expanded_has(self) -> None:
        """_visibleRows calls expanded.has() to check if a node is expanded."""
        assert "expanded.has(" in self.content, (
            "_visibleRows must call expanded.has(session_id) to skip collapsed nodes"
        )

    # --- _rowIndexMap used in #draw with state.expandedSessions ---

    def test_draw_calls_row_index_map_with_expanded_sessions(self) -> None:
        """#draw() calls _rowIndexMap(state.sessionData, state.expandedSessions)."""
        assert (
            "_rowIndexMap(state.sessionData, state.expandedSessions)" in self.content
        ), (
            "#draw() must call _rowIndexMap(state.sessionData, state.expandedSessions) "
            "to build a session-row mapping that respects expand/collapse state"
        )

    # --- collapsed sessions skip drawing (row === undefined) ---

    def test_draw_skips_collapsed_sessions_undefined_check(self) -> None:
        """#draw() skips spans where rowMap.get() returns undefined (collapsed session)."""
        content = self.content
        # rowIdx === undefined is the collapsed-session guard in #draw
        assert "rowIdx === undefined" in content or "rowMap.get(" in content, (
            "#draw() must check that rowIdx !== undefined before drawing "
            "(collapsed sessions have no row, their spans must be skipped)"
        )

    # --- renderAll called after expandedSessions update ---

    def test_render_all_called_after_expanded_sessions_update(self) -> None:
        """toggle-expand handler updates expandedSessions then calls renderAll()."""
        content = self.content
        assert "expandedSessions" in content and "renderAll" in content, (
            "toggle-expand handler must update state.expandedSessions then call renderAll() "
            "so the canvas redraws immediately"
        )

    # --- renderAll passes expandedSessions through to #draw ---

    def test_draw_reads_state_expanded_sessions(self) -> None:
        """#draw() reads state.expandedSessions (passed via _rowIndexMap)."""
        assert "state.expandedSessions" in self.content, (
            "#draw() must read state.expandedSessions (passed to _rowIndexMap) "
            "so collapsed rows are omitted from the canvas"
        )

    # --- detail-close wired in init ---

    def test_detail_close_wired_in_init(self) -> None:
        """init() wires 'detail-close' event listener on acv-timeline."""
        content = self.content
        assert (
            "addEventListener('detail-close'" in content
            or 'addEventListener("detail-close"' in content
        ), "init() must wire 'detail-close' event listener on acv-timeline"

    # --- state.selectedSpan set on span-select ---

    def test_span_select_sets_state_selected_span(self) -> None:
        """span-select handler sets state.selectedSpan = e.detail.span."""
        assert "state.selectedSpan = e.detail.span" in self.content, (
            "span-select handler must set state.selectedSpan = e.detail.span"
        )


# ---------------------------------------------------------------------------
# Fixture for loading-indicator tests
# ---------------------------------------------------------------------------


@pytest.fixture
def app_js_code() -> str:
    return APP_JS.read_text()


# ---------------------------------------------------------------------------
# Tests: Loading indicator — spinner in toolbar + canvas overlay
# ---------------------------------------------------------------------------


def test_state_has_loading_field(app_js_code: str) -> None:
    """state object must have loading: false"""
    assert "loading: false" in app_js_code, "state must declare 'loading: false' field"


def test_loading_set_in_load_session(app_js_code: str) -> None:
    """loadSession must set state.loading = true before fetch"""
    assert "state.loading = true" in app_js_code, (
        "loadSession must set state.loading = true before fetching"
    )


def test_loading_cleared_in_finally(app_js_code: str) -> None:
    """loading must be cleared in a finally block"""
    assert "finally" in app_js_code, (
        "loadSession (or init) must use a finally block to clear loading"
    )
    assert "state.loading = false" in app_js_code, (
        "loading must be cleared with state.loading = false in a finally block"
    )


def test_spinner_css_in_toolbar(app_js_code: str) -> None:
    """AcvToolbar shadow DOM must contain .spinner CSS"""
    assert ".spinner" in app_js_code, (
        "AcvToolbar styles must define a .spinner CSS class"
    )
    assert "border-radius: 50%" in app_js_code, (
        "AcvToolbar .spinner must use border-radius: 50% to make a circle"
    )


def test_canvas_shows_loading_text(app_js_code: str) -> None:
    """timeline draw() must render Loading text when loading"""
    assert "Loading" in app_js_code, (
        "AcvTimeline #draw() must render 'Loading' text when loading"
    )
    assert (
        "this._loading" in app_js_code
        or "this.#loading" in app_js_code
        or "_loading" in app_js_code
    ), "AcvTimeline must track loading state via this._loading or this.#loading"


# ---------------------------------------------------------------------------
# Tests: Adaptive ruler ticks — Chrome DevTools style
# ---------------------------------------------------------------------------


def test_ruler_uses_adaptive_tick_interval(app_js_code: str) -> None:
    """Ruler must use NICE_INTERVALS array for adaptive tick selection."""
    assert "NICE_INTERVALS" in app_js_code, (
        "Ruler must use NICE_INTERVALS array (Chrome DevTools adaptive ticks) "
        "instead of a fixed sparse INTERVALS list"
    )


def test_ruler_label_formats_minutes(app_js_code: str) -> None:
    """_formatRulerLabel must exist for ruler-specific label formatting."""
    assert "_formatRulerLabel" in app_js_code, (
        "_formatRulerLabel function must exist to format ruler tick labels "
        "with ms/s/m/h units based on the active tick interval"
    )


def test_ruler_starts_from_visible_window(app_js_code: str) -> None:
    """Ruler tick computation must account for scrollLeft offset."""
    assert "scrollLeftMs" in app_js_code, (
        "Ruler must compute scrollLeftMs = scrollLeft * timeScale so ticks "
        "start from the visible window, not from t=0"
    )


# ---------------------------------------------------------------------------
# Tests: Drag-to-pan on the timeline canvas
# ---------------------------------------------------------------------------


def test_drag_pan_mousedown_handler(app_js_code: str) -> None:
    """Canvas must have drag-to-pan mousedown handler."""
    assert "mousedown" in app_js_code
    assert (
        "dragStartX" in app_js_code
        or "_dragStartX" in app_js_code
        or "dragstart" in app_js_code.lower()
    )


def test_drag_pan_mousemove_handler(app_js_code: str) -> None:
    """Canvas must have mousemove handler that updates scrollLeft."""
    assert "mousemove" in app_js_code
    assert "scrollLeft" in app_js_code


def test_drag_pan_stops_on_mouseleave(app_js_code: str) -> None:
    """Drag must stop on mouseleave to avoid stuck drag state."""
    assert "mouseleave" in app_js_code


# ---------------------------------------------------------------------------
# Tests: Cmd/Ctrl+scroll zoom on the gantt canvas
# ---------------------------------------------------------------------------


def test_canvas_ctrl_scroll_zoom(app_js_code: str) -> None:
    """Canvas must have a wheel listener that fires on ctrlKey/metaKey for zoom."""
    # Must have passive: false to prevent browser native zoom interference
    assert "passive: false" in app_js_code or "passive:false" in app_js_code, (
        "Canvas wheel listener must use { passive: false } to allow preventDefault() "
        "and suppress browser native zoom/scroll"
    )
    # Must check ctrlKey or metaKey
    assert "ctrlKey" in app_js_code, (
        "Canvas wheel listener must check e.ctrlKey for Ctrl+scroll (Windows/Linux)"
    )
    assert "metaKey" in app_js_code, (
        "Canvas wheel listener must check e.metaKey for Cmd+scroll (macOS)"
    )


# ---------------------------------------------------------------------------
# Tests: Vertical scroll sync — tree as scroll master, canvas as follower
# ---------------------------------------------------------------------------


def test_state_has_scroll_top(app_js_code: str) -> None:
    """state object must track vertical scroll offset."""
    assert "scrollTop: 0" in app_js_code, (
        "state must declare 'scrollTop: 0' to track vertical scroll offset"
    )


def test_canvas_subtracts_scroll_top(app_js_code: str) -> None:
    """Canvas draw must subtract scrollTop from row y positions."""
    assert "scrollTop" in app_js_code, "app.js must reference scrollTop"
    # The draw function must use vertical scroll offset
    assert (
        "- scrollTop" in app_js_code
        or "-scrollTop" in app_js_code
        or "state.scrollTop" in app_js_code
    ), (
        "#draw() must use scrollTop offset when computing row y positions "
        "(subtract scrollTop from rowIdx * ROW_H)"
    )


def test_tree_dispatches_scroll_to_state(app_js_code: str) -> None:
    """AcvTree must listen for scroll events and update state.scrollTop."""
    assert "state.scrollTop" in app_js_code, (
        "AcvTree must update state.scrollTop on scroll events"
    )
    assert "scroll" in app_js_code, (
        "AcvTree must add a 'scroll' event listener to sync vertical position"
    )


def test_canvas_vertical_wheel_routes_to_tree(app_js_code: str) -> None:
    """Canvas wheel handler must route vertical scroll to the tree element."""
    # The vertical wheel handler routes to tree's scrollTop
    assert "deltaY" in app_js_code, (
        "Canvas wheel handler must read e.deltaY for vertical scroll routing"
    )
    assert "scrollTop" in app_js_code, (
        "Canvas vertical wheel must update scrollTop to keep tree as scroll master"
    )


# ---------------------------------------------------------------------------
# Tests: Sidebar ruler gap (spacer div)
# ---------------------------------------------------------------------------


class TestTreeRulerSpacer:
    """AcvTree must render a spacer div to align rows with timeline canvas rows."""

    def test_ruler_h_constant_defined(self, app_js_code: str) -> None:
        """RULER_H constant must be defined in the constants block."""
        assert "RULER_H" in app_js_code, (
            "app.js must define a RULER_H constant for the ruler height (28px)"
        )

    def test_tree_has_ruler_spacer_class(self, app_js_code: str) -> None:
        """AcvTree must render a <div class='ruler-spacer'> before the rows."""
        assert "ruler-spacer" in app_js_code, (
            "AcvTree must include a 'ruler-spacer' div to offset tree rows "
            "by the ruler + heatmap height so they align with timeline canvas rows"
        )

    def test_ruler_spacer_uses_flex_shrink_zero(self, app_js_code: str) -> None:
        """The .ruler-spacer CSS must use flex-shrink: 0 so it doesn't collapse."""
        assert "flex-shrink: 0" in app_js_code or "flex-shrink:0" in app_js_code, (
            ".ruler-spacer must have 'flex-shrink: 0' so it keeps its height "
            "and doesn't collapse in a flex container"
        )


# ---------------------------------------------------------------------------
# Tests: Smooth Animated Zoom
# ---------------------------------------------------------------------------


class TestAnimatedZoom:
    """Zoom changes must animate over 100ms with ease-out cubic easing."""

    def test_animate_zoom_function_exists(self, app_js_code: str) -> None:
        """_animateZoom function must be defined in app.js."""
        assert "_animateZoom" in app_js_code, (
            "app.js must define an _animateZoom() function that interpolates "
            "state.timeScale over 100ms instead of jumping instantly"
        )

    def test_zoom_uses_ease_out(self, app_js_code: str) -> None:
        """_animateZoom must use ease-out cubic interpolation via 'eased' variable."""
        assert "eased" in app_js_code, (
            "app.js must use an 'eased' variable for t*(2-t) ease-out cubic "
            "interpolation inside _animateZoom"
        )

    def test_state_has_zoom_anim_raf(self, app_js_code: str) -> None:
        """The state object must have a _zoomAnimRaf field for tracking the RAF handle."""
        assert "_zoomAnimRaf" in app_js_code, (
            "state must include a '_zoomAnimRaf' field so in-flight zoom "
            "animations can be cancelled"
        )

    def test_zoom_animation_cancels_previous(self, app_js_code: str) -> None:
        """_animateZoom must cancel any in-flight animation before starting a new one."""
        assert "cancelAnimationFrame" in app_js_code, (
            "app.js must call cancelAnimationFrame() in _animateZoom to cancel "
            "any previously running zoom animation before starting a new one"
        )

    def test_zoom_animation_uses_performance_now(self, app_js_code: str) -> None:
        """_animateZoom must use performance.now() to track animation time."""
        assert "performance.now" in app_js_code, (
            "app.js must use performance.now() in _animateZoom to measure "
            "elapsed animation time accurately"
        )


# ---------------------------------------------------------------------------
# Tests: Canvas-rendered spend area graph (heatmap)
# ---------------------------------------------------------------------------


class TestHeatmapAreaGraph:
    """Verify the heatmap uses a Canvas-rendered filled area chart."""

    def setup_method(self) -> None:
        self.source = APP_JS.read_text()

    def test_heatmap_uses_canvas_element(self) -> None:
        """Heatmap must use <canvas id='heatmap-canvas'> instead of a div."""
        assert "heatmap-canvas" in self.source, (
            "AcvTimeline must render <canvas id='heatmap-canvas'> "
            "instead of <div id='heatmap'>"
        )

    def test_heatmap_has_gradient_fill(self) -> None:
        """Heatmap area chart must use createLinearGradient for the fill."""
        assert "createLinearGradient" in self.source, (
            "#renderHeatmap must use createLinearGradient to fill the area chart"
        )

    def test_heatmap_has_peak_marker(self) -> None:
        """Heatmap must mark the peak bucket with amber (#f59e0b)."""
        assert "f59e0b" in self.source, (
            "#renderHeatmap must draw an amber peak marker using colour #f59e0b"
        )

    def test_heatmap_uses_float64_buckets(self) -> None:
        """Cost bucketing must use Float64Array for numeric precision."""
        assert "Float64Array" in self.source, (
            "#renderHeatmap must bucket span costs using Float64Array"
        )

    def test_heatmap_uses_purple_gradient(self) -> None:
        """Gradient fill must use Anthropic purple (rgb 123, 47, 190)."""
        assert (
            "123, 47, 190" in self.source or "7b2fbe" in self.source.lower()
        ), (
            "#renderHeatmap gradient must use Anthropic purple "
            "rgba(123, 47, 190, ...) or hex #7b2fbe"
        )


# ---------------------------------------------------------------------------
# Tests: Detail panel formatting — formatted durations, tokens, content
# ---------------------------------------------------------------------------


class TestDetailPanelFormatting:
    """Tests for the beautiful detail panel helpers and layout."""

    def setup_method(self) -> None:
        self.source = APP_JS.read_text()

    def test_detail_has_format_duration_helper(self) -> None:
        """app.js must define _formatDuration() helper function."""
        assert "_formatDuration" in self.source, (
            "app.js must define _formatDuration() for human-readable durations "
            "(e.g. '342ms', '4.2s', '2m 15s')"
        )

    def test_detail_has_extract_content_helper(self) -> None:
        """app.js must define _extractContent() helper function."""
        assert "_extractContent" in self.source, (
            "app.js must define _extractContent() to extract readable text "
            "from string, message array, or tool-use shapes"
        )

    def test_detail_uses_locale_string_for_tokens(self) -> None:
        """Token counts must use .toLocaleString() for comma-separated formatting."""
        assert "toLocaleString" in self.source, (
            "app.js must call .toLocaleString() on token counts so large numbers "
            "are formatted with commas (e.g. 12,345 instead of 12345)"
        )

    def test_detail_has_render_tool_input_helper(self) -> None:
        """app.js must define _renderToolInput() helper function."""
        assert "_renderToolInput" in self.source, (
            "app.js must define _renderToolInput() to render tool input as "
            "'key: value' lines for objects, as-is for strings"
        )

    def test_detail_handles_tool_use_output(self) -> None:
        """_extractContent must handle tool_use type in content arrays."""
        assert "tool_use" in self.source, (
            "app.js must handle tool_use content type in _extractContent(), "
            "e.g. returning '[called: name]' for tool_use blocks"
        )

    def test_detail_panel_has_stats_grid(self) -> None:
        """Detail panel must use a stats grid layout class."""
        assert "detail-stats" in self.source or "stats-grid" in self.source, (
            "AcvDetail must use a .detail-stats or .stats-grid CSS class for "
            "a grid layout of span statistics"
        )

    def test_detail_panel_uses_pre_wrap(self) -> None:
        """Detail panel I/O content must use white-space: pre-wrap."""
        assert "pre-wrap" in self.source, (
            "AcvDetail I/O content blocks must use white-space: pre-wrap "
            "to preserve line breaks in content display"
        )
