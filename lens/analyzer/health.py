"""Codebase health scoring — produces a 0-100 score with category breakdown."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from lens.models import ProjectAnalysis


@dataclass
class HealthCategory:
    """A single scored health category."""

    name: str
    score: float  # 0-100
    weight: float
    details: list[str] = field(default_factory=list)


@dataclass
class HealthReport:
    """Complete health report for a project."""

    overall_score: float  # 0-100
    grade: str  # A/B/C/D/F
    categories: list[HealthCategory] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def _score_to_grade(score: float) -> str:
    """Map a numeric score to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Category scorers
# ---------------------------------------------------------------------------

def _score_code_quality(analysis: ProjectAnalysis) -> HealthCategory:
    """Score code quality (comment ratio, function length, complexity)."""
    details: list[str] = []
    sub_scores: list[float] = []

    # --- Comment ratio ---
    total_code = analysis.stats.code_lines or 1
    total_comments = analysis.stats.comment_lines
    comment_ratio = total_comments / total_code

    if 0.10 <= comment_ratio <= 0.30:
        ratio_score = 100.0
    elif comment_ratio < 0.10:
        # Scale linearly: 0% → 0, 10% → 100
        ratio_score = max(0.0, (comment_ratio / 0.10) * 100.0)
    else:
        # Over-commented: 30% → 100, 60%+ → 0
        ratio_score = max(0.0, 100.0 - ((comment_ratio - 0.30) / 0.30) * 100.0)

    details.append(f"Comment ratio: {comment_ratio:.0%} (target 10-30%)")
    sub_scores.append(ratio_score)

    # --- Average function length (via complexity as a proxy) ---
    all_functions = []
    for mod in analysis.modules:
        all_functions.extend(mod.functions)
        for cls in mod.classes:
            all_functions.extend(cls.methods)

    if all_functions:
        avg_complexity = sum(f.complexity for f in all_functions) / len(all_functions)
        # Complexity of 1 is perfect; penalise above 10 heavily
        if avg_complexity <= 5:
            complexity_score = 100.0
        elif avg_complexity <= 10:
            complexity_score = 100.0 - ((avg_complexity - 5) / 5) * 50.0
        else:
            complexity_score = max(0.0, 50.0 - ((avg_complexity - 10) / 10) * 50.0)
        details.append(f"Avg function complexity: {avg_complexity:.1f}")
    else:
        complexity_score = 50.0  # Neutral when no data
        details.append("No functions detected for complexity analysis")

    sub_scores.append(complexity_score)

    # --- Large function penalty (files with many functions as proxy) ---
    func_count = len(all_functions)
    if func_count > 0:
        avg_lines_per_func = total_code / func_count
        if avg_lines_per_func <= 50:
            length_score = 100.0
        else:
            length_score = max(0.0, 100.0 - ((avg_lines_per_func - 50) / 50) * 100.0)
        details.append(f"Avg lines per function: {avg_lines_per_func:.0f} (target <=50)")
    else:
        length_score = 50.0
        details.append("No functions detected for length analysis")

    sub_scores.append(length_score)

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    return HealthCategory(name="Code Quality", score=_clamp(score), weight=0.25, details=details)


