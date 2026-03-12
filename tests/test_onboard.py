"""Tests for onboard renderer."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

from lens.models import (
    ArchitecturePattern,
    DependencyEdge,
    FileInfo,
    Framework,
    HotspotInfo,
    Language,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)
from lens.renderer.onboard import render_onboard


def _make_analysis(tmp_path: Path | None = None) -> ProjectAnalysis:
    root = str(tmp_path) if tmp_path else "/tmp/myproject"
    return ProjectAnalysis(
        root_path=root,
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            frameworks=[Framework.FLASK],
            has_tests=True,
            has_ci=True,
            has_docker=False,
        ),
        stats=ProjectStats(total_files=10, code_lines=500),
        files=[
            FileInfo(
                path=Path(root) / "myapp" / "cli.py",
                relative_path="myapp/cli.py",
                language=Language.PYTHON,
                size_bytes=800,
                code_lines=60,
            ),
            FileInfo(
                path=Path(root) / "myapp" / "app.py",
                relative_path="myapp/app.py",
                language=Language.PYTHON,
                size_bytes=1200,
                code_lines=100,
            ),
            FileInfo(
                path=Path(root) / "tests" / "test_app.py",
                relative_path="tests/test_app.py",
                language=Language.PYTHON,
                size_bytes=600,
                code_lines=40,
            ),
        ],
        entry_points=["myapp/cli.py", "myapp/app.py"],
        external_deps=["flask", "sqlalchemy", "pytest"],
        dependencies=[
            DependencyEdge(source="myapp/cli.py", target="myapp/app.py"),
            DependencyEdge(source="myapp/app.py", target="myapp/models.py"),
            DependencyEdge(source="myapp/cli.py", target="myapp/models.py"),
        ],
        hotspots=[
            HotspotInfo(
                file_path="myapp/app.py",
                score=65.0,
                change_frequency=70,
                complexity=60,
                is_danger_zone=False,
            ),
        ],
        architecture=ArchitecturePattern.CLI_TOOL,
        explanation="This is a Python CLI tool using Flask.",
    )


def _capture(analysis: ProjectAnalysis) -> str:
    """Render onboard and capture output as string."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)
    render_onboard(analysis, console)
    return output.getvalue()


def test_render_onboard_no_crash():
    """Renders without error on a mock ProjectAnalysis."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert len(text) > 0


def test_contains_project_name():
    """Output contains the project name."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "myproject" in text


def test_shows_entry_points():
    """Output shows entry points."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "cli.py" in text
    assert "app.py" in text


def test_shows_external_dependencies():
    """Output shows external dependencies."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "flask" in text
    assert "sqlalchemy" in text


def test_shows_internal_dependencies():
    """Output shows internal dependency targets."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "myapp/models.py" in text


def test_shows_architecture():
    """Output shows architecture pattern."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "CLI Tool" in text


def test_shows_explanation():
    """Output shows the explanation text."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "Python CLI tool using Flask" in text


def test_shows_tips():
    """Output shows contextual tips."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "pytest" in text
    assert "CI/CD" in text


def test_shows_structure():
    """Output shows project structure directories."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "myapp" in text
    assert "tests" in text


def test_shows_step_labels():
    """Output includes step labels."""
    analysis = _make_analysis()
    text = _capture(analysis)
    assert "Step 1 of 6" in text
    assert "Step 6 of 6" in text


def test_minimal_analysis():
    """Works with minimal/empty analysis."""
    analysis = ProjectAnalysis(
        root_path="/tmp/empty",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
        ),
        stats=ProjectStats(),
    )
    text = _capture(analysis)
    assert "empty" in text
    assert "Step 1 of 6" in text
    # Should still render all 6 steps without crashing
    assert "Step 6 of 6" in text


def test_with_tmp_path(tmp_path: Path):
    """Works with a real tmp_path from pytest."""
    analysis = _make_analysis(tmp_path)
    text = _capture(analysis)
    assert len(text) > 0


def test_no_entry_points():
    """Renders gracefully when there are no entry points."""
    analysis = ProjectAnalysis(
        root_path="/tmp/noentry",
        detection=ProjectDetection(
            primary_language=Language.GO,
        ),
        stats=ProjectStats(total_files=5, code_lines=200),
    )
    text = _capture(analysis)
    assert "No entry points" in text


def test_docker_tip():
    """Shows Docker tip when has_docker is True."""
    analysis = ProjectAnalysis(
        root_path="/tmp/dockerproject",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            has_docker=True,
        ),
        stats=ProjectStats(),
    )
    text = _capture(analysis)
    assert "Docker" in text


def test_language_specific_test_commands():
    """Shows correct test command per language."""
    for lang, expected_cmd in [
        (Language.PYTHON, "pytest"),
        (Language.JAVASCRIPT, "npm test"),
        (Language.GO, "go test"),
        (Language.RUST, "cargo test"),
    ]:
        analysis = ProjectAnalysis(
            root_path="/tmp/langtest",
            detection=ProjectDetection(
                primary_language=lang,
                has_tests=True,
            ),
            stats=ProjectStats(),
        )
        text = _capture(analysis)
        assert expected_cmd in text, f"Expected '{expected_cmd}' for {lang.value}"
