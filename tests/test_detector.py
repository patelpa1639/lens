"""Tests for project detection."""

from lens.models import ArchitecturePattern, Framework, Language
from lens.scanner.detector import detect_project


def test_detect_python_project(tmp_python_project):
    detection = detect_project(tmp_python_project)
    assert detection.primary_language == Language.PYTHON
    assert detection.package_manager == "pip"
    assert detection.has_tests is True
    assert Framework.FLASK in detection.frameworks


def test_detect_js_project(tmp_js_project):
    detection = detect_project(tmp_js_project)
    assert detection.primary_language in (Language.TYPESCRIPT, Language.JAVASCRIPT)
    assert Framework.REACT in detection.frameworks or Framework.NEXTJS in detection.frameworks


def test_detect_go_project(tmp_go_project):
    detection = detect_project(tmp_go_project)
    assert detection.primary_language == Language.GO
    assert detection.package_manager == "go modules"


def test_detect_rust_project(tmp_rust_project):
    detection = detect_project(tmp_rust_project)
    assert detection.primary_language == Language.RUST
    assert detection.package_manager == "cargo"


def test_detect_monorepo(tmp_monorepo):
    detection = detect_project(tmp_monorepo)
    assert detection.architecture == ArchitecturePattern.MONOREPO


def test_detect_empty_dir(tmp_path):
    detection = detect_project(tmp_path)
    assert detection.primary_language == Language.OTHER


def test_detect_has_docker(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    detection = detect_project(tmp_path)
    assert detection.has_docker is True


def test_detect_has_ci(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\n")
    detection = detect_project(tmp_path)
    assert detection.has_ci is True
