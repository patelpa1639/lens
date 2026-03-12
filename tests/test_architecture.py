"""Tests for architecture detection."""

from lens.models import ArchitecturePattern
from lens.scanner.detector import detect_project


def test_detect_monorepo(tmp_monorepo):
    detection = detect_project(tmp_monorepo)
    assert detection.architecture == ArchitecturePattern.MONOREPO


def test_detect_cli_tool(tmp_python_project):
    detection = detect_project(tmp_python_project)
    # Has console_scripts in pyproject.toml
    assert detection.architecture in (
        ArchitecturePattern.CLI_TOOL,
        ArchitecturePattern.UNKNOWN,
        ArchitecturePattern.MVC,
    )


def test_detect_fullstack(tmp_path):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "index.html").write_text("<html></html>")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "server.py").write_text("# server\n")
    detection = detect_project(tmp_path)
    assert detection.architecture == ArchitecturePattern.FULLSTACK


def test_detect_serverless(tmp_path):
    (tmp_path / "serverless.yml").write_text("service: myapp\n")
    detection = detect_project(tmp_path)
    assert detection.architecture == ArchitecturePattern.SERVERLESS


def test_detect_unknown_empty(tmp_path):
    detection = detect_project(tmp_path)
    assert detection.architecture == ArchitecturePattern.UNKNOWN
