"""Tests for the v2 static HTML shell and CSS — written FIRST before files exist (TDD RED).

Tests verify:
1. index.html contains the correct v2 shell: DOCTYPE, lang=en, charset utf-8,
   title 'Amplifier Cost Viewer', link to /static/style.css,
   script type=module src /static/app.js, and custom element tags
   <acv-toolbar id=toolbar>, <acv-tree id=tree>, <acv-timeline id=timeline>,
   <main id=main>.
2. style.css contains the dark theme with required CSS custom properties,
   layout vars, span colors, box-sizing reset, flex-direction column,
   monospace font 12px, and scrollbar styling.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

STATIC = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static"
INDEX_HTML = STATIC / "index.html"
STYLE_CSS = STATIC / "style.css"


# ---------------------------------------------------------------------------
# HTML parsing helper
# ---------------------------------------------------------------------------


class _AttrCollector(HTMLParser):
    """Minimal HTML parser that collects tags with their attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []  # (tag, attrs)
        self.data_segments: list[tuple[str, str]] = []  # (tag, data)
        self._current_tag: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))
        self._current_tag = tag

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped and self._current_tag:
            self.data_segments.append((self._current_tag, stripped))


def _parse_html(html: str) -> _AttrCollector:
    collector = _AttrCollector()
    collector.feed(html)
    return collector


def _get_tags_by_name(
    collector: _AttrCollector, tag: str
) -> list[dict[str, str | None]]:
    return [attrs for t, attrs in collector.tags if t == tag]


def _has_element(
    collector: _AttrCollector,
    tag: str,
    *,
    id: str | None = None,
    class_: str | None = None,
) -> bool:
    for t, attrs in collector.tags:
        if t != tag:
            continue
        if id is not None and attrs.get("id") != id:
            continue
        if class_ is not None:
            classes = (attrs.get("class") or "").split()
            if class_ not in classes:
                continue
        return True
    return False


# ---------------------------------------------------------------------------
# Tests: index.html existence and basic structure
# ---------------------------------------------------------------------------


class TestIndexHtmlExists:
    def test_file_exists(self) -> None:
        assert INDEX_HTML.exists(), f"{INDEX_HTML} must exist"

    def test_not_empty(self) -> None:
        assert len(INDEX_HTML.read_text()) > 100, (
            "index.html must have substantial content"
        )


class TestIndexHtmlDoctype:
    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()

    def test_has_doctype(self) -> None:
        assert (
            "<!DOCTYPE html>" in self.content
            or "<!doctype html>" in self.content.lower()
        ), "Must have <!DOCTYPE html>"

    def test_html_lang_en(self) -> None:
        assert 'lang="en"' in self.content, "Must have lang='en' on <html>"


class TestIndexHtmlHead:
    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()
        self.collector = _parse_html(self.content)

    def test_meta_charset_utf8(self) -> None:
        metas = _get_tags_by_name(self.collector, "meta")
        assert any(
            (m.get("charset") or "").lower() in ("utf-8", "utf8") for m in metas
        ), "Must have <meta charset='utf-8'>"

    def test_viewport_meta(self) -> None:
        metas = _get_tags_by_name(self.collector, "meta")
        assert any(m.get("name") == "viewport" for m in metas), (
            "Must have viewport meta tag"
        )

    def test_title_amplifier_cost_viewer(self) -> None:
        assert "Amplifier Cost Viewer" in self.content, (
            "Must have title 'Amplifier Cost Viewer'"
        )

    def test_link_to_style_css(self) -> None:
        links = _get_tags_by_name(self.collector, "link")
        assert any("/static/style.css" in (lnk.get("href") or "") for lnk in links), (
            "Must link to /static/style.css"
        )

    def test_script_type_module(self) -> None:
        scripts = _get_tags_by_name(self.collector, "script")
        assert any(
            s.get("type") == "module" and "/static/app.js" in (s.get("src") or "")
            for s in scripts
        ), "Must have <script type='module' src='/static/app.js'>"


