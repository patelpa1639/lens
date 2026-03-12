"""Tests for entry point detection."""

from pathlib import Path

from lens.analyzer.entry_points import find_entry_points
from lens.models import FunctionInfo, Language, ModuleInfo


def test_find_entry_points_by_name():
    modules = [
        ModuleInfo(file_path="main.py", language=Language.PYTHON),
        ModuleInfo(file_path="utils.py", language=Language.PYTHON),
        ModuleInfo(file_path="app.py", language=Language.PYTHON),
    ]
    eps = find_entry_points(modules, Path("/tmp"))
    assert "main.py" in eps
    assert "app.py" in eps
    assert "utils.py" not in eps


def test_find_entry_points_by_flag():
    modules = [
        ModuleInfo(file_path="custom.py", language=Language.PYTHON, entry_point=True),
        ModuleInfo(file_path="other.py", language=Language.PYTHON, entry_point=False),
    ]
    eps = find_entry_points(modules, Path("/tmp"))
    assert "custom.py" in eps
    assert "other.py" not in eps


def test_find_entry_points_routes():
    modules = [
        ModuleInfo(
            file_path="routes.py",
            language=Language.PYTHON,
            functions=[
                FunctionInfo(
                    name="get_users",
                    file_path="routes.py",
                    line_number=1,
                    decorators=["app.route"],
                )
            ],
        ),
    ]
    eps = find_entry_points(modules, Path("/tmp"))
    assert "routes.py" in eps


def test_find_entry_points_empty():
    eps = find_entry_points([], Path("/tmp"))
    assert eps == []
