"""Tests for app.js v2 — written FIRST before the file is rewritten (TDD RED).

Tests verify that app.js:
- Exists and has >500 chars
- Imports html/render from the local Lit vendor bundle
- Declares a const state object with the required properties
- Defines custom element classes (AcvToolbar, AcvBody, AcvOverview, AcvDetail)
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
INDEX_HTML = STATIC / "index.html"
CSS_FILE = STATIC / "style.css"


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

    def test_acv_detail_class_defined(self) -> None:
        assert "class AcvDetail" in self.content, (
            "Must define 'class AcvDetail' extending HTMLElement"
        )

    # --- Extend HTMLElement ---

    def test_acv_toolbar_extends_html_element(self) -> None:
        assert "AcvToolbar extends HTMLElement" in self.content, (
            "AcvToolbar must extend HTMLElement"
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

    def test_no_zoom_in_button(self) -> None:
        assert "_onZoomIn" not in self.content, (
            "AcvToolbar must NOT have _onZoomIn method (zoom controls removed in v3)"
        )

    def test_no_zoom_out_button(self) -> None:
        assert "_onZoomOut" not in self.content, (
            "AcvToolbar must NOT have _onZoomOut method (zoom controls removed in v3)"
        )

    def test_dispatches_refresh_event(self) -> None:
        assert "CustomEvent" in self.content, (
            "AcvToolbar must use CustomEvent for dispatching"
        )
        assert "dispatchEvent" in self.content, "AcvToolbar must call dispatchEvent"

    def test_shows_total_cost(self) -> None:
        assert "totalCost" in self.content, "AcvToolbar must show totalCost"


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

    def test_wires_refresh_event(self) -> None:
        assert "refresh" in self.content, "init must wire refresh event listener"

    def test_calls_api_refresh(self) -> None:
        assert "/api/refresh" in self.content, "refresh handler must call /api/refresh"


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
    """v3 loading model: state.loading drives toolbar spinner (canvas overlay removed)"""
    # Toolbar spinner uses aria-label="Loading" — Loading text still present in codebase
    assert "Loading" in app_js_code, (
        "Loading indicator must exist somewhere in the UI (e.g. toolbar spinner aria-label)"
    )
    # v3: loading is tracked via state.loading, not a per-component #loading field
    assert "state.loading" in app_js_code, (
        "Loading state must be tracked via state.loading in v3 architecture"
    )


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
# Tests: Detail panel formatting — formatted durations, tokens, content
# ---------------------------------------------------------------------------


class TestDetailPanelFormatting:
    """Tests for the beautiful detail panel helpers and layout."""

    def test_detail_has_format_duration_helper(self, app_js_code: str) -> None:
        """app.js must define _formatDuration() helper function."""
        assert "_formatDuration" in app_js_code, (
            "app.js must define _formatDuration() for human-readable durations "
            "(e.g. '342ms', '4.2s', '2m 15s')"
        )

    def test_detail_has_extract_content_helper(self, app_js_code: str) -> None:
        """app.js must define _extractContent() helper function."""
        assert "_extractContent" in app_js_code, (
            "app.js must define _extractContent() to extract readable text "
            "from string, message array, or tool-use shapes"
        )

    def test_detail_uses_locale_string_for_tokens(self, app_js_code: str) -> None:
        """Token counts must use .toLocaleString() for comma-separated formatting."""
        assert "toLocaleString" in app_js_code, (
            "app.js must call .toLocaleString() on token counts so large numbers "
            "are formatted with commas (e.g. 12,345 instead of 12345)"
        )

    def test_detail_has_render_tool_input_helper(self, app_js_code: str) -> None:
        """app.js must define _renderToolInput() helper function."""
        assert "_renderToolInput" in app_js_code, (
            "app.js must define _renderToolInput() to render tool input as "
            "'key: value' lines for objects, as-is for strings"
        )

    def test_detail_handles_tool_use_output(self, app_js_code: str) -> None:
        """_extractContent must handle tool_use type in content arrays."""
        assert "tool_use" in app_js_code, (
            "app.js must handle tool_use content type in _extractContent(), "
            "e.g. returning '[called: name]' for tool_use blocks"
        )

    def test_detail_panel_has_stats_grid(self, app_js_code: str) -> None:
        """Detail panel must use a stats grid layout class."""
        assert "detail-stats" in app_js_code or "stats-grid" in app_js_code, (
            "AcvDetail must use a .detail-stats or .stats-grid CSS class for "
            "a grid layout of span statistics"
        )

    def test_detail_panel_uses_pre_wrap(self, app_js_code: str) -> None:
        """Detail panel I/O content must use white-space: pre-wrap."""
        assert "pre-wrap" in app_js_code, (
            "AcvDetail I/O content blocks must use white-space: pre-wrap "
            "to preserve line breaks in content display"
        )


# ---------------------------------------------------------------------------
# Tests: v3 viewport state model
# ---------------------------------------------------------------------------


class TestV3StateModel:
    """Verify that v3 state fields and MIN_SPAN_MS constant are added."""

    def test_min_span_ms_constant(self, app_js_code: str) -> None:
        """MIN_SPAN_MS = 100 constant must be defined."""
        assert "MIN_SPAN_MS = 100" in app_js_code, (
            "app.js must define 'const MIN_SPAN_MS = 100' constant"
        )

    def test_state_has_total_duration_ms(self, app_js_code: str) -> None:
        """state must have totalDurationMs field initialised to 0."""
        assert "totalDurationMs" in app_js_code, (
            "state object must declare 'totalDurationMs' field"
        )

    def test_state_has_viewport_start_ms(self, app_js_code: str) -> None:
        """state must have viewportStartMs field initialised to 0."""
        assert "viewportStartMs" in app_js_code, (
            "state object must declare 'viewportStartMs' field"
        )

    def test_state_has_viewport_end_ms(self, app_js_code: str) -> None:
        """state must have viewportEndMs field initialised to 0."""
        assert "viewportEndMs" in app_js_code, (
            "state object must declare 'viewportEndMs' field"
        )

    def test_state_has_anim_raf(self, app_js_code: str) -> None:
        """state must have _animRaf field for viewport animation handle."""
        assert "_animRaf" in app_js_code, (
            "state object must declare '_animRaf' field (viewport animation RAF handle)"
        )


# ---------------------------------------------------------------------------
# Tests: v3 coordinate helpers
# ---------------------------------------------------------------------------


class TestV3CoordinateHelpers:
    """Verify timeToPixel, pixelToTime, msPerPx helper functions are defined."""

    def test_time_to_pixel_defined(self, app_js_code: str) -> None:
        """timeToPixel(ms, canvasW) must be defined."""
        assert "function timeToPixel" in app_js_code, (
            "app.js must define 'function timeToPixel(ms, canvasW)'"
        )

    def test_pixel_to_time_defined(self, app_js_code: str) -> None:
        """pixelToTime(px, canvasW) must be defined."""
        assert "function pixelToTime" in app_js_code, (
            "app.js must define 'function pixelToTime(px, canvasW)'"
        )

    def test_ms_per_px_defined(self, app_js_code: str) -> None:
        """msPerPx(canvasW) must be defined."""
        assert "function msPerPx" in app_js_code, (
            "app.js must define 'function msPerPx(canvasW)'"
        )


# ---------------------------------------------------------------------------
# Tests: v3 setViewport / _animateViewport
# ---------------------------------------------------------------------------


class TestV3SetViewport:
    """Verify setViewport and _animateViewport functions."""

    def test_set_viewport_defined(self, app_js_code: str) -> None:
        """setViewport(startMs, endMs, animate) must be defined."""
        assert "function setViewport" in app_js_code, (
            "app.js must define 'function setViewport'"
        )

    def test_animate_viewport_defined(self, app_js_code: str) -> None:
        """_animateViewport(targetStart, targetEnd) must be defined."""
        assert "function _animateViewport" in app_js_code, (
            "app.js must define 'function _animateViewport'"
        )

    def test_set_viewport_has_animate_param(self, app_js_code: str) -> None:
        """setViewport must accept an animate parameter defaulting to true."""
        assert "animate = true" in app_js_code or "animate=true" in app_js_code, (
            "setViewport must have 'animate = true' default parameter"
        )

    def test_animate_viewport_uses_ease_out_quad(self, app_js_code: str) -> None:
        """_animateViewport must use easeOutQuad easing."""
        assert "easeOutQuad" in app_js_code, (
            "_animateViewport must use easeOutQuad easing (comment or variable name)"
        )


# ---------------------------------------------------------------------------
# Tests: v3 _visibleRowsWithDepth
# ---------------------------------------------------------------------------


class TestV3VisibleRowsWithDepth:
    """Verify _visibleRowsWithDepth helper is defined."""

    def test_visible_rows_with_depth_defined(self, app_js_code: str) -> None:
        """_visibleRowsWithDepth(node, expanded) must be defined."""
        assert "function _visibleRowsWithDepth" in app_js_code, (
            "app.js must define 'function _visibleRowsWithDepth(node, expanded)' "
            "that returns {node, depth} objects for label indentation"
        )


# ---------------------------------------------------------------------------
# Tests: AcvOverview placeholder element
# ---------------------------------------------------------------------------


class TestV3AcvOverview:
    """Verify AcvOverview placeholder element is defined and registered."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_acv_overview_class_defined(self) -> None:
        """AcvOverview class must be defined extending HTMLElement."""
        assert "class AcvOverview" in self.content, (
            "app.js must define 'class AcvOverview' extending HTMLElement"
        )

    def test_acv_overview_custom_element_registered(self) -> None:
        """AcvOverview must be registered as 'acv-overview' custom element."""
        assert (
            "customElements.define('acv-overview'" in self.content
            or 'customElements.define("acv-overview"' in self.content
        ), "Must register acv-overview via customElements.define"

    def test_attach_shadow_count_gte_4(self) -> None:
        """All v3 custom element classes must call attachShadow (4 classes: AcvToolbar, AcvOverview, AcvBody, AcvDetail)."""
        count = self.content.count("attachShadow")
        assert count >= 4, (
            f"All 4 custom element classes must call attachShadow, found {count} calls"
        )


