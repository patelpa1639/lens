"""Tests for Markdown renderer."""


from lens.models import (
    ArchitecturePattern,
    DependencyEdge,
    HotspotInfo,
    Language,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)
from lens.renderer.markdown import render_markdown


def _make_analysis() -> ProjectAnalysis:
    return ProjectAnalysis(
        root_path="/tmp/test",
        detection=ProjectDetection(
            primary_language=Language.PYTHON,
            languages={Language.PYTHON: 5},
        ),
        stats=ProjectStats(
            total_files=5,
            total_lines=200,
            code_lines=150,
            language_breakdown={"Python": 150},
            language_percentages={"Python": 100.0},
        ),
        entry_points=["main.py"],
        dependencies=[
            DependencyEdge(source="main.py", target="utils.py", import_names=["helper"]),
        ],
        external_deps=["click", "rich"],
        hotspots=[
            HotspotInfo(file_path="main.py", score=50.0),
        ],
        architecture=ArchitecturePattern.CLI_TOOL,
        explanation="A Python CLI tool.",
    )


def test_render_markdown_string():
    analysis = _make_analysis()
    result = render_markdown(analysis)
    assert "# test" in result
    assert "Python" in result
    assert "main.py" in result


def test_render_markdown_mermaid():
    analysis = _make_analysis()
    result = render_markdown(analysis)
    assert "```mermaid" in result


def test_render_markdown_to_file(tmp_path):
    analysis = _make_analysis()
    out = tmp_path / "output.md"
    render_markdown(analysis, out)
    assert out.exists()
    content = out.read_text()
    assert "# test" in content
