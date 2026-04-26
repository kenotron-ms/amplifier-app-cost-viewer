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
