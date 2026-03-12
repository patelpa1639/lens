"""Tests for the health scoring module."""

from __future__ import annotations

from pathlib import Path

import pytest

from lens.analyzer.health import calculate_health
from lens.models import (
    FileInfo,
    FunctionInfo,
    Language,
    ModuleInfo,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)

# ---------------------------------------------------------------------------
# Helpers to build fake analyses
# ---------------------------------------------------------------------------

def _make_file(relative: str, *, line_count: int = 100, code_lines: int = 80,
               comment_lines: int = 15, language: Language = Language.PYTHON) -> FileInfo:
    return FileInfo(
        path=Path(relative),
        relative_path=relative,
        language=language,
        size_bytes=line_count * 40,
        line_count=line_count,
        blank_lines=line_count - code_lines - comment_lines,
        comment_lines=comment_lines,
        code_lines=code_lines,
    )


def _make_function(name: str, complexity: int = 2) -> FunctionInfo:
    return FunctionInfo(name=name, file_path="src/app.py", line_number=1, complexity=complexity)


def _make_module(file_path: str, functions: list[FunctionInfo] | None = None) -> ModuleInfo:
    return ModuleInfo(
        file_path=file_path,
        language=Language.PYTHON,
        functions=functions or [],
    )


def _perfect_analysis() -> ProjectAnalysis:
    """Build an analysis that should score very high."""
    files = [
        _make_file("src/app.py", line_count=100, code_lines=80, comment_lines=15),
        _make_file("src/models.py", line_count=80, code_lines=60, comment_lines=12),
        _make_file("src/utils.py", line_count=60, code_lines=45, comment_lines=8),
        _make_file("tests/test_app.py", line_count=50, code_lines=40, comment_lines=5),
        _make_file("tests/test_models.py", line_count=40, code_lines=30, comment_lines=5),
    ]
    functions = [_make_function(f"func_{i}", complexity=2) for i in range(10)]
    modules = [_make_module("src/app.py", functions=functions)]
    return ProjectAnalysis(
        root_path="/fake",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            has_tests=True,
            has_ci=True,
            has_docker=True,
            has_docs=True,
        ),
        stats=ProjectStats(
            total_files=5,
            total_lines=330,
            code_lines=255,
            comment_lines=45,
            blank_lines=30,
            language_breakdown={"Python": 330},
            largest_files=[("src/app.py", 100)],
        ),
        files=files,
        modules=modules,
        circular_deps=[],
    )


def _no_tests_analysis() -> ProjectAnalysis:
    """Build an analysis with no tests."""
    files = [
        _make_file("src/app.py"),
        _make_file("src/models.py"),
    ]
    functions = [_make_function(f"func_{i}") for i in range(5)]
    modules = [_make_module("src/app.py", functions=functions)]
    return ProjectAnalysis(
        root_path="/fake",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            has_tests=False,
            has_ci=True,
            has_docker=True,
            has_docs=True,
        ),
        stats=ProjectStats(
            total_files=2,
            total_lines=200,
            code_lines=160,
            comment_lines=30,
            blank_lines=10,
            language_breakdown={"Python": 200},
            largest_files=[("src/app.py", 100)],
        ),
        files=files,
        modules=modules,
        circular_deps=[],
    )


def _no_docs_analysis() -> ProjectAnalysis:
    """Build an analysis with no documentation."""
    files = [
        _make_file("src/app.py", comment_lines=0, code_lines=95),
        _make_file("src/models.py", comment_lines=0, code_lines=95),
    ]
    functions = [_make_function(f"func_{i}") for i in range(5)]
    modules = [_make_module("src/app.py", functions=functions)]
    return ProjectAnalysis(
        root_path="/fake",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            has_tests=True,
            has_ci=True,
            has_docker=True,
            has_docs=False,
        ),
        stats=ProjectStats(
            total_files=2,
            total_lines=200,
            code_lines=190,
            comment_lines=0,
            blank_lines=10,
            language_breakdown={"Python": 200},
            largest_files=[("src/app.py", 100)],
        ),
        files=files,
        modules=modules,
        circular_deps=[],
    )


# ---------------------------------------------------------------------------
# Fixtures that set up a fake project root with the right files on disk
# ---------------------------------------------------------------------------

