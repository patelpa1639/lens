"""Go source file scanner using regex parsing."""

from __future__ import annotations

import re
from pathlib import Path

from lens.models import FunctionInfo, ImportInfo, Language, ModuleInfo
from lens.utils.file_utils import read_file_safe

_PACKAGE_RE = re.compile(r"^package\s+(\w+)", re.MULTILINE)
_IMPORT_SINGLE_RE = re.compile(r'^import\s+"([^"]+)"', re.MULTILINE)
_IMPORT_BLOCK_RE = re.compile(r"import\s*\((.*?)\)", re.DOTALL)
_IMPORT_LINE_RE = re.compile(r'"([^"]+)"')
_FUNC_RE = re.compile(
    r"^func\s+(?:\((\w+)\s+\*?(\w+)\)\s+)?(\w+)\s*\(([^)]*)\)", re.MULTILINE
)
_STRUCT_RE = re.compile(r"^type\s+(\w+)\s+struct\s*\{", re.MULTILINE)
_INTERFACE_RE = re.compile(r"^type\s+(\w+)\s+interface\s*\{", re.MULTILINE)


def scan_go_file(file_path: Path, root: Path) -> ModuleInfo | None:
    """Parse a Go file and extract structure information."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    relative = str(file_path.relative_to(root))
    module = ModuleInfo(file_path=relative, language=Language.GO)

    module.imports = _extract_imports(content, relative)
    module.functions = _extract_functions(content, relative)
    module.entry_point = _is_entry_point(content)

    # Detect exported names (capitalized)
    module.exports = _extract_exports(content)

    return module


def _extract_imports(content: str, file_path: str) -> list[ImportInfo]:
    """Extract import statements."""
    imports: list[ImportInfo] = []
    seen: set[str] = set()

    # Single imports
    for match in _IMPORT_SINGLE_RE.finditer(content):
        pkg = match.group(1)
        if pkg not in seen:
            seen.add(pkg)
            imports.append(_make_import(pkg, file_path))

    # Import blocks
    for block in _IMPORT_BLOCK_RE.finditer(content):
        for line_match in _IMPORT_LINE_RE.finditer(block.group(1)):
            pkg = line_match.group(1)
            if pkg not in seen:
                seen.add(pkg)
                imports.append(_make_import(pkg, file_path))

    return imports


def _make_import(pkg: str, file_path: str) -> ImportInfo:
    """Create an ImportInfo from a Go import path."""
    parts = pkg.split("/")
    short_name = parts[-1]
    # External if it contains a domain-like prefix
    is_external = "." in parts[0] if parts else False
    return ImportInfo(
        module=pkg,
        names=[short_name],
        is_relative=False,
        is_external=is_external,
        source_file=file_path,
    )


def _extract_functions(content: str, file_path: str) -> list[FunctionInfo]:
    """Extract function and method definitions."""
    functions: list[FunctionInfo] = []
    for match in _FUNC_RE.finditer(content):
        receiver_type = match.group(2)
        name = match.group(3)
        params_str = match.group(4)
        params = [p.strip().split()[0] for p in params_str.split(",") if p.strip()] if params_str.strip() else []

        functions.append(
            FunctionInfo(
                name=name,
                file_path=file_path,
                line_number=content[: match.start()].count("\n") + 1,
                is_method=receiver_type is not None,
                parameters=params,
            )
        )
    return functions


def _extract_exports(content: str) -> list[str]:
    """Extract exported (capitalized) type and function names."""
    exports: list[str] = []
    for match in _FUNC_RE.finditer(content):
        name = match.group(3)
        if name[0].isupper():
            exports.append(name)
    for match in _STRUCT_RE.finditer(content):
        name = match.group(1)
        if name[0].isupper():
            exports.append(name)
    for match in _INTERFACE_RE.finditer(content):
        name = match.group(1)
        if name[0].isupper():
            exports.append(name)
    return exports


def _is_entry_point(content: str) -> bool:
    """Check if this is a main package with main function."""
    has_main_pkg = bool(_PACKAGE_RE.search(content) and "package main" in content)
    has_main_func = bool(re.search(r"^func\s+main\s*\(\s*\)", content, re.MULTILINE))
    return has_main_pkg and has_main_func
