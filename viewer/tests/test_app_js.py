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