# ---------------------------------------------------------------------------
# Tests: AcvBody CSS Grid shell with labels
# ---------------------------------------------------------------------------


class TestV3AcvBody:
    """Verify AcvBody custom element — CSS Grid shell with labels column."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_acv_body_class_defined(self) -> None:
        """AcvBody class must be defined extending HTMLElement."""
        assert "class AcvBody" in self.content, (
            "app.js must define 'class AcvBody extends HTMLElement'"
        )

    def test_acv_body_custom_element_registered(self) -> None:
        """AcvBody must be registered as 'acv-body' custom element."""
        assert (
            "customElements.define('acv-body'" in self.content
            or 'customElements.define("acv-body"' in self.content
        ), "Must register acv-body via customElements.define"

    def test_label_column_width(self) -> None:
        """AcvBody must declare a 220px label column."""
        assert "220px" in self.content, (
            "AcvBody must declare a 220px wide label column (col.col-label or equivalent)"
        )

    def test_ruler_spans_full_width(self) -> None:
        """Ruler header row must span both columns via <thead>."""
        assert "<thead" in self.content, (
            "AcvBody must use <thead> so the ruler row spans the full table width"
        )

    def test_ruler_position_sticky(self) -> None:
        """Ruler wrapper must use position: sticky so it sticks to the top."""
        assert (
            "position: sticky" in self.content or "position:sticky" in self.content
        ), "AcvBody ruler wrapper must use 'position: sticky' to stay at top"

    def test_labels_column_present(self) -> None:
        """AcvBody must render a sticky left-column label cell."""
        assert "td-label" in self.content or "labels-column" in self.content or "label-col" in self.content, (
            "AcvBody must render label cells (class 'td-label', 'labels-column', or 'label-col')"
        )

    def test_canvas_column_present(self) -> None:
        """AcvBody must render a right-side canvas area."""
        assert "td-canvas" in self.content or "canvas-column" in self.content or "canvas-col" in self.content, (
            "AcvBody must render canvas column cells (class 'td-canvas', 'canvas-column', or 'canvas-col')"
        )

    def test_uses_visible_rows_with_depth(self) -> None:
        """AcvBody must call _visibleRowsWithDepth to render label rows."""
        assert "_visibleRowsWithDepth" in self.content, (
            "AcvBody must call _visibleRowsWithDepth(sessionData, expandedSessions) "
            "to build the visible rows with depth for indentation"
        )

    def test_toggle_triangles_present(self) -> None:
        """AcvBody must render ▾ for expanded and ▸ for collapsed nodes."""
        # These unicode chars are already in the file (used in AcvTree), but
        # AcvBody must also reference them. The test checks they appear in the
        # context of the AcvBody implementation.
        content = self.content
        assert "\u25be" in content or "▾" in content, (
            "AcvBody must render ▾ (U+25BE) for expanded nodes"
        )
        assert "\u25b8" in content or "▸" in content, (
            "AcvBody must render ▸ (U+25B8) for collapsed nodes"
        )

    def test_dispatches_toggle_expand_event(self) -> None:
        """AcvBody must dispatch 'toggle-expand' CustomEvent when a parent row is clicked."""
        content = self.content
        # Ensure toggle-expand appears — it already exists for AcvTree, but AcvBody
        # must also dispatch it (with bubbles:true, composed:true).
        assert "toggle-expand" in content, (
            "AcvBody must dispatch 'toggle-expand' CustomEvent on label row click "
            "when the node has children"
        )

    def test_dispatches_session_select_event(self) -> None:
        """AcvBody must dispatch 'session-select' CustomEvent on every row click."""
        assert "session-select" in self.content, (
            "AcvBody must dispatch 'session-select' CustomEvent on label row click"
        )

    def test_acv_detail_included_in_shadow_dom(self) -> None:
        """AcvBody shadow DOM must include <acv-detail> after the grid div."""
        assert "acv-detail" in self.content, (
            "AcvBody shadow DOM must include <acv-detail></acv-detail> after the grid div"
        )

    def test_scroll_top_tracking_on_grid(self) -> None:
        """AcvBody must track scrollTop on the .grid container and push to state."""
        content = self.content
        assert "state.scrollTop" in content, (
            "AcvBody connectedCallback must wire a scroll listener on the .grid container "
            "that sets state.scrollTop = grid.scrollTop"
        )
        assert "scrollTop" in content, (
            "AcvBody must track vertical scroll via scrollTop"
        )


# ---------------------------------------------------------------------------
# Tests: v3 HTML structure (index.html)
# ---------------------------------------------------------------------------


class TestV3HtmlStructure:
    """Verify index.html uses acv-overview + acv-body, not the old tree/timeline layout."""

    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()

    def test_has_acv_overview(self) -> None:
        assert "<acv-overview" in self.content, (
            "index.html must contain <acv-overview> element"
        )

    def test_has_acv_body(self) -> None:
        assert "<acv-body" in self.content, "index.html must contain <acv-body> element"

    def test_no_acv_tree(self) -> None:
        assert "<acv-tree" not in self.content, (
            "index.html must NOT contain <acv-tree> (moved to shadow DOM)"
        )

    def test_no_acv_timeline(self) -> None:
        assert "<acv-timeline" not in self.content, (
            "index.html must NOT contain <acv-timeline> (moved to shadow DOM)"
        )

    def test_no_main_tag(self) -> None:
        assert "<main" not in self.content, (
            "index.html must NOT contain <main> wrapper element"
        )


# ---------------------------------------------------------------------------
# Tests: v3 CSS layout (style.css)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tests: v3 loadSession - totalDurationMs and setViewport
# ---------------------------------------------------------------------------


class TestV3LoadSession:
    """Verify loadSession computes totalDurationMs and calls setViewport."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_load_session_computes_total_duration_ms(self) -> None:
        """loadSession must assign state.totalDurationMs from spans reduce."""
        assert "state.totalDurationMs" in self.content, (
            "loadSession must compute state.totalDurationMs from spans"
        )

    def test_load_session_calls_set_viewport(self) -> None:
        """loadSession must call setViewport(0, state.totalDurationMs, false)."""
        assert "setViewport(0," in self.content, (
            "loadSession must call setViewport(0, state.totalDurationMs, false)"
        )