@pytest.fixture
def perfect_root(tmp_path: Path) -> Path:
    """Create a project root with all expected files/dirs."""
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / ".gitignore").write_text("__pycache__/\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"x\"\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    return tmp_path


@pytest.fixture
def bare_root(tmp_path: Path) -> Path:
    """Create a project root with almost nothing on disk."""
    (tmp_path / "src").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPerfectProject:
    def test_gets_a_grade(self, perfect_root: Path) -> None:
        report = calculate_health(_perfect_analysis(), perfect_root)
        assert report.grade == "A", f"Expected A, got {report.grade} (score={report.overall_score})"

    def test_score_within_range(self, perfect_root: Path) -> None:
        report = calculate_health(_perfect_analysis(), perfect_root)
        assert 0 <= report.overall_score <= 100


class TestNoTests:
    def test_penalised(self, perfect_root: Path) -> None:
        perfect_report = calculate_health(_perfect_analysis(), perfect_root)
        no_test_report = calculate_health(_no_tests_analysis(), perfect_root)
        assert no_test_report.overall_score < perfect_report.overall_score

    def test_testing_category_low(self, perfect_root: Path) -> None:
        report = calculate_health(_no_tests_analysis(), perfect_root)
        testing = next(c for c in report.categories if c.name == "Testing")
        assert testing.score < 50


class TestNoDocs:
    def test_penalised(self, perfect_root: Path) -> None:
        perfect_report = calculate_health(_perfect_analysis(), perfect_root)
        no_docs_report = calculate_health(_no_docs_analysis(), perfect_root)
        assert no_docs_report.overall_score < perfect_report.overall_score

    def test_doc_category_lower(self, bare_root: Path) -> None:
        """With no README and no config on disk, documentation should be low."""
        report = calculate_health(_no_docs_analysis(), bare_root)
        doc = next(c for c in report.categories if c.name == "Documentation")
        assert doc.score < 50


class TestScoreRange:
    def test_always_0_to_100(self, perfect_root: Path) -> None:
        for builder in (_perfect_analysis, _no_tests_analysis, _no_docs_analysis):
            report = calculate_health(builder(), perfect_root)
            assert 0 <= report.overall_score <= 100, f"Out of range: {report.overall_score}"

    def test_categories_0_to_100(self, perfect_root: Path) -> None:
        report = calculate_health(_perfect_analysis(), perfect_root)
        for cat in report.categories:
            assert 0 <= cat.score <= 100, f"{cat.name} out of range: {cat.score}"


class TestCategoriesWeights:
    def test_weights_sum_to_one(self, perfect_root: Path) -> None:
        report = calculate_health(_perfect_analysis(), perfect_root)
        total_weight = sum(c.weight for c in report.categories)
        assert abs(total_weight - 1.0) < 1e-9

    def test_overall_is_weighted_sum(self, perfect_root: Path) -> None:
        report = calculate_health(_perfect_analysis(), perfect_root)
        expected = sum(c.score * c.weight for c in report.categories)
        assert abs(report.overall_score - round(expected, 1)) < 0.2


class TestGradeBoundaries:
    @pytest.mark.parametrize("score,grade", [
        (95, "A"), (90, "A"),
        (85, "B"), (80, "B"),
        (75, "C"), (70, "C"),
        (65, "D"), (60, "D"),
        (55, "F"), (0, "F"),
    ])
    def test_grade_mapping(self, score: float, grade: str) -> None:
        from lens.analyzer.health import _score_to_grade
        assert _score_to_grade(score) == grade


class TestRecommendations:
    def test_no_tests_gets_recommendation(self, perfect_root: Path) -> None:
        report = calculate_health(_no_tests_analysis(), perfect_root)
        assert any("test" in r.lower() for r in report.recommendations)

    def test_perfect_has_few_recommendations(self, perfect_root: Path) -> None:
        report = calculate_health(_perfect_analysis(), perfect_root)
        # A perfect project may still get minor recommendations, but not many
        assert len(report.recommendations) <= 2


class TestCircularDeps:
    def test_circular_deps_penalise_maintenance(self, perfect_root: Path) -> None:
        analysis = _perfect_analysis()
        analysis.circular_deps = [["a.py", "b.py", "a.py"], ["c.py", "d.py", "c.py"]]
        report = calculate_health(analysis, perfect_root)
        maint = next(c for c in report.categories if c.name == "Maintenance")
        clean_report = calculate_health(_perfect_analysis(), perfect_root)
        clean_maint = next(c for c in clean_report.categories if c.name == "Maintenance")
        assert maint.score < clean_maint.score
