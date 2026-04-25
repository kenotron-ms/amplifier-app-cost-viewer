"""Tests for package scaffold structure — written FIRST before files exist (TDD RED)."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).parent.parent  # viewer/
PKG = BASE / "amplifier_app_cost_viewer"
TESTS = BASE / "tests"


class TestFilesExist:
    def test_pyproject_toml_exists(self):
        assert (BASE / "pyproject.toml").exists(), "viewer/pyproject.toml must exist"

    def test_init_py_exists(self):
        assert (PKG / "__init__.py").exists(), (
            "amplifier_app_cost_viewer/__init__.py must exist"
        )

    def test_main_py_exists(self):
        assert (PKG / "__main__.py").exists(), (
            "amplifier_app_cost_viewer/__main__.py must exist"
        )

    def test_tests_init_exists(self):
        assert (TESTS / "__init__.py").exists(), "tests/__init__.py must exist"


class TestPyprojectToml:
    def test_project_name(self):
        content = (BASE / "pyproject.toml").read_text()
        assert 'name = "amplifier-app-cost-viewer"' in content

    def test_version(self):
        content = (BASE / "pyproject.toml").read_text()
        assert 'version = "0.1.0"' in content

    def test_python_requires(self):
        content = (BASE / "pyproject.toml").read_text()
        assert ">=3.11" in content

    def test_fastapi_dependency(self):
        content = (BASE / "pyproject.toml").read_text()
        assert "fastapi>=0.115" in content

    def test_uvicorn_dependency(self):
        content = (BASE / "pyproject.toml").read_text()
        assert "uvicorn[standard]>=0.32" in content

    def test_entry_point(self):
        content = (BASE / "pyproject.toml").read_text()
        assert "amplifier-cost-viewer" in content
        assert "amplifier_app_cost_viewer.__main__:main" in content

    def test_wheel_packages(self):
        content = (BASE / "pyproject.toml").read_text()
        assert "amplifier_app_cost_viewer" in content

    def test_hatchling_build_system(self):
        content = (BASE / "pyproject.toml").read_text()
        assert "hatchling" in content

    def test_pytest_testpaths(self):
        content = (BASE / "pyproject.toml").read_text()
        assert 'testpaths = ["tests"]' in content

    def test_asyncio_mode_auto(self):
        content = (BASE / "pyproject.toml").read_text()
        assert 'asyncio_mode = "auto"' in content

    def test_asyncio_fixture_loop_scope(self):
        content = (BASE / "pyproject.toml").read_text()
        assert 'asyncio_default_fixture_loop_scope = "function"' in content


class TestInitPy:
    def test_docstring_content(self):
        content = (PKG / "__init__.py").read_text()
        assert "Amplifier session cost and performance viewer." in content


class TestMainPy:
    def test_argparse_host(self):
        content = (PKG / "__main__.py").read_text()
        assert "--host" in content
        assert "127.0.0.1" in content

    def test_argparse_port(self):
        content = (PKG / "__main__.py").read_text()
        assert "--port" in content
        assert "8181" in content

    def test_uvicorn_app_reference(self):
        content = (PKG / "__main__.py").read_text()
        assert "amplifier_app_cost_viewer.server:app" in content

    def test_reload_false(self):
        content = (PKG / "__main__.py").read_text()
        assert "reload=False" in content

    def test_main_guard(self):
        content = (PKG / "__main__.py").read_text()
        assert 'if __name__ == "__main__"' in content
        assert "main()" in content

    def test_main_function_defined(self):
        content = (PKG / "__main__.py").read_text()
        assert "def main(" in content


class TestImportability:
    def test_package_importable(self):
        """Package must be importable after installation."""
        if "amplifier_app_cost_viewer" in sys.modules:
            del sys.modules["amplifier_app_cost_viewer"]
        import amplifier_app_cost_viewer  # noqa: F401

        assert amplifier_app_cost_viewer.__doc__ is not None

    def test_package_docstring(self):
        import amplifier_app_cost_viewer

        doc = amplifier_app_cost_viewer.__doc__ or ""
        assert "Amplifier session cost and performance viewer." in doc
