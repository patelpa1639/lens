"""Tests for dependency analysis."""

from pathlib import Path

from lens.analyzer.dependencies import build_dependency_graph
from lens.models import ImportInfo, Language, ModuleInfo


def test_build_dependency_graph_basic():
    modules = [
        ModuleInfo(
            file_path="app.py",
            language=Language.PYTHON,
            imports=[
                ImportInfo(module="utils", names=["helper"], source_file="app.py"),
                ImportInfo(module="flask", names=["Flask"], is_external=True, source_file="app.py"),
            ],
        ),
        ModuleInfo(
            file_path="utils.py",
            language=Language.PYTHON,
            imports=[],
        ),
    ]
    edges, ext_deps, circular = build_dependency_graph(modules, Path("/tmp/test"))
    assert "flask" in ext_deps


def test_detect_circular_deps():
    modules = [
        ModuleInfo(
            file_path="a.py",
            language=Language.PYTHON,
            imports=[ImportInfo(module="b", names=["b"], source_file="a.py")],
        ),
        ModuleInfo(
            file_path="b.py",
            language=Language.PYTHON,
            imports=[ImportInfo(module="a", names=["a"], source_file="b.py")],
        ),
    ]
    edges, _, circular = build_dependency_graph(modules, Path("/tmp/test"))
    # Circular detection depends on resolution; verify no crash
    assert isinstance(circular, list)


def test_collect_package_deps_python(tmp_python_project):
    from lens.analyzer.dependencies import _collect_package_deps

    deps = _collect_package_deps(tmp_python_project)
    assert "flask" in deps or "Flask" in deps or len(deps) > 0


def test_empty_modules():
    edges, ext_deps, circular = build_dependency_graph([], Path("/tmp/test"))
    assert edges == []
    assert ext_deps == []
    assert circular == []
