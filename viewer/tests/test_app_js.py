"""Tests for app.js structure \u2014 written FIRST before the file exists (TDD RED).

Tests verify that app.js contains the required sections, functions, and patterns
per the Task 7 spec: Sections 1\u20133 and 7 plus stubs for 4\u20136.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Path
# ---------------------------------------------------------------------------

APP_JS = (
    Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static" / "app.js"
)


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
# Tests: Section 1 \u2014 State
# ---------------------------------------------------------------------------


class TestSection1State:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_const_state_object_declared(self) -> None:
        assert "const state = {" in self.content or "const state={" in self.content, (
            "Must declare 'const state = {'"
        )

    def test_state_has_sessions_array(self) -> None:
        assert "sessions: []" in self.content or "sessions:[]" in self.content, (
            "state must have sessions: []"
        )

    def test_state_has_active_session_id(self) -> None:
        assert "activeSessionId:" in self.content, (
            "state must have activeSessionId property"
        )

    def test_state_has_session_data(self) -> None:
        assert "sessionData:" in self.content, "state must have sessionData property"

    def test_state_has_spans_array(self) -> None:
        assert "spans: []" in self.content or "spans:[]" in self.content, (
            "state must have spans: []"
        )

    def test_state_has_selected_span(self) -> None:
        assert "selectedSpan:" in self.content, "state must have selectedSpan property"

    def test_state_has_time_scale(self) -> None:
        assert "timeScale:" in self.content, "state must have timeScale property"

    def test_expanded_nodes_set_declared(self) -> None:
        assert (
            "const expandedNodes = new Set()" in self.content
            or "const expandedNodes=new Set()" in self.content
        ), "Must declare 'const expandedNodes = new Set()'"


# ---------------------------------------------------------------------------
# Tests: Section 2 \u2014 API calls
# ---------------------------------------------------------------------------


class TestSection2ApiCalls:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_fetch_sessions_function_defined(self) -> None:
        assert "async function fetchSessions()" in self.content, (
            "Must define 'async function fetchSessions()'"
        )

    def test_fetch_sessions_calls_api(self) -> None:
        assert (
            "'/api/sessions'" in self.content
            or '"/api/sessions"' in self.content
            or "'/api/sessions'" in self.content
        ), "fetchSessions must call GET /api/sessions"

    def test_fetch_sessions_stores_to_state(self) -> None:
        assert "state.sessions" in self.content, (
            "fetchSessions must store result in state.sessions"
        )

    def test_fetch_sessions_throws_on_non_ok(self) -> None:
        # Should check resp.ok and throw
        assert "resp.ok" in self.content or "response.ok" in self.content, (
            "fetchSessions must check resp.ok and throw on failure"
        )
        assert "throw new Error" in self.content, (
            "Must throw new Error on non-ok response"
        )

    def test_fetch_session_function_defined(self) -> None:
        assert (
            "async function fetchSession(id)" in self.content
            or "async function fetchSession(id )" in self.content
        ), "Must define 'async function fetchSession(id)'"

    def test_fetch_session_uses_encode_uri(self) -> None:
        assert "encodeURIComponent(id)" in self.content, (
            "fetchSession must use encodeURIComponent(id)"
        )

    def test_fetch_session_stores_to_state(self) -> None:
        assert "state.sessionData" in self.content, (
            "fetchSession must store result in state.sessionData"
        )

    def test_fetch_spans_function_defined(self) -> None:
        assert (
            "async function fetchSpans(id)" in self.content
            or "async function fetchSpans(id )" in self.content
        ), "Must define 'async function fetchSpans(id)'"

    def test_fetch_spans_uses_encode_uri(self) -> None:
        # encodeURIComponent must appear at least twice (once for fetchSession, once for fetchSpans)
        count = self.content.count("encodeURIComponent")
        assert count >= 2, (
            f"encodeURIComponent must be used in both fetchSession and fetchSpans, found {count} occurrences"
        )

    def test_fetch_spans_stores_to_state(self) -> None:
        assert "state.spans" in self.content, (
            "fetchSpans must store result in state.spans"
        )

    def test_fetch_spans_calls_spans_endpoint(self) -> None:
        assert "/spans" in self.content, "fetchSpans must call .../spans endpoint"


# ---------------------------------------------------------------------------
# Tests: Section 3 \u2014 Toolbar rendering
# ---------------------------------------------------------------------------


class TestSection3Toolbar:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_render_toolbar_function_defined(self) -> None:
        assert "function renderToolbar()" in self.content, (
            "Must define 'function renderToolbar()'"
        )

    def test_toolbar_computes_total_cost(self) -> None:
        # Should use reduce to compute totalCost
        assert "reduce" in self.content, (
            "renderToolbar must use reduce to compute totalCost"
        )
        assert "total_cost_usd" in self.content, (
            "renderToolbar must reference total_cost_usd from session data"
        )

    def test_toolbar_has_title_span(self) -> None:
        assert "toolbar-title" in self.content, (
            "renderToolbar must include span.toolbar-title"
        )
        assert "Cost Viewer" in self.content, "Toolbar title must be 'Cost Viewer'"

    def test_toolbar_title_is_amplifier_cost_viewer(self) -> None:
        # Extract only the renderToolbar function body to avoid matching the
        # file-level comment at the top ("// Amplifier Cost Viewer — app.js").
        toolbar_fn = self.content.split("function renderToolbar()")[1].split(
            "function "
        )[0]
        assert "Amplifier Cost Viewer" in toolbar_fn, (
            "Toolbar innerHTML must render 'Amplifier Cost Viewer' as the title "
            "(found only 'Cost Viewer' — prepend 'Amplifier ')"
        )

    def test_toolbar_has_session_select(self) -> None:
        assert "session-select" in self.content, (
            "renderToolbar must include select#session-select"
        )

    def test_toolbar_options_show_last_8_chars(self) -> None:
        assert "slice(-8)" in self.content or ".slice(-8)" in self.content, (
            "Session dropdown options must show last 8 chars of session_id"
        )

    def test_toolbar_option_uses_session_name_when_present(self) -> None:
        """Toolbar <option> label shows session.name when available."""
        # The toolbar renderToolbar() must reference session.name to build the label
        toolbar_fn = self.content.split("function renderToolbar()")[1].split(
            "function "
        )[0]
        assert "session_id.slice(0, 8)" in toolbar_fn or ".slice(0, 8)" in toolbar_fn, (
            "renderToolbar must use slice(0, 8) (first 8 chars) for the short session ID"
        )
        assert "s.name" in toolbar_fn or "session.name" in toolbar_fn, (
            "renderToolbar must reference session.name to build the option label"
        )

    def test_toolbar_has_cost_total_span(self) -> None:
        assert "cost-total" in self.content, (
            "renderToolbar must include span.cost-total"
        )

    def test_toolbar_has_refresh_button(self) -> None:
        assert "refresh-btn" in self.content, (
            "renderToolbar must include button#refresh-btn"
        )

    def test_toolbar_session_select_change_listener(self) -> None:
        assert "loadSession" in self.content, (
            "renderToolbar must wire change listener to loadSession"
        )

    def test_toolbar_refresh_calls_fetch_sessions(self) -> None:
        # Refresh button should call fetchSessions and reload
        assert "fetchSessions" in self.content, "Refresh button must call fetchSessions"

    def test_format_date_function_defined(self) -> None:
        assert "function _formatDate(" in self.content, (
            "Must define '_formatDate' helper function"
        )

    def test_format_date_handles_today(self) -> None:
        assert "Today" in self.content, "_formatDate must handle 'Today HH:MM' case"

    def test_format_date_handles_yesterday(self) -> None:
        assert "Yesterday" in self.content, "_formatDate must handle 'Yesterday' case"

    def test_format_date_uses_to_local_date_string(self) -> None:
        assert "toLocaleDateString" in self.content, (
            "_formatDate must fall back to toLocaleDateString()"
        )


# ---------------------------------------------------------------------------
# Tests: Stubs for Sections 4-6
# ---------------------------------------------------------------------------


class TestSectionStubs:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_render_tree_panel_stub_exists(self) -> None:
        assert "function renderTreePanel()" in self.content, (
            "Must have renderTreePanel() stub"
        )

    def test_render_gantt_stub_exists(self) -> None:
        assert "function renderGantt()" in self.content, "Must have renderGantt() stub"

    def test_render_detail_stub_exists(self) -> None:
        # After Task 10, renderDetail() is fully implemented with a span parameter
        assert "function renderDetail(" in self.content, (
            "Must have renderDetail() function (stub or full implementation)"
        )

    def test_select_span_stub_exists(self) -> None:
        assert "function selectSpan(" in self.content, "Must have selectSpan() stub"


# ---------------------------------------------------------------------------
# Tests: Section 4 — Tree panel rendering (Task 8)
# ---------------------------------------------------------------------------


class TestSection4TreePanel:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- renderTreePanel ---

    def test_render_tree_panel_is_not_a_stub(self) -> None:
        """renderTreePanel must be fully implemented, not just a comment stub."""
        assert (
            "/* stub"
            not in self.content.split("function renderTreePanel()")[1].split(
                "function "
            )[0]
        ), "renderTreePanel() must not be a stub comment"

    def test_render_tree_panel_clears_tree_panel_element(self) -> None:
        assert "tree-panel" in self.content, (
            "renderTreePanel must reference #tree-panel element"
        )
        assert "innerHTML" in self.content, (
            "renderTreePanel must clear innerHTML of #tree-panel"
        )

    def test_render_tree_panel_shows_no_session_when_no_data(self) -> None:
        assert "No session loaded" in self.content, (
            "renderTreePanel must show 'No session loaded.' when sessionData is null"
        )

    def test_render_tree_panel_calls_render_tree_node(self) -> None:
        assert "_renderTreeNode(" in self.content, (
            "renderTreePanel must call _renderTreeNode()"
        )
        # Should call with depth 0 for root
        assert "_renderTreeNode(panel, state.sessionData, 0)" in self.content or (
            "_renderTreeNode(" in self.content and "0)" in self.content
        ), "renderTreePanel must call _renderTreeNode with depth 0"

    # --- _renderTreeNode ---

    def test_render_tree_node_function_defined(self) -> None:
        assert "function _renderTreeNode(" in self.content, (
            "Must define '_renderTreeNode' function"
        )

    def test_render_tree_node_creates_tree_row_div(self) -> None:
        assert "tree-row" in self.content, (
            "_renderTreeNode must create div with class 'tree-row'"
        )

    def test_render_tree_node_sets_dataset_session_id(self) -> None:
        assert (
            "dataset.sessionId" in self.content or "data-session-id" in self.content
        ), "_renderTreeNode must set dataset.sessionId on the row"

    def test_render_tree_node_adds_active_class(self) -> None:
        assert "active" in self.content, (
            "_renderTreeNode must add 'active' class when node matches activeSessionId"
        )
        assert "activeSessionId" in self.content, (
            "_renderTreeNode must check state.activeSessionId"
        )

    def test_render_tree_node_renders_indent_span(self) -> None:
        assert "indent" in self.content or "depth" in self.content, (
            "_renderTreeNode must render indent span based on depth"
        )
        assert "12" in self.content, "Indent width must be depth * 12px"

    def test_render_tree_node_renders_toggle_span(self) -> None:
        # Should have expand/collapse triangles
        # ▾ (25BE) and ▸ (25B8)
        assert (
            "\u25be" in self.content
            or "\\u25be" in self.content
            or "&#9662;" in self.content
            or "\u25b8" in self.content
            or "\\u25b8" in self.content
            or "&#9656;" in self.content
        ), "_renderTreeNode must render toggle span with triangle characters (▾/▸)"

    def test_render_tree_node_renders_session_label(self) -> None:
        assert "session-label" in self.content, (
            "_renderTreeNode must render span with class 'session-label'"
        )

    def test_render_tree_node_label_shows_last_8_chars(self) -> None:
        # slice(-8) must appear at least once (in _renderTreeNode)
        # Note: renderToolbar() now uses slice(0, 8) (first 8 chars) for a different format
        count = self.content.count("slice(-8)")
        assert count >= 1, (
            f"tree session label must show last 8 chars via slice(-8), found {count} occurrences"
        )

    def test_render_tree_node_label_shows_agent_name(self) -> None:
        assert "agent" in self.content.lower(), (
            "_renderTreeNode must optionally show agent name"
        )

    def test_render_tree_node_label_has_title_attribute(self) -> None:
        assert "title" in self.content, (
            "_renderTreeNode must set title attribute to full session_id"
        )

    def test_render_tree_node_renders_cost_span(self) -> None:
        assert "session-cost" in self.content, (
            "_renderTreeNode must render span with class 'session-cost'"
        )
        assert "total_cost_usd" in self.content, (
            "_renderTreeNode must display total_cost_usd"
        )

    def test_render_tree_node_click_handler_toggles_expansion(self) -> None:
        assert "expandedNodes" in self.content, (
            "_renderTreeNode click handler must use expandedNodes set"
        )
        assert (
            "expandedNodes.has(" in self.content
            or "expandedNodes.delete(" in self.content
        ), "_renderTreeNode click handler must toggle node in expandedNodes"

    def test_render_tree_node_click_calls_render_tree_panel(self) -> None:
        # The click handler should re-render the tree panel
        assert "renderTreePanel()" in self.content, (
            "_renderTreeNode click handler must call renderTreePanel() to re-render"
        )

    def test_render_tree_node_click_calls_scroll_gantt(self) -> None:
        assert "_scrollGanttToSession(" in self.content, (
            "_renderTreeNode click handler must call _scrollGanttToSession()"
        )

    def test_render_tree_node_renders_children_recursively(self) -> None:
        # Should recursively call _renderTreeNode for children
        assert "children" in self.content, "_renderTreeNode must handle children array"
        # Check recursive call pattern
        assert (
            "_renderTreeNode(container" in self.content
            or "_renderTreeNode(panel" in self.content
            or "forEach" in self.content
        ), "_renderTreeNode must recursively render children"

    # --- _scrollGanttToSession ---

    def test_scroll_gantt_function_defined(self) -> None:
        assert "function _scrollGanttToSession(" in self.content, (
            "Must define '_scrollGanttToSession' function"
        )

    def test_scroll_gantt_queries_by_data_attribute(self) -> None:
        assert "gantt-rows" in self.content, (
            "_scrollGanttToSession must query #gantt-rows"
        )
        assert "data-session-id" in self.content, (
            "_scrollGanttToSession must query by data-session-id attribute"
        )

    def test_scroll_gantt_calls_scroll_into_view(self) -> None:
        assert "scrollIntoView" in self.content, (
            "_scrollGanttToSession must call scrollIntoView"
        )
        assert "smooth" in self.content, (
            "_scrollGanttToSession must use smooth scrolling"
        )
        assert "nearest" in self.content, (
            "_scrollGanttToSession must use block:'nearest'"
        )


# ---------------------------------------------------------------------------
# Tests: Section 7 \u2014 Init / loadSession
# ---------------------------------------------------------------------------


class TestSection7Init:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_load_session_function_defined(self) -> None:
        assert "async function loadSession(id)" in self.content, (
            "Must define 'async function loadSession(id)'"
        )

    def test_load_session_sets_active_id(self) -> None:
        assert (
            "state.activeSessionId = id" in self.content
            or "state.activeSessionId=id" in self.content
        ), "loadSession must set state.activeSessionId = id"

    def test_load_session_fetches_session(self) -> None:
        assert (
            "fetchSession(id)" in self.content
            or "await fetchSession(id)" in self.content
        ), "loadSession must call fetchSession(id)"

    def test_load_session_fetches_spans(self) -> None:
        assert (
            "fetchSpans(id)" in self.content or "await fetchSpans(id)" in self.content
        ), "loadSession must call fetchSpans(id)"

    def test_load_session_auto_expands_root(self) -> None:
        assert "expandedNodes.add(id)" in self.content, (
            "loadSession must auto-expand root in expandedNodes"
        )

    def test_load_session_auto_expands_children(self) -> None:
        # Should add immediate children to expandedNodes
        assert "expandedNodes.add(" in self.content, (
            "loadSession must add children to expandedNodes"
        )
        assert "children" in self.content, (
            "loadSession must reference sessionData.children"
        )

    def test_load_session_computes_time_scale(self) -> None:
        assert "state.timeScale" in self.content, (
            "loadSession must compute state.timeScale"
        )
        assert (
            "maxEndMs" in self.content
            or "max_end_ms" in self.content
            or "end_ms" in self.content
        ), "loadSession must compute timeScale from max end_ms"

    def test_load_session_clamps_gantt_width(self) -> None:
        # Should clamp to min 400
        assert "400" in self.content, (
            "loadSession must clamp gantt width to minimum 400"
        )

    def test_load_session_calls_render_toolbar(self) -> None:
        assert "renderToolbar()" in self.content, (
            "loadSession must call renderToolbar()"
        )

    def test_load_session_calls_render_tree_panel(self) -> None:
        assert "renderTreePanel()" in self.content, (
            "loadSession must call renderTreePanel()"
        )

    def test_load_session_calls_render_gantt(self) -> None:
        assert "renderGantt()" in self.content, "loadSession must call renderGantt()"

    def test_init_function_defined(self) -> None:
        assert "async function init()" in self.content, (
            "Must define 'async function init()'"
        )

    def test_init_fetches_sessions(self) -> None:
        assert "fetchSessions" in self.content, "init must call fetchSessions"

    def test_init_renders_toolbar(self) -> None:
        assert "renderToolbar" in self.content, "init must call renderToolbar"

    def test_init_loads_first_session(self) -> None:
        assert "sessions[0]" in self.content, (
            "init must load the first session with sessions[0]"
        )

    def test_init_handles_no_sessions(self) -> None:
        # Should show 'No sessions found' message
        assert "No sessions" in self.content, (
            "init must show 'No sessions found' message when no sessions"
        )

    def test_init_handles_errors(self) -> None:
        assert "catch" in self.content, "init must handle errors with try/catch"
        assert (
            "color:#f85149" in self.content
            or "color: #f85149" in self.content
            or "#f85149" in self.content
        ), "init must display error in red (danger color #f85149)"

    def test_dom_content_loaded_listener(self) -> None:
        assert "DOMContentLoaded" in self.content, (
            "Must add 'DOMContentLoaded' event listener"
        )
        assert "init" in self.content, "DOMContentLoaded listener must call init"

    def test_refresh_button_handler_has_error_handling(self) -> None:
        # Refresh click handler must catch errors so state corruption is visible to user
        assert "Refresh failed" in self.content, (
            "Refresh button click handler must catch errors and display 'Refresh failed' feedback"
        )

    def test_init_load_session_wrapped_in_try_catch(self) -> None:
        # loadSession in init() must be protected so a corrupt first session doesn't produce
        # an unhandled promise rejection — look for 'Failed to load session' or 'Error loading'
        assert (
            "Failed to load session" in self.content
            or "Error loading session" in self.content
        ), (
            "init() must wrap loadSession() in try/catch and log the error "
            "(e.g., console.error('Failed to load session:', err))"
        )

    def test_session_select_change_listener_has_catch_handler(self) -> None:
        # The session-select change listener calls loadSession (async); without .catch()
        # any rejection becomes an unhandled promise rejection with no user feedback.
        assert "Failed to switch session" in self.content, (
            "session-select change listener must add .catch() to loadSession() "
            "and display user-visible feedback (e.g., 'Failed to switch session')"
        )

    def test_refresh_handler_does_not_pre_clear_sessions(self) -> None:
        # Refresh handler must NOT wipe state.sessions before the fetch succeeds.
        # fetchSessions() updates state.sessions on success; pre-clearing corrupts state
        # when the network call fails (DOM still shows old sessions, state is empty).
        assert "state.sessions = []" not in self.content, (
            "Refresh handler must not pre-clear state.sessions before fetchSessions() "
            "succeeds — mutate state only after the network call completes successfully"
        )


# ---------------------------------------------------------------------------
# Tests: Section 5 — Gantt SVG rendering (Task 9)
# ---------------------------------------------------------------------------


class TestSection5GanttConstants:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_row_height_constant_defined(self) -> None:
        assert "ROW_HEIGHT" in self.content, "Must define ROW_HEIGHT constant"
        assert "ROW_HEIGHT = 32" in self.content or "ROW_HEIGHT=32" in self.content, (
            "ROW_HEIGHT must equal 32"
        )

    def test_span_h_constant_defined(self) -> None:
        assert "SPAN_H" in self.content, "Must define SPAN_H constant"
        assert "SPAN_H = 20" in self.content or "SPAN_H=20" in self.content, (
            "SPAN_H must equal 20"
        )

    def test_span_y_off_constant_defined(self) -> None:
        assert "SPAN_Y_OFF" in self.content, "Must define SPAN_Y_OFF constant"
        assert "SPAN_Y_OFF = 6" in self.content or "SPAN_Y_OFF=6" in self.content, (
            "SPAN_Y_OFF must equal 6"
        )

    def test_min_bar_w_constant_defined(self) -> None:
        assert "MIN_BAR_W" in self.content, "Must define MIN_BAR_W constant"
        assert "MIN_BAR_W = 2" in self.content or "MIN_BAR_W=2" in self.content, (
            "MIN_BAR_W must equal 2"
        )


class TestSection5RenderGantt:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    def test_render_gantt_is_not_a_stub(self) -> None:
        """renderGantt must be fully implemented, not just a comment stub."""
        after_fn = self.content.split("function renderGantt()")[1]
        next_fn = after_fn.split("function ")[0]
        assert "/* stub" not in next_fn, "renderGantt() must not be a stub comment"

    def test_render_gantt_clears_gantt_rows(self) -> None:
        assert "gantt-rows" in self.content, (
            "renderGantt must reference #gantt-rows element"
        )

    def test_render_gantt_clears_time_ruler(self) -> None:
        assert "time-ruler" in self.content, (
            "renderGantt must reference #time-ruler element"
        )

    def test_render_gantt_shows_no_spans_message(self) -> None:
        assert "No spans to display" in self.content, (
            "renderGantt must show 'No spans to display.' when spans is empty"
        )

    def test_render_gantt_computes_max_end_ms(self) -> None:
        assert "maxEndMs" in self.content, (
            "renderGantt must compute maxEndMs from spans"
        )
        assert "end_ms" in self.content, (
            "renderGantt must use end_ms from spans to compute maxEndMs"
        )

    def test_render_gantt_computes_svg_width(self) -> None:
        assert "svgWidth" in self.content, (
            "renderGantt must compute svgWidth as max of panel width and timeline extent"
        )

    def test_render_gantt_builds_session_order(self) -> None:
        assert "sessionOrder" in self.content, (
            "renderGantt must build sessionOrder via _flattenSessionOrder DFS"
        )
        assert "_flattenSessionOrder" in self.content, (
            "renderGantt must call _flattenSessionOrder to get session order"
        )

    def test_render_gantt_creates_svg_element(self) -> None:
        assert "createElementNS" in self.content or "_svgEl(" in self.content, (
            "renderGantt must create SVG elements using createElementNS or _svgEl helper"
        )

    def test_render_gantt_alternating_backgrounds(self) -> None:
        assert "#161b22" in self.content, (
            "renderGantt must use #161b22 for alternating row background"
        )
        assert "#0d1117" in self.content, (
            "renderGantt must use #0d1117 for alternating row background"
        )

    def test_render_gantt_groups_spans_by_session_id(self) -> None:
        assert "session_id" in self.content, (
            "renderGantt must group spans by session_id"
        )

    def test_render_gantt_creates_g_elements_with_data_session_id(self) -> None:
        assert "data-session-id" in self.content, (
            "renderGantt must create <g data-session-id=...> for each session row"
        )

    def test_render_gantt_uses_transform_translate(self) -> None:
        assert "translate" in self.content, (
            "renderGantt must use transform=translate(...) for row positioning"
        )

    def test_render_gantt_creates_rect_elements(self) -> None:
        assert '"rect"' in self.content or "'rect'" in self.content, (
            "renderGantt must create <rect> elements for spans"
        )

    def test_render_gantt_rect_has_rx3(self) -> None:
        assert "rx" in self.content and "3" in self.content, (
            "renderGantt rect must have rx=3 for rounded corners"
        )

    def test_render_gantt_rect_has_opacity(self) -> None:
        assert "0.85" in self.content, "renderGantt rect must have opacity=0.85"

    def test_render_gantt_rect_uses_span_y_off(self) -> None:
        assert "SPAN_Y_OFF" in self.content, (
            "renderGantt rect y-position must use SPAN_Y_OFF constant"
        )

    def test_render_gantt_rect_uses_span_h(self) -> None:
        assert "SPAN_H" in self.content, (
            "renderGantt rect height must use SPAN_H constant"
        )

    def test_render_gantt_rect_uses_min_bar_w(self) -> None:
        assert "MIN_BAR_W" in self.content, (
            "renderGantt rect width must use MIN_BAR_W for minimum bar width"
        )

    def test_render_gantt_uses_span_color(self) -> None:
        assert "span.color" in self.content, "renderGantt rect fill must use span.color"

    def test_render_gantt_has_fallback_color(self) -> None:
        assert "'#64748B'" in self.content or '"#64748B"' in self.content, (
            "renderGantt must have fallback color #64748B when span.color is absent"
        )

    def test_render_gantt_rect_has_title_tooltip(self) -> None:
        assert "_spanTooltip" in self.content, (
            "renderGantt rect must have SVG <title> tooltip via _spanTooltip"
        )
        assert '"title"' in self.content or "'title'" in self.content, (
            "renderGantt must create <title> elements for span tooltips"
        )

    def test_render_gantt_rect_click_calls_select_span(self) -> None:
        assert "selectSpan" in self.content, (
            "renderGantt rect click handler must call selectSpan"
        )

    def test_render_gantt_rect_click_stops_propagation(self) -> None:
        assert "stopPropagation" in self.content, (
            "renderGantt rect click handler must call stopPropagation"
        )

    def test_render_gantt_rect_hover_highlight(self) -> None:
        assert "mouseenter" in self.content, (
            "renderGantt rect must have mouseenter listener for opacity highlight"
        )
        assert "mouseleave" in self.content, (
            "renderGantt rect must have mouseleave listener to restore opacity"
        )

    def test_render_gantt_svg_background_click(self) -> None:
        assert "_showGap" in self.content, (
            "renderGantt SVG background click must call _showGap"
        )
        assert "clickMs" in self.content, (
            "renderGantt SVG background click must compute clickMs"
        )

    def test_render_gantt_calls_render_ruler(self) -> None:
        assert "_renderRuler" in self.content, (
            "renderGantt must call _renderRuler after appending rows"
        )


class TestSection5HelperFunctions:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- _flattenSessionOrder ---

    def test_flatten_session_order_defined(self) -> None:
        assert "function _flattenSessionOrder(" in self.content, (
            "Must define '_flattenSessionOrder' DFS function"
        )

    def test_flatten_session_order_is_dfs_push(self) -> None:
        assert "result.push" in self.content, (
            "_flattenSessionOrder must push node to result (DFS)"
        )

    # --- _renderRuler ---

    def test_render_ruler_defined(self) -> None:
        assert "function _renderRuler(" in self.content, (
            "Must define '_renderRuler' function"
        )

    def test_render_ruler_creates_svg_height_28(self) -> None:
        assert "28" in self.content, "_renderRuler must create SVG with height 28"

    def test_render_ruler_has_tick_intervals(self) -> None:
        # Should pick tick interval based on total duration: 5s/30s/1m/5m
        # These are all in seconds but used as milliseconds internally
        assert (
            "5000" in self.content or "30000" in self.content or "60000" in self.content
        ), "_renderRuler must pick tick interval based on total duration (5s/30s/1m/5m)"

    def test_render_ruler_renders_line_and_text(self) -> None:
        assert '"line"' in self.content or "'line'" in self.content, (
            "_renderRuler must render <line> tick marks"
        )
        assert '"text"' in self.content or "'text'" in self.content, (
            "_renderRuler must render <text> tick labels"
        )

    # --- _svgEl ---

    def test_svg_el_helper_defined(self) -> None:
        assert "function _svgEl(" in self.content, (
            "Must define '_svgEl' SVG element helper function"
        )

    def test_svg_el_uses_namespace(self) -> None:
        assert "http://www.w3.org/2000/svg" in self.content, (
            "_svgEl must use SVG namespace 'http://www.w3.org/2000/svg'"
        )

    def test_svg_el_sets_attributes(self) -> None:
        assert "setAttribute" in self.content, (
            "_svgEl must set attributes with setAttribute"
        )

    # --- _formatMs ---

    def test_format_ms_defined(self) -> None:
        assert "function _formatMs(" in self.content, "Must define '_formatMs' function"

    def test_format_ms_returns_ms_format(self) -> None:
        assert (
            "'ms'" in self.content or '"ms"' in self.content or "`ms`" in self.content
        ), "_formatMs must return 'Nms' format for short durations"

    def test_format_ms_returns_seconds_format(self) -> None:
        # Should return 'N.Ns' for durations under 1 minute
        assert (
            "'s'" in self.content or '"s"' in self.content or "`s`" in self.content
        ), "_formatMs must return 'N.Ns' format for second-scale durations"

    def test_format_ms_returns_minutes_format(self) -> None:
        # Should return 'NmSSs' for durations over 1 minute
        assert (
            "'m'" in self.content or '"m"' in self.content or "`m`" in self.content
        ), "_formatMs must return 'NmSSs' format for minute-scale durations"

    # --- _spanTooltip ---

    def test_span_tooltip_defined(self) -> None:
        assert "function _spanTooltip(" in self.content, (
            "Must define '_spanTooltip' function"
        )

    def test_span_tooltip_handles_llm_spans(self) -> None:
        # Should show provider/model, time range, token counts, cost for llm spans
        assert "provider" in self.content, (
            "_spanTooltip must reference provider for llm spans"
        )
        assert "model" in self.content, (
            "_spanTooltip must reference model for llm spans"
        )

    def test_span_tooltip_handles_token_counts(self) -> None:
        # Should show input_tokens and output_tokens
        assert "tokens" in self.content, "_spanTooltip must show token counts"

    def test_span_tooltip_handles_tool_spans(self) -> None:
        # Should show tool name and success/failure
        assert "tool" in self.content, "_spanTooltip must handle tool spans"

    def test_span_tooltip_handles_thinking_spans(self) -> None:
        # Should show 'thinking' type spans
        assert "thinking" in self.content, "_spanTooltip must handle thinking spans"

    # --- _showGap ---

    def test_show_gap_defined(self) -> None:
        assert "function _showGap(" in self.content, "Must define '_showGap' function"

    def test_show_gap_finds_span_before(self) -> None:
        assert "clickMs" in self.content, (
            "_showGap must use clickMs to find surrounding spans"
        )

    def test_show_gap_calls_render_detail_with_gap_type(self) -> None:
        assert (
            "type:'gap'" in self.content
            or "type: 'gap'" in self.content
            or 'type:"gap"' in self.content
            or 'type: "gap"' in self.content
        ), "_showGap must call renderDetail with type='gap'"

    # --- selectSpan updated ---

    def test_select_span_calls_render_detail(self) -> None:
        # selectSpan stub must be updated to call renderDetail(span)
        after_fn = self.content.split("function selectSpan(")[1]
        next_fn = after_fn.split("function ")[0]
        assert "renderDetail(" in next_fn, "selectSpan must call renderDetail(span)"


# ---------------------------------------------------------------------------
# Tests: Section 6 — Detail panel (Task 10)
# ---------------------------------------------------------------------------


class TestSection6DetailPanel:
    def setup_method(self) -> None:
        self.content = APP_JS.read_text()

    # --- IO_TRUNCATE constant ---

    def test_io_truncate_constant_defined(self) -> None:
        assert "IO_TRUNCATE" in self.content, "Must define IO_TRUNCATE constant"

    def test_io_truncate_value_is_500(self) -> None:
        assert (
            "IO_TRUNCATE = 500" in self.content or "IO_TRUNCATE=500" in self.content
        ), "IO_TRUNCATE must equal 500"

    # --- renderDetail function ---

    def test_render_detail_is_not_a_stub(self) -> None:
        """renderDetail must be fully implemented, not just a comment stub."""
        after_fn = self.content.split("function renderDetail(")[1]
        next_fn = after_fn.split("function ")[0]
        assert "/* stub" not in next_fn, "renderDetail() must not be a stub comment"

    def test_render_detail_removes_hidden_class(self) -> None:
        assert (
            "classList.remove('hidden')" in self.content
            or 'classList.remove("hidden")' in self.content
        ), "renderDetail must remove 'hidden' class from #detail-panel"

    def test_render_detail_dispatches_to_detail_llm(self) -> None:
        assert "_detailLlm(" in self.content, (
            "renderDetail must dispatch to _detailLlm for llm spans"
        )

    def test_render_detail_dispatches_to_detail_tool(self) -> None:
        assert "_detailTool(" in self.content, (
            "renderDetail must dispatch to _detailTool for tool spans"
        )

    def test_render_detail_dispatches_to_detail_thinking(self) -> None:
        assert "_detailThinking(" in self.content, (
            "renderDetail must dispatch to _detailThinking for thinking spans"
        )

    def test_render_detail_dispatches_to_detail_gap(self) -> None:
        assert "_detailGap(" in self.content, (
            "renderDetail must dispatch to _detailGap for gap spans"
        )

    def test_render_detail_wires_show_more_buttons(self) -> None:
        assert "detail-show-more" in self.content, (
            "renderDetail must wire .detail-show-more click handlers"
        )

    def test_render_detail_wires_close_button(self) -> None:
        assert "detail-close" in self.content, (
            "renderDetail must wire .detail-close button"
        )
        assert "_closeDetail" in self.content, (
            "renderDetail must call _closeDetail from close button"
        )

    # --- selectSpan sets state.selectedSpan ---

    def test_select_span_sets_state_selected_span(self) -> None:
        after_fn = self.content.split("function selectSpan(")[1]
        next_fn = after_fn.split("function ")[0]
        assert "state.selectedSpan" in next_fn, "selectSpan must set state.selectedSpan"

    # --- _detailLlm ---

    def test_detail_llm_function_defined(self) -> None:
        assert "function _detailLlm(" in self.content, (
            "Must define '_detailLlm' function"
        )

    def test_detail_llm_shows_provider_model_title(self) -> None:
        assert "span.provider" in self.content, (
            "_detailLlm must reference span.provider for the title"
        )
        assert "span.model" in self.content, (
            "_detailLlm must reference span.model for the title"
        )

    def test_detail_llm_shows_token_counts_with_to_locale_string(self) -> None:
        assert "toLocaleString" in self.content, (
            "_detailLlm must display token counts using toLocaleString"
        )

    def test_detail_llm_shows_cost_as_6_decimals(self) -> None:
        assert "toFixed(6)" in self.content, (
            "_detailLlm must format cost_usd with toFixed(6)"
        )

    def test_detail_llm_references_cost_usd(self) -> None:
        assert "cost_usd" in self.content, (
            "_detailLlm must reference cost_usd from span"
        )

    def test_detail_llm_calls_io_block(self) -> None:
        assert "_ioBlock(" in self.content, (
            "_detailLlm must call _ioBlock for INPUT and OUTPUT blocks"
        )

    def test_detail_llm_shows_cache_tokens(self) -> None:
        assert "cache_read" in self.content or "cache_write" in self.content, (
            "_detailLlm must show optional cache_read/cache_write token counts"
        )

    def test_detail_llm_shows_input_tokens(self) -> None:
        assert "input_tokens" in self.content, "_detailLlm must show input token count"

    def test_detail_llm_shows_output_tokens(self) -> None:
        assert "output_tokens" in self.content, (
            "_detailLlm must show output token count"
        )

    # --- _detailTool ---

    def test_detail_tool_function_defined(self) -> None:
        assert "function _detailTool(" in self.content, (
            "Must define '_detailTool' function"
        )

    def test_detail_tool_shows_success_checkmark(self) -> None:
        assert "\u2713" in self.content or "\\u2713" in self.content, (
            "_detailTool must show \u2713 checkmark for successful tools"
        )

    def test_detail_tool_shows_failure_cross(self) -> None:
        assert "\u2717" in self.content or "\\u2717" in self.content, (
            "_detailTool must show \u2717 cross for failed tools"
        )

    def test_detail_tool_shows_success_in_green(self) -> None:
        # green color for success indicator
        assert "green" in self.content or "#" in self.content, (
            "_detailTool must color success indicator green"
        )

    def test_detail_tool_calls_io_block(self) -> None:
        # _ioBlock must be called (already tested above but confirm context)
        assert "_ioBlock(" in self.content, (
            "_detailTool must call _ioBlock for INPUT/OUTPUT blocks"
        )

    # --- _detailThinking ---

    def test_detail_thinking_function_defined(self) -> None:
        assert "function _detailThinking(" in self.content, (
            "Must define '_detailThinking' function"
        )

    def test_detail_thinking_shows_thinking_title(self) -> None:
        after_fn = self.content.split("function _detailThinking(")[1]
        next_fn = after_fn.split("function _detail")[0]
        assert "thinking" in next_fn.lower(), (
            "_detailThinking must display 'thinking' title"
        )

    def test_detail_thinking_uses_indigo_color(self) -> None:
        assert "#6366F1" in self.content or "#6366f1" in self.content, (
            "_detailThinking must use indigo color #6366F1 for the title"
        )

    # --- _detailGap ---

    def test_detail_gap_function_defined(self) -> None:
        assert "function _detailGap(" in self.content, (
            "Must define '_detailGap' function"
        )

    def test_detail_gap_shows_orchestrator_overhead(self) -> None:
        assert "orchestrator overhead" in self.content, (
            "_detailGap must display 'orchestrator overhead' as the title"
        )

    def test_detail_gap_shows_duration(self) -> None:
        after_fn = self.content.split("function _detailGap(")[1]
        next_fn = after_fn.split("function _")[0]
        # Duration should be computed from before/after spans
        assert "duration" in next_fn.lower() or "_formatMs" in next_fn, (
            "_detailGap must show duration of the gap"
        )

    def test_detail_gap_shows_before_after_labels(self) -> None:
        assert (
            "before_label" in self.content
            or "after_label" in self.content
            or ("before" in self.content and "after" in self.content)
        ), "_detailGap must show 'between {before_label} and {after_label}'"

    # --- _ioBlock ---

    def test_io_block_function_defined(self) -> None:
        assert "function _ioBlock(" in self.content, "Must define '_ioBlock' function"

    def test_io_block_returns_empty_for_null(self) -> None:
        after_fn = self.content.split("function _ioBlock(")[1]
        next_fn = after_fn.split("function _")[0]
        assert (
            "== null" in next_fn or "=== null" in next_fn or "undefined" in next_fn
        ), "_ioBlock must return empty string for null/undefined value"

    def test_io_block_converts_to_json_with_indent_2(self) -> None:
        assert "JSON.stringify" in self.content, (
            "_ioBlock must convert non-string values to JSON"
        )
        assert "null, 2" in self.content, (
            "_ioBlock must use JSON.stringify with indent 2"
        )

    def test_io_block_truncates_at_io_truncate(self) -> None:
        assert "IO_TRUNCATE" in self.content, (
            "_ioBlock must use IO_TRUNCATE for truncation limit"
        )
        assert "slice(0, IO_TRUNCATE)" in self.content, (
            "_ioBlock must slice content at IO_TRUNCATE characters"
        )

    def test_io_block_uses_detail_io_content_class(self) -> None:
        assert "detail-io-content" in self.content, (
            "_ioBlock must use detail-io-content div class"
        )

    def test_io_block_has_data_full_text_attribute(self) -> None:
        assert "data-full-text" in self.content or "data-fullText" in self.content, (
            "_ioBlock must set data-full-text attribute"
        )

    def test_io_block_has_show_more_link(self) -> None:
        assert "show more" in self.content, (
            "_ioBlock must add 'show more (N chars)' link when truncated"
        )

    def test_io_block_ellipsis_when_truncated(self) -> None:
        assert (
            "\u2026" in self.content
            or "\\u2026" in self.content
            or "..." in self.content
        ), "_ioBlock must add ellipsis when content is truncated"

    # --- _closeDetail ---

    def test_close_detail_function_defined(self) -> None:
        assert "function _closeDetail()" in self.content, (
            "Must define '_closeDetail()' function"
        )

    def test_close_detail_adds_hidden_class(self) -> None:
        assert (
            "classList.add('hidden')" in self.content
            or 'classList.add("hidden")' in self.content
        ), "_closeDetail must add 'hidden' class to #detail-panel"

    def test_close_detail_clears_selected_span(self) -> None:
        after_fn = self.content.split("function _closeDetail()")[1]
        next_fn = after_fn.split("function ")[0]
        assert "state.selectedSpan" in next_fn, (
            "_closeDetail must clear state.selectedSpan"
        )

    # --- _esc ---

    def test_esc_function_defined(self) -> None:
        assert "function _esc(" in self.content, (
            "Must define '_esc' HTML-escape function"
        )

    def test_esc_escapes_ampersand(self) -> None:
        assert "&amp;" in self.content, "_esc must escape & to &amp;"

    def test_esc_escapes_less_than(self) -> None:
        assert "&lt;" in self.content, "_esc must escape < to &lt;"

    def test_esc_escapes_greater_than(self) -> None:
        assert "&gt;" in self.content, "_esc must escape > to &gt;"

    def test_esc_escapes_double_quote(self) -> None:
        assert "&quot;" in self.content, '_esc must escape " to &quot;'

    # --- Time range formatting ---

    def test_detail_panel_uses_format_ms_for_offsets(self) -> None:
        # _detailLlm/_detailTool show time range using _formatMs
        after_s6 = (
            self.content.split("Section 6")[1]
            if "Section 6" in self.content
            else self.content
        )
        assert "_formatMs" in after_s6, (
            "Detail panel functions must use _formatMs for formatted offsets"
        )
