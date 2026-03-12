"""Tests for JSON renderer."""

import json
from pathlib import Path

from lens.models import (
    ArchitecturePattern,
    FileInfo,
    Language,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)
from lens.renderer.json_out import render_json


def _make_analysis() -> ProjectAnalysis:
    return ProjectAnalysis(
        root_path="/tmp/test",
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
        ),
        files=[
            FileInfo(
                path=Path("/tmp/test/app.py"),
                relative_path="app.py",
                language=Language.PYTHON,
                size_bytes=500,
                code_lines=50,
            ),
        ],
        architecture=ArchitecturePattern.CLI_TOOL,
    )


def test_render_json_string():
    analysis = _make_analysis()
    result = render_json(analysis)
    data = json.loads(result)
    assert data["version"] == "0.1.0"
    assert data["project"]["primaryLanguage"] == "Python"


def test_render_json_to_file(tmp_path):
    analysis = _make_analysis()
    out = tmp_path / "output.json"
    render_json(analysis, out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["stats"]["totalFiles"] == 5
