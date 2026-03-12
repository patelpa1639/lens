"""Tests for statistics calculation."""

from pathlib import Path

from lens.analyzer.stats import calculate_stats
from lens.models import FileInfo, Language


def test_calculate_stats_basic():
    files = [
        FileInfo(
            path=Path("/tmp/a.py"),
            relative_path="a.py",
            language=Language.PYTHON,
            size_bytes=1000,
            line_count=100,
            code_lines=80,
            blank_lines=10,
            comment_lines=10,
        ),
        FileInfo(
            path=Path("/tmp/b.js"),
            relative_path="b.js",
            language=Language.JAVASCRIPT,
            size_bytes=500,
            line_count=50,
            code_lines=40,
            blank_lines=5,
            comment_lines=5,
        ),
    ]
    stats = calculate_stats(files)
    assert stats.total_files == 2
    assert stats.total_lines == 150
    assert stats.code_lines == 120
    assert stats.blank_lines == 15
    assert stats.comment_lines == 15
    assert "Python" in stats.language_breakdown
    assert "JavaScript" in stats.language_breakdown
    assert stats.language_percentages["Python"] > stats.language_percentages["JavaScript"]
    assert len(stats.largest_files) == 2
    assert stats.largest_files[0][0] == "a.py"


def test_calculate_stats_empty():
    stats = calculate_stats([])
    assert stats.total_files == 0
    assert stats.total_lines == 0
    assert stats.code_lines == 0


def test_calculate_stats_single_language():
    files = [
        FileInfo(
            path=Path("/tmp/a.py"),
            relative_path="a.py",
            language=Language.PYTHON,
            size_bytes=100,
            line_count=10,
            code_lines=8,
            blank_lines=1,
            comment_lines=1,
        ),
    ]
    stats = calculate_stats(files)
    assert stats.language_percentages["Python"] == 100.0