class TestIndexHtmlBody:
    def setup_method(self) -> None:
        self.content = INDEX_HTML.read_text()
        self.collector = _parse_html(self.content)

    def test_acv_toolbar_element(self) -> None:
        assert _has_element(self.collector, "acv-toolbar", id="toolbar"), (
            "Must have <acv-toolbar id='toolbar'>"
        )

    def test_main_element(self) -> None:
        assert _has_element(self.collector, "main", id="main"), (
            "Must have <main id='main'>"
        )

    def test_acv_tree_element(self) -> None:
        assert _has_element(self.collector, "acv-tree", id="tree"), (
            "Must have <acv-tree id='tree'>"
        )

    def test_acv_timeline_element(self) -> None:
        assert _has_element(self.collector, "acv-timeline", id="timeline"), (
            "Must have <acv-timeline id='timeline'>"
        )


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
        assert (
            "--surface:#161b22" in self.content or "--surface: #161b22" in self.content
        )

    def test_surface_alt_color(self) -> None:
        assert (
            "--surface-alt:#21262d" in self.content
            or "--surface-alt: #21262d" in self.content
        )

    def test_border_color(self) -> None:
        assert "--border:#30363d" in self.content or "--border: #30363d" in self.content

    def test_text_color(self) -> None:
        assert "--text:#e6edf3" in self.content or "--text: #e6edf3" in self.content

    def test_text_muted_color(self) -> None:
        assert (
            "--text-muted:#8b949e" in self.content
            or "--text-muted: #8b949e" in self.content
        )

    def test_accent_color(self) -> None:
        assert "--accent:#58a6ff" in self.content or "--accent: #58a6ff" in self.content

    def test_danger_color(self) -> None:
        assert "--danger:#f85149" in self.content or "--danger: #f85149" in self.content

    def test_success_color(self) -> None:
        assert (
            "--success:#3fb950" in self.content or "--success: #3fb950" in self.content
        )


class TestStyleCssLayoutVars:
    def setup_method(self) -> None:
        self.content = STYLE_CSS.read_text()

    def test_toolbar_height(self) -> None:
        assert (
            "--toolbar-height:42px" in self.content
            or "--toolbar-height: 42px" in self.content
        )

    def test_tree_width(self) -> None:
        assert (
            "--tree-width:220px" in self.content
            or "--tree-width: 220px" in self.content
        )

    def test_ruler_height(self) -> None:
        assert (
            "--ruler-height:28px" in self.content
            or "--ruler-height: 28px" in self.content
        )

    def test_detail_height(self) -> None:
        assert (
            "--detail-height:180px" in self.content
            or "--detail-height: 180px" in self.content
        )

    def test_row_height(self) -> None:
        assert (
            "--row-height:32px" in self.content or "--row-height: 32px" in self.content
        )


class TestStyleCssSpanColors:
    """Verify that span bar colors are present in style.css."""

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


@pytest.fixture
def static_html() -> str:
    return INDEX_HTML.read_text()


def test_no_acv_detail_in_body(static_html: str) -> None:
    """acv-detail must NOT appear in index.html body — it lives in timeline shadow DOM only."""
    assert "<acv-detail" not in static_html


class TestStyleCssLayout:
    def setup_method(self) -> None:
        self.content = STYLE_CSS.read_text()

    def test_box_sizing_reset(self) -> None:
        assert "box-sizing" in self.content

    def test_body_flex_column(self) -> None:
        assert (
            "flex-direction" in self.content or "flex-direction:column" in self.content
        )
        assert "column" in self.content

    def test_monospace_font(self) -> None:
        assert any(font in self.content for font in ["SF Mono", "Consolas", "Monaco"])

    def test_font_size_12px(self) -> None:
        assert "12px" in self.content

    def test_custom_scrollbar(self) -> None:
        assert "scrollbar" in self.content
