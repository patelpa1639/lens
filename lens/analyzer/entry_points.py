"""Entry point detection — find where to start reading the codebase."""

from __future__ import annotations

from pathlib import Path

from lens.models import ModuleInfo

# Files that are commonly entry points
_ENTRY_POINT_NAMES = {
    "main.py",
    "__main__.py",
    "app.py",
    "server.py",
    "index.py",
    "cli.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "main.go",
    "main.rs",
    "lib.rs",
    "index.js",
    "index.ts",
    "app.js",
    "app.ts",
    "server.js",
    "server.ts",
    "main.js",
    "main.ts",
    "index.jsx",
    "index.tsx",
    "App.jsx",
    "App.tsx",
}


def find_entry_points(modules: list[ModuleInfo], root: Path) -> list[str]:
    """Find entry point files in the project.

    Entry points are files where execution starts or that serve as
    the main interface (routes, CLI commands, exports).
    """
    entry_points: list[str] = []
    seen: set[str] = set()

    for module in modules:
        file_name = Path(module.file_path).name

        # Check if scanner already detected it as entry point
        if module.entry_point and module.file_path not in seen:
            entry_points.append(module.file_path)
            seen.add(module.file_path)
            continue

        # Check common entry point file names
        if file_name in _ENTRY_POINT_NAMES and module.file_path not in seen:
            entry_points.append(module.file_path)
            seen.add(module.file_path)
            continue

        # Check for route/endpoint definitions
        if _has_route_definitions(module) and module.file_path not in seen:
            entry_points.append(module.file_path)
            seen.add(module.file_path)

    # Also check for standalone scripts/configs
    _check_config_entry_points(root, entry_points, seen)

    return entry_points


def _has_route_definitions(module: ModuleInfo) -> bool:
    """Check if a module has route/endpoint definitions."""
    route_decorators = {"route", "get", "post", "put", "delete", "patch", "api_view", "app.route"}
    for func in module.functions:
        for dec in func.decorators:
            if any(r in dec.lower() for r in route_decorators):
                return True
    return False


def _check_config_entry_points(
    root: Path, entry_points: list[str], seen: set[str]
) -> None:
    """Check for configuration-based entry points."""
    # Check pyproject.toml for console_scripts
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "[project.scripts]" in content:
                # Parse the scripts section to find entry module
                in_scripts = False
                for line in content.splitlines():
                    if "[project.scripts]" in line:
                        in_scripts = True
                        continue
                    if in_scripts:
                        if line.strip().startswith("["):
                            break
                        if "=" in line:
                            target = line.split("=")[1].strip().strip('"').split(":")[0]
                            module_path = target.replace(".", "/") + ".py"
                            if module_path not in seen:
                                entry_points.append(module_path)
                                seen.add(module_path)
        except OSError:
            pass
