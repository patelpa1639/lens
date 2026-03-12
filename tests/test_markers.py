"""Tests for marker (TODO/FIXME/HACK) scanning."""

from __future__ import annotations

from pathlib import Path

import pytest

from lens.analyzer.markers import scan_markers


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a small temporary project with various marker comments."""
    # Python file with TODO and FIXME
    py_file = tmp_path / "app.py"
    py_file.write_text(
        "# TODO: refactor this function\n"
        "def greet():\n"
        "    # FIXME: handle edge case\n"
        "    print('hello')\n"
        "    # NOTE: greeting is hardcoded\n"
        "    return True\n",
        encoding="utf-8",
    )

    # JavaScript file with various markers in // and /* comments
    js_file = tmp_path / "index.js"
    js_file.write_text(
        "// HACK: temporary workaround\n"
        "function init() {\n"
        "  /* BUG: race condition here */\n"
        "  // XXX: needs investigation\n"
        "  console.log('start');\n"
        "}\n",
        encoding="utf-8",
    )

    # File with inline TODO inside a string (should still be found)
    str_file = tmp_path / "notes.py"
    str_file.write_text(
        "msg = 'TODO: remember to update docs'\n"
        "# OPTIMIZE: use caching here\n"
        "data = load()\n",
        encoding="utf-8",
    )

    # A sub-directory with another file
    sub = tmp_path / "lib"
    sub.mkdir()
    (sub / "helpers.py").write_text(
        "# todo: lowercase marker test\n"
        "def helper():\n"
        "    pass\n",
        encoding="utf-8",
    )

    return tmp_path


def test_finds_todos_in_python(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    py_markers = [m for m in report.markers if m.file_path == "app.py"]
    types = {m.marker_type for m in py_markers}
    assert "TODO" in types
    assert "FIXME" in types
    assert "NOTE" in types
    assert len(py_markers) == 3


def test_finds_fixmes_in_js(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    js_markers = [m for m in report.markers if m.file_path == "index.js"]
    types = {m.marker_type for m in js_markers}
    assert "HACK" in types
    assert "BUG" in types
    assert "XXX" in types
    assert len(js_markers) == 3


def test_severity_classification(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)

    critical = [m for m in report.markers if m.severity == "critical"]
    warning = [m for m in report.markers if m.severity == "warning"]
    info = [m for m in report.markers if m.severity == "info"]

    # FIXME, BUG, XXX -> critical
    critical_types = {m.marker_type for m in critical}
    assert critical_types <= {"FIXME", "BUG", "XXX"}

    # TODO, HACK, OPTIMIZE -> warning
    warning_types = {m.marker_type for m in warning}
    assert warning_types <= {"TODO", "HACK", "OPTIMIZE"}

    # NOTE -> info
    info_types = {m.marker_type for m in info}
    assert info_types <= {"NOTE"}


def test_grouping_by_file(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    assert "app.py" in report.by_file
    assert "index.js" in report.by_file
    assert len(report.by_file["app.py"]) == 3
    assert len(report.by_file["index.js"]) == 3


def test_counting_by_type(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    # At least one TODO from app.py and one from notes.py (string) and one lowercase from lib/
    assert report.by_type.get("TODO", 0) >= 2
    assert report.by_type.get("FIXME", 0) >= 1
    assert report.by_type.get("HACK", 0) >= 1
    assert report.by_type.get("BUG", 0) >= 1
    assert report.by_type.get("XXX", 0) >= 1
    assert report.by_type.get("NOTE", 0) >= 1
    assert report.by_type.get("OPTIMIZE", 0) >= 1


def test_non_comment_todo_in_string_found(tmp_project: Path) -> None:
    """TODOs inside string literals are still detected (line-level match)."""
    report = scan_markers(tmp_project)
    notes_markers = [m for m in report.markers if m.file_path == "notes.py"]
    types = {m.marker_type for m in notes_markers}
    assert "TODO" in types
    assert "OPTIMIZE" in types
    assert len(notes_markers) == 2


def test_case_insensitive_matching(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    lib_markers = [m for m in report.markers if "helpers.py" in m.file_path]
    assert len(lib_markers) == 1
    assert lib_markers[0].marker_type == "TODO"


def test_total_count(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    assert report.total_count == len(report.markers)
    assert report.total_count >= 9  # 3 + 3 + 2 + 1


def test_by_severity_sums(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    total_from_severity = sum(report.by_severity.values())
    assert total_from_severity == report.total_count


def test_empty_directory(tmp_path: Path) -> None:
    report = scan_markers(tmp_path)
    assert report.total_count == 0
    assert report.markers == []
    assert report.by_severity == {}
    assert report.by_type == {}
    assert report.by_file == {}


def test_context_includes_surrounding_lines(tmp_project: Path) -> None:
    report = scan_markers(tmp_project)
    # The FIXME on line 3 of app.py should have context including lines 2 and 4
    fixme = [m for m in report.markers if m.marker_type == "FIXME" and m.file_path == "app.py"]
    assert len(fixme) == 1
    assert "def greet():" in fixme[0].context
    assert "print('hello')" in fixme[0].context