# ---------------------------------------------------------------------------
# Tests: v3 init() wiring — events wired on acv-body (not acv-tree/acv-timeline)
# ---------------------------------------------------------------------------


class TestV3InitWiring:
    """Verify that init() wires body events on acv-body, not acv-tree/acv-timeline."""

    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_toggle_expand_wired_on_body(self) -> None:
        """init() must use querySelector('acv-body') and wire toggle-expand."""
        content = self.content
        assert (
            "querySelector('acv-body')" in content
            or 'querySelector("acv-body")' in content
        ), "init() must query for 'acv-body' element to wire toggle-expand"
        assert "toggle-expand" in content, "init() must wire toggle-expand event"

    def test_session_select_wired_on_body(self) -> None:
        """init() must use querySelector('acv-body') and wire session-select."""
        content = self.content
        assert (
            "querySelector('acv-body')" in content
            or 'querySelector("acv-body")' in content
        ), "init() must query for 'acv-body' element to wire session-select"
        assert "session-select" in content, "init() must wire session-select event"

    def test_detail_close_wired_on_body(self) -> None:
        """init() must use querySelector('acv-body') and wire detail-close."""
        content = self.content
        assert (
            "querySelector('acv-body')" in content
            or 'querySelector("acv-body")' in content
        ), "init() must query for 'acv-body' element to wire detail-close"
        assert "detail-close" in content, "init() must wire detail-close event"


