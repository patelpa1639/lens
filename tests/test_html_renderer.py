"""Tests for HTML renderer."""

from pathlib import Path

from lens.models import (
    ArchitecturePattern,
    FileInfo,
    Language,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)
from lens.renderer.html import render_html


def _make_analysis() -> ProjectAnalysis:
    return ProjectAnalysis(
        root_path="/tmp/testproject",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            languages={Language.PYTHON: 5},
            package_manager="pip",
        ),
        stats=ProjectStats(
            total_files=5,
            total_lines=200,
            code_lines=150,
            language_breakdown={"Python": 150},
            language_percentages={"Python": 100.0},
            file_count_by_language={"Python": 5},
        ),
        files=[
            FileInfo(
                path=Path("/tmp/testproject/main.py"),
                relative_path="main.py",
                language=Language.PYTHON,
                size_bytes=500,
                code_lines=50,
            ),
        ],
        architecture=ArchitecturePattern.CLI_TOOL,
        explanation="A simple Python CLI tool.",
    )


def test_render_html_creates_file(tmp_path):
    analysis = _make_analysis()
    output = tmp_path / "report.html"
    result = render_html(analysis, output)
    assert result == output
    assert output.exists()


def test_render_html_self_contained(tmp_path):
    analysis = _make_analysis()
    output = tmp_path / "report.html"
    render_html(analysis, output)
    content = output.read_text()
    # Must be self-contained
    assert "<style>" in content
    assert "<script>" in content
    assert "<!DOCTYPE html>" in content


def test_render_html_contains_data(tmp_path):
    analysis = _make_analysis()
    output = tmp_path / "report.html"
    render_html(analysis, output)
    content = output.read_text()
    assert "testproject" in content
    assert "Python" in content


def test_render_html_no_xss(tmp_path):
    """Verify project names are escaped in HTML."""
    analysis = _make_analysis()
    analysis.root_path = "/tmp/<script>alert(1)</script>"
    output = tmp_path / "report.html"
    render_html(analysis, output)
    content = output.read_text()
    # The raw script tag should be escaped
    assert "<script>alert(1)</script>" not in content.split("</style>")[0]


def test_render_html_default_path():
    analysis = _make_analysis()
    result = render_html(analysis)
    assert result == Path("lens-report.html")
    # Cleanup
    Path("lens-report.html").unlink(missing_ok=True)
