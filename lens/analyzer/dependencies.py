"""Dependency analysis — internal and external dependency mapping."""

from __future__ import annotations

import json
from pathlib import Path

from lens.models import DependencyEdge, ModuleInfo


def build_dependency_graph(
    modules: list[ModuleInfo], root: Path
) -> tuple[list[DependencyEdge], list[str], list[list[str]]]:
    """Build internal dependency graph, external deps list, and detect circular deps.

    Returns:
        (edges, external_deps, circular_deps)
    """
    edges: list[DependencyEdge] = []
    external_deps: set[str] = set()
    file_set = {m.file_path for m in modules}

    for module in modules:
        for imp in module.imports:
            if imp.is_external:
                # Top-level package name
                top_pkg = imp.module.split("/")[0].split(".")[0]
                external_deps.add(top_pkg)
            else:
                # Try to resolve internal dependency
                target = _resolve_internal(imp.module, module.file_path, file_set, root)
                if target:
                    edges.append(
                        DependencyEdge(
                            source=module.file_path,
                            target=target,
                            import_names=imp.names,
                        )
                    )

    # Also collect external deps from package files
    external_deps.update(_collect_package_deps(root))

    # Detect circular dependencies
    circular = _find_circular_deps(edges)

    return edges, sorted(external_deps), circular


def _resolve_internal(
    module_name: str, source_file: str, file_set: set[str], root: Path
) -> str | None:
    """Try to resolve an import to an internal file path."""
    if not module_name:
        return None

    # Python-style module resolution
    candidates = [
        module_name.replace(".", "/") + ".py",
        module_name.replace(".", "/") + "/__init__.py",
    ]

    # JS-style resolution
    js_base = module_name.lstrip("./")
    for ext in [".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]:
        candidates.append(js_base + ext)

    # Go package resolution
    candidates.append(module_name.split("/")[-1] + ".go")

    for candidate in candidates:
        if candidate in file_set:
            return candidate

    return None


def _collect_package_deps(root: Path) -> set[str]:
    """Collect external dependency names from package manifest files."""
    deps: set[str] = set()

    # Python: pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            # Simple TOML parsing for dependencies list
            in_deps = False
            for line in content.splitlines():
                if line.strip() == "dependencies = [":
                    in_deps = True
                    continue
                if in_deps:
                    if line.strip() == "]":
                        break
                    # Extract package name from "package>=version"
                    pkg = line.strip().strip('",').split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip()
                    if pkg:
                        deps.add(pkg)
        except OSError:
            pass

    # Python: requirements.txt
    req = root / "requirements.txt"
    if req.exists():
        try:
            for line in req.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    pkg = line.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip()
                    if pkg:
                        deps.add(pkg)
        except OSError:
            pass

    # JS: package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps.update(pkg.get("dependencies", {}).keys())
            deps.update(pkg.get("devDependencies", {}).keys())
        except (ValueError, OSError):
            pass

    # Go: go.mod
    go_mod = root / "go.mod"
    if go_mod.exists():
        try:
            in_require = False
            for line in go_mod.read_text().splitlines():
                if line.strip() == "require (":
                    in_require = True
                    continue
                if in_require:
                    if line.strip() == ")":
                        break
                    parts = line.strip().split()
                    if parts:
                        deps.add(parts[0])
        except OSError:
            pass

    # Rust: Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.exists():
        try:
            in_deps = False
            for line in cargo.read_text().splitlines():
                if line.strip() in ("[dependencies]", "[dev-dependencies]"):
                    in_deps = True
                    continue
                if in_deps:
                    if line.strip().startswith("["):
                        in_deps = False
                        continue
                    if "=" in line:
                        pkg = line.split("=")[0].strip()
                        if pkg:
                            deps.add(pkg)
        except OSError:
            pass

    return deps


def _find_circular_deps(edges: list[DependencyEdge]) -> list[list[str]]:
    """Find circular dependencies using DFS."""
    graph: dict[str, list[str]] = {}
    for edge in edges:
        graph.setdefault(edge.source, []).append(edge.target)

    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []

    def _dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                _dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                if len(cycle) <= 10:  # Only report small cycles
                    cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            _dfs(node, [])

    return cycles[:10]  # Limit to 10 cycles