# ---------------------------------------------------------------------------
# Tests: v3 CSS layout (style.css)
# ---------------------------------------------------------------------------


class TestV3CssLayout:
    """Verify style.css has acv-overview and acv-body rules with correct sizing."""

    def setup_method(self) -> None:
        self.content = CSS_FILE.read_text()

    def test_has_acv_overview(self) -> None:
        assert "acv-overview" in self.content, (
            "style.css must contain acv-overview layout rule"
        )

    def test_has_acv_body(self) -> None:
        assert "acv-body" in self.content, "style.css must contain acv-body layout rule"

    def test_has_60px(self) -> None:
        assert "60px" in self.content, (
            "style.css must contain 60px height rule for acv-overview"
        )


# ---------------------------------------------------------------------------
# Tests: Task 8 — AcvBody canvas drawing
# ---------------------------------------------------------------------------


class TestAcvBodyCanvas:
    """Verify AcvBody replaces placeholder divs with real canvas elements."""

    def test_main_canvas_in_template(self, app_js_code: str) -> None:
        assert "main-canvas" in app_js_code, (
            "AcvBody template must contain canvas id='main-canvas' "
            "instead of the .canvas-column placeholder div"
        )

    def test_ruler_canvas_in_template(self, app_js_code: str) -> None:
        assert "ruler-canvas" in app_js_code, (
            "AcvBody template must contain canvas id='ruler-canvas' "
            "instead of the .ruler-ticks placeholder div"
        )

    def test_draw_uses_time_to_pixel(self, app_js_code: str) -> None:
        assert "timeToPixel" in app_js_code, (
            "AcvBody #draw() must use timeToPixel() for coordinate conversion"
        )
        # Must NOT use old timeScale formula
        assert "ms / timeScale" not in app_js_code, (
            "AcvBody #draw() must NOT use the old 'ms / timeScale' formula"
        )

    def test_drag_pan_uses_set_viewport(self, app_js_code: str) -> None:
        assert "setViewport" in app_js_code, (
            "AcvBody canvas drag handler must call setViewport() to pan the viewport"
        )
        assert "dragStartViewportStart" in app_js_code or "dragStart" in app_js_code, (
            "AcvBody mousedown handler must store drag start position "
            "(dragStartViewportStart or similar)"
        )

    def test_ctrl_scroll_zoom_on_canvas(self, app_js_code: str) -> None:
        assert "ctrlKey" in app_js_code, (
            "AcvBody canvas wheel handler must check e.ctrlKey for Ctrl+scroll zoom"
        )
        assert "metaKey" in app_js_code, (
            "AcvBody canvas wheel handler must check e.metaKey for Cmd+scroll zoom (macOS)"
        )
        assert "passive: false" in app_js_code or "passive:false" in app_js_code, (
            "AcvBody canvas wheel listener must use { passive: false } "
            "to allow preventDefault()"
        )


