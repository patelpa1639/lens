"""Tests for hotspot analysis."""

from pathlib import Path

from lens.analyzer.hotspots import calculate_hotspots
from lens.models import FileInfo, GitFileHistory, Language, ModuleInfo


def test_calculate_hotspots_basic():
    files = [
        FileInfo(
            path=Path("/tmp/a.py"),
            relative_path="a.py",
            language=Language.PYTHON,
            size_bytes=1000,
            code_lines=100,
        ),
        FileInfo(
            path=Path("/tmp/b.py"),
            relative_path="b.py",
            language=Language.PYTHON,
            size_bytes=500,
            code_lines=50,
        ),
    ]
    git_history = [
        GitFileHistory(file_path="a.py", commit_count=20, contributors=["alice", "bob"]),
        GitFileHistory(file_path="b.py", commit_count=2, contributors=["alice"]),
    ]
    modules = [
        ModuleInfo(file_path="a.py", language=Language.PYTHON),
        ModuleInfo(file_path="b.py", language=Language.PYTHON),
    ]

    hotspots = calculate_hotspots(files, modules, git_history)
    assert len(hotspots) == 2
    # File with more commits should have higher score
    assert hotspots[0].file_path == "a.py"
    assert hotspots[0].score > hotspots[1].score


def test_calculate_hotspots_empty():
    hotspots = calculate_hotspots([], [], [])
    assert hotspots == []


def test_calculate_hotspots_no_git():
    files = [
        FileInfo(
            path=Path("/tmp/a.py"),
            relative_path="a.py",
            language=Language.PYTHON,
            size_bytes=1000,
            code_lines=100,
        ),
    ]
    hotspots = calculate_hotspots(files, [], [])
    assert len(hotspots) == 1
    assert hotspots[0].score >= 0