def _score_organization(analysis: ProjectAnalysis, root: Path) -> HealthCategory:
    """Score project organisation (file sizes, directory structure)."""
    details: list[str] = []
    sub_scores: list[float] = []

    # --- Consistent file sizes (low std-dev) ---
    line_counts = [f.line_count for f in analysis.files if f.line_count > 0]
    if len(line_counts) >= 2:
        mean = sum(line_counts) / len(line_counts)
        variance = sum((x - mean) ** 2 for x in line_counts) / len(line_counts)
        std_dev = math.sqrt(variance)
        # Normalise: std_dev 0 → 100, std_dev >= 500 → 0
        consistency_score = max(0.0, 100.0 - (std_dev / 500.0) * 100.0)
        details.append(f"File size std deviation: {std_dev:.0f} lines")
    else:
        consistency_score = 50.0
        details.append("Not enough files to assess size consistency")
    sub_scores.append(consistency_score)

    # --- Proper directory structure ---
    expected_dirs = {"src", "lib", "tests", "test", "docs", "doc"}
    existing = {p.name for p in root.iterdir() if p.is_dir()} if root.exists() else set()
    matched = expected_dirs & existing
    if matched:
        structure_score = min(100.0, len(matched) * 50.0)
        details.append(f"Standard directories found: {', '.join(sorted(matched))}")
    else:
        structure_score = 20.0
        details.append("No standard directories (src/, tests/, docs/) found")
    sub_scores.append(structure_score)

    # --- No extremely large files ---
    large_files = [f for f in analysis.files if f.line_count > 500]
    if not large_files:
        large_score = 100.0
        details.append("No files over 500 lines")
    else:
        penalty = min(100.0, len(large_files) * 20.0)
        large_score = 100.0 - penalty
        details.append(f"{len(large_files)} file(s) over 500 lines")
    sub_scores.append(large_score)

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    return HealthCategory(name="Organization", score=_clamp(score), weight=0.25, details=details)


def _score_testing(analysis: ProjectAnalysis) -> HealthCategory:
    """Score test coverage presence."""
    details: list[str] = []
    sub_scores: list[float] = []

    # --- Has test directory / files ---
    if analysis.detection.has_tests:
        sub_scores.append(100.0)
        details.append("Test directory/files detected")
    else:
        sub_scores.append(0.0)
        details.append("No test directory or files detected")

    # --- Test-to-code file ratio ---
    test_files = [f for f in analysis.files if _is_test_file(f.relative_path)]
    code_files = [f for f in analysis.files if not _is_test_file(f.relative_path)]
    if code_files:
        ratio = len(test_files) / len(code_files)
        if 0.5 <= ratio <= 1.0:
            ratio_score = 100.0
        elif ratio < 0.5:
            ratio_score = (ratio / 0.5) * 100.0
        else:
            ratio_score = 100.0  # More tests than code is fine
        details.append(f"Test-to-code file ratio: {ratio:.2f} (target 0.5-1.0)")
    else:
        ratio_score = 0.0
        details.append("No code files to compute test ratio")
    sub_scores.append(ratio_score)

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    return HealthCategory(name="Testing", score=_clamp(score), weight=0.20, details=details)


def _score_documentation(analysis: ProjectAnalysis, root: Path) -> HealthCategory:
    """Score documentation presence."""
    details: list[str] = []
    sub_scores: list[float] = []

    # --- Has README ---
    readme_patterns = ("README", "README.md", "README.rst", "readme.md")
    has_readme = any((root / name).exists() for name in readme_patterns) if root.exists() else False
    if has_readme:
        sub_scores.append(100.0)
        details.append("README found")
    else:
        sub_scores.append(0.0)
        details.append("No README found")

    # --- Docstrings in Python files ---
    py_files = [f for f in analysis.files if f.relative_path.endswith(".py")]
    if py_files:
        commented = [f for f in py_files if f.comment_lines > 0]
        docstring_ratio = len(commented) / len(py_files)
        docstring_score = docstring_ratio * 100.0
        details.append(f"{len(commented)}/{len(py_files)} Python files have docstrings/comments")
    else:
        docstring_score = 50.0  # Neutral for non-Python projects
        details.append("No Python files to check for docstrings")
    sub_scores.append(docstring_score)

    # --- Has config files ---
    config_names = (
        "pyproject.toml", "setup.py", "setup.cfg",
        "package.json", "Cargo.toml", "go.mod",
        "Makefile", "Gemfile",
    )
    found_configs = [name for name in config_names if (root / name).exists()] if root.exists() else []
    if found_configs:
        sub_scores.append(100.0)
        details.append(f"Config files: {', '.join(found_configs)}")
    else:
        sub_scores.append(0.0)
        details.append("No project config files found")

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    return HealthCategory(name="Documentation", score=_clamp(score), weight=0.15, details=details)