# ---------------------------------------------------------------------------
# Fixture for CSS tests
# ---------------------------------------------------------------------------


@pytest.fixture
def css_code() -> str:
    return CSS_FILE.read_text()


# ---------------------------------------------------------------------------
# Tests: Bug fixes — display:flex + canvas height resize gate
# ---------------------------------------------------------------------------


def test_acv_body_display_flex(css_code: str) -> None:
    """acv-body must use display: flex to allow inner grid to be constrained."""
    import re

    match = re.search(r"acv-body\s*\{([^}]+)\}", css_code)
    assert match, "acv-body rule not found"
    rule = match.group(1)
    assert "display: flex" in rule or "display:flex" in rule, (
        "acv-body must use 'display: flex' (not display:block) so shadow DOM "
        ":host { display: flex } is not overridden and the inner grid is constrained"
    )


def test_canvas_resize_checks_both_dimensions(app_js_code: str) -> None:
    """Canvas resize must check height as well as width."""
    assert "needsMcResize" in app_js_code or "mc.height !== " in app_js_code, (
        "#ensureCanvases() must check BOTH mc.width AND mc.height when deciding "
        "whether to resize (use needsMcResize variable or 'mc.height !== ' check)"
    )


# ---------------------------------------------------------------------------
# Tests: HTML table layout (replaces CSS Grid hack in AcvBody)
# ---------------------------------------------------------------------------


