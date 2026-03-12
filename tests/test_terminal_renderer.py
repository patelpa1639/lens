"""Tests for terminal renderer."""

from io import StringIO
from pathlib import Path

from rich.console import Console

from lens.models import (
    ArchitecturePattern,
    FileInfo,
    Framework,
    HotspotInfo,
    Language,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)
from lens.renderer.terminal import render_terminal


def _make_analysis() -> ProjectAnalysis:
    return ProjectAnalysis(
        root_path="/tmp/myproject",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            languages={Language.PYTHON: 10},
            frameworks=[Framework.FLASK],
            package_manager="pip",
            has_tests=True,
            has_ci=True,
            has_docker=False,
        ),
        stats=ProjectStats(
            total_files=10,
            total_lines=500,
            code_lines=400,
            blank_lines=50,
            comment_lines=50,
            language_breakdown={"Python": 400},
            language_percentages={"Python": 100.0},
            file_count_by_language={"Python": 10},
            avg_file_size=1000,
            largest_files=[("big.py", 5000)],
        ),
        files=[
            FileInfo(
                path=Path("/tmp/myproject/app.py"),
                relative_path="app.py",
                language=Language.PYTHON,
                size_bytes=1000,
                code_lines=100,
            ),
        ],
        entry_points=["app.py"],
        external_deps=["flask", "sqlalchemy"],
        hotspots=[
            HotspotInfo(file_path="app.py", score=75.0, change_frequency=80, complexity=70, is_danger_zone=True),
        ],
        architecture=ArchitecturePattern.API_SERVICE,
        explanation="This is a Python API service using Flask.",
    )


def test_render_terminal_no_crash():
    analysis = _make_analysis()
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)
    render_terminal(analysis, console)
    text = output.getvalue()
    assert "LENS" in text
    assert "myproject" in text


def test_render_terminal_shows_stats():
    analysis = _make_analysis()
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)
    render_terminal(analysis, console)
    text = output.getvalue()
    assert "400" in text  # code lines
    assert "10" in text  # total files


def test_render_terminal_shows_entry_points():
    analysis = _make_analysis()
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)
    render_terminal(analysis, console)
    text = output.getvalue()
    assert "app.py" in text