def _score_maintenance(analysis: ProjectAnalysis, root: Path) -> HealthCategory:
    """Score maintenance hygiene."""
    details: list[str] = []
    sub_scores: list[float] = []

    # --- Has CI/CD config ---
    if analysis.detection.has_ci:
        sub_scores.append(100.0)
        details.append("CI/CD configuration detected")
    else:
        sub_scores.append(0.0)
        details.append("No CI/CD configuration detected")

    # --- Has .gitignore ---
    has_gitignore = (root / ".gitignore").exists() if root.exists() else False
    if has_gitignore:
        sub_scores.append(100.0)
        details.append(".gitignore found")
    else:
        sub_scores.append(0.0)
        details.append("No .gitignore found")

    # --- Has Docker setup ---
    if analysis.detection.has_docker:
        sub_scores.append(100.0)
        details.append("Docker setup detected")
    else:
        sub_scores.append(0.0)
        details.append("No Docker setup detected")

    # --- No circular dependencies ---
    if not analysis.circular_deps:
        sub_scores.append(100.0)
        details.append("No circular dependencies detected")
    else:
        # Penalise proportionally
        penalty = min(100.0, len(analysis.circular_deps) * 25.0)
        sub_scores.append(100.0 - penalty)
        details.append(f"{len(analysis.circular_deps)} circular dependency chain(s) found")

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    return HealthCategory(name="Maintenance", score=_clamp(score), weight=0.15, details=details)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _is_test_file(relative_path: str) -> bool:
    parts = relative_path.replace("\\", "/").split("/")
    basename = parts[-1] if parts else ""
    # Path contains test dir or file starts with test_
    return (
        any(p in ("tests", "test", "__tests__", "spec") for p in parts)
        or basename.startswith("test_")
        or basename.endswith("_test.py")
        or basename.endswith(".test.js")
        or basename.endswith(".test.ts")
        or basename.endswith(".spec.js")
        or basename.endswith(".spec.ts")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _build_recommendations(categories: list[HealthCategory]) -> list[str]:
    """Generate actionable recommendations from category scores."""
    recs: list[str] = []
    for cat in categories:
        if cat.score < 50:
            if cat.name == "Testing":
                recs.append("Add a test suite — aim for at least one test file per source module.")
            elif cat.name == "Documentation":
                recs.append("Add a README and docstrings to improve documentation.")
            elif cat.name == "Maintenance":
                recs.append("Set up CI/CD, add a .gitignore, and consider Docker for reproducibility.")
            elif cat.name == "Organization":
                recs.append("Break large files into smaller modules and adopt a standard directory layout.")
            elif cat.name == "Code Quality":
                recs.append("Reduce function complexity and improve comment coverage.")
        elif cat.score < 75:
            if cat.name == "Testing":
                recs.append("Increase test coverage — target a 0.5-1.0 test-to-code file ratio.")
            elif cat.name == "Documentation":
                recs.append("Expand documentation with more docstrings and a comprehensive README.")
    return recs


def calculate_health(analysis: ProjectAnalysis, root: Path) -> HealthReport:
    """Calculate a health score 0-100 with category breakdown.

    Parameters
    ----------
    analysis:
        A fully populated ``ProjectAnalysis`` from the Lens engine.
    root:
        The project root directory on disk.

    Returns
    -------
    HealthReport
        Overall score, letter grade, per-category scores and recommendations.
    """
    categories = [
        _score_code_quality(analysis),
        _score_organization(analysis, root),
        _score_testing(analysis),
        _score_documentation(analysis, root),
        _score_maintenance(analysis, root),
    ]

    overall = sum(cat.score * cat.weight for cat in categories)
    overall = _clamp(overall)
    grade = _score_to_grade(overall)
    recommendations = _build_recommendations(categories)

    return HealthReport(
        overall_score=round(overall, 1),
        grade=grade,
        categories=categories,
        recommendations=recommendations,
    )