def test_acv_body_uses_table(app_js_code: str) -> None:
    """AcvBody must use an HTML table, not a CSS grid."""
    assert "<table" in app_js_code, "AcvBody must render a <table> element"
    assert "<thead" in app_js_code, "AcvBody must render a <thead> element"
    assert "<tbody" in app_js_code, "AcvBody must render a <tbody> element"


def test_left_column_is_sticky(app_js_code: str) -> None:
    """Left column <td> must be position: sticky; left: 0."""
    assert "position: sticky" in app_js_code, (
        "AcvBody left column must use 'position: sticky'"
    )
    assert "left: 0" in app_js_code, (
        "AcvBody left column must use 'left: 0' for sticky positioning"
    )


def test_ruler_thead_sticky_top(app_js_code: str) -> None:
    """Ruler <thead> row must be position: sticky; top: 0."""
    assert "top: 0" in app_js_code, (
        "AcvBody ruler header must use 'top: 0' for sticky top positioning"
    )


def test_canvas_position_absolute_in_table_wrap(app_js_code: str) -> None:
    """Main canvas must be position: absolute inside the scrollable table-wrap."""
    assert "position: absolute" in app_js_code, (
        "AcvBody main-canvas must use 'position: absolute' to overlay the right column"
    )
    assert "table-wrap" in app_js_code, (
        "AcvBody must have a 'table-wrap' scroll container"
    )


def test_no_css_grid_in_acv_body(app_js_code: str) -> None:
    """AcvBody must NOT use CSS grid-template-columns: 220px (the old two-column grid hack)."""
    assert "grid-template-columns: 220px" not in app_js_code, (
        "AcvBody must NOT use 'grid-template-columns: 220px' — "
        "the CSS grid two-column approach has been replaced by an HTML table"
    )


# ---------------------------------------------------------------------------
# Tests: Canvas sizing — DOM measurement + ResizeObserver
# ---------------------------------------------------------------------------


def test_ensure_canvases_uses_getboundingclientrect(app_js_code: str) -> None:
    """Canvas sizing must measure actual DOM dimensions, not compute rows*ROW_H."""
    assert "getBoundingClientRect" in app_js_code


def test_resize_observer_watches_host_and_tbody(app_js_code: str) -> None:
    """ResizeObserver must observe both the host element and tbody."""
    assert "ResizeObserver" in app_js_code
    assert "#resizeObserver" in app_js_code or "_resizeObserver" in app_js_code


def test_canvas_dpr_scaling(app_js_code: str) -> None:
    """Canvas pixel buffer must be scaled by devicePixelRatio."""
    assert "devicePixelRatio" in app_js_code
    assert "dpr" in app_js_code


def test_disconnected_callback_cleans_up(app_js_code: str) -> None:
    """disconnectedCallback must disconnect ResizeObserver and cancel RAF."""
    assert "disconnectedCallback" in app_js_code
    assert "disconnect()" in app_js_code


# ---------------------------------------------------------------------------
# Tests: Pixel-accurate canvas positioning — measure actual row/thead height
# ---------------------------------------------------------------------------


def test_actual_row_height_field(app_js_code: str) -> None:
    """AcvBody must store measured row height separately from the ROW_H constant."""
    assert "#rowH" in app_js_code or "_rowH" in app_js_code


def test_actual_thead_height_field(app_js_code: str) -> None:
    """AcvBody must store measured thead height for canvas top positioning."""
    assert "#theadH" in app_js_code or "_theadH" in app_js_code


def test_canvas_top_uses_measured_thead(app_js_code: str) -> None:
    """Canvas top must be set from measured thead height, not hardcoded RULER_H."""
    assert "this.#theadH" in app_js_code or "this._theadH" in app_js_code
    # Must not hardcode top to RULER_H constant
    assert "top: ${RULER_H}px" not in app_js_code


def test_draw_uses_measured_row_height(app_js_code: str) -> None:
    """#draw() must use measured row height, not the ROW_H constant for y positions."""
    assert "this.#rowH" in app_js_code or "this._rowH" in app_js_code
