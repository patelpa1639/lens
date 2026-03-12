"""Tests for size analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from lens.analyzer.size import analyze_size
from lens.models import FileInfo, Language


def _make_file(
    relative_path: str,
    language: Language,
    size_bytes: int,
    code_lines: int = 0,
    line_count: int = 0,
    blank_lines: int = 0,
    comment_lines: int = 0,
) -> FileInfo:
    return FileInfo(
        path=Path("/tmp/test") / relative_path,
        relative_path=relative_path,
        language=language,
        size_bytes=size_bytes,
        line_count=line_count,
        code_lines=code_lines,
        blank_lines=blank_lines,
        comment_lines=comment_lines,
    )


ROOT = Path("/tmp/test")

SAMPLE_FILES = [
    _make_file("src/main.py", Language.PYTHON, 1000, code_lines=40, line_count=50),
    _make_file("src/utils.py", Language.PYTHON, 500, code_lines=20, line_count=30),
    _make_file("lib/helper.js", Language.JAVASCRIPT, 800, code_lines=30, line_count=40),
    _make_file("lib/index.js", Language.JAVASCRIPT, 200, code_lines=10, line_count=15),
    _make_file("README.md", Language.MARKDOWN, 300, code_lines=0, line_count=20),
    _make_file("config.yaml", Language.YAML, 200, code_lines=0, line_count=10),
]


class TestTotalSize:
    def test_total_size_bytes(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        assert report.total_size_bytes == 3000

    def test_total_files(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        assert report.total_files == 6


class TestGroupByDirectory:
    def test_directory_names(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        names = {e.name for e in report.by_directory}
        assert names == {"src", "lib", "./"}

    def test_directory_sizes(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_directory}
        assert by_name["src"].size_bytes == 1500
        assert by_name["lib"].size_bytes == 1000
        assert by_name["./"].size_bytes == 500

    def test_directory_file_counts(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_directory}
        assert by_name["src"].file_count == 2
        assert by_name["lib"].file_count == 2
        assert by_name["./"].file_count == 2

    def test_directory_sorted_by_size_desc(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        sizes = [e.size_bytes for e in report.by_directory]
        assert sizes == sorted(sizes, reverse=True)

    def test_directory_code_lines(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_directory}
        assert by_name["src"].code_lines == 60
        assert by_name["lib"].code_lines == 40


class TestGroupByLanguage:
    def test_language_names(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        names = {e.name for e in report.by_language}
        assert names == {"Python", "JavaScript", "Markdown", "YAML"}

    def test_language_sizes(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_language}
        assert by_name["Python"].size_bytes == 1500
        assert by_name["JavaScript"].size_bytes == 1000

    def test_language_sorted_by_size_desc(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        sizes = [e.size_bytes for e in report.by_language]
        assert sizes == sorted(sizes, reverse=True)

    def test_language_code_lines(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_language}
        assert by_name["Python"].code_lines == 60
        assert by_name["JavaScript"].code_lines == 40


class TestGroupByExtension:
    def test_extension_names(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        names = {e.name for e in report.by_extension}
        assert names == {".py", ".js", ".md", ".yaml"}

    def test_extension_sizes(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_extension}
        assert by_name[".py"].size_bytes == 1500
        assert by_name[".js"].size_bytes == 1000

    def test_extension_sorted_by_size_desc(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        sizes = [e.size_bytes for e in report.by_extension]
        assert sizes == sorted(sizes, reverse=True)


class TestPercentages:
    def test_percentages_sum_to_100(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        dir_pct = sum(e.percentage for e in report.by_directory)
        lang_pct = sum(e.percentage for e in report.by_language)
        ext_pct = sum(e.percentage for e in report.by_extension)
        assert abs(dir_pct - 100.0) < 1.0
        assert abs(lang_pct - 100.0) < 1.0
        assert abs(ext_pct - 100.0) < 1.0

    def test_individual_percentages(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        by_name = {e.name: e for e in report.by_directory}
        assert by_name["src"].percentage == 50.0
        assert by_name["lib"].percentage == pytest.approx(33.3, abs=0.1)


class TestLargestFiles:
    def test_largest_files_sorted_desc(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        sizes = [s for _, s in report.largest_files]
        assert sizes == sorted(sizes, reverse=True)

    def test_largest_files_top_entry(self) -> None:
        report = analyze_size(SAMPLE_FILES, ROOT)
        path, size = report.largest_files[0]
        assert path == "src/main.py"
        assert size == 1000

    def test_largest_files_capped_at_10(self) -> None:
        many_files = [
            _make_file(f"src/f{i}.py", Language.PYTHON, 100 + i)
            for i in range(20)
        ]
        report = analyze_size(many_files, ROOT)
        assert len(report.largest_files) == 10


class TestEmptyProject:
    def test_empty_returns_zeros(self) -> None:
        report = analyze_size([], ROOT)
        assert report.total_size_bytes == 0
        assert report.total_files == 0
        assert report.by_directory == []
        assert report.by_language == []
        assert report.by_extension == []
        assert report.largest_files == []


class TestRootFiles:
    def test_files_in_root_grouped_under_dot_slash(self) -> None:
        files = [
            _make_file("setup.py", Language.PYTHON, 100),
            _make_file("README.md", Language.MARKDOWN, 200),
        ]
        report = analyze_size(files, ROOT)
        assert len(report.by_directory) == 1
        assert report.by_directory[0].name == "./"
        assert report.by_directory[0].file_count == 2
        assert report.by_directory[0].size_bytes == 300
