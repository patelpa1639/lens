"""Generic/fallback scanner for unsupported languages."""

from __future__ import annotations

import re
from pathlib import Path

from lens.models import FunctionInfo, ImportInfo, ModuleInfo
from lens.utils.file_utils import detect_language, read_file_safe

# Generic patterns that work across many languages
_INCLUDE_RE = re.compile(r'#include\s*[<"]([^>"]+)[>"]', re.MULTILINE)
_GENERIC_IMPORT_RE = re.compile(
    r"(?:import|require|include|use|using)\s+['\"]?([^\s;'\"]+)", re.MULTILINE
)
_GENERIC_FUNC_RE = re.compile(
    r"(?:def|func|function|fn|sub|proc)\s+(\w+)\s*\(", re.MULTILINE
)
_GENERIC_CLASS_RE = re.compile(
    r"(?:class|struct|interface|trait|type)\s+(\w+)", re.MULTILINE
)


def scan_generic_file(file_path: Path, root: Path) -> ModuleInfo | None:
    """Parse any source file using generic heuristics."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    relative = str(file_path.relative_to(root))
    language = detect_language(file_path)

    module = ModuleInfo(file_path=relative, language=language)

    # Try generic patterns
    module.imports = _extract_imports(content, relative)
    module.functions = _extract_functions(content, relative)

    return module


def _extract_imports(content: str, file_path: str) -> list[ImportInfo]:
    """Extract imports using generic patterns."""
    imports: list[ImportInfo] = []
    seen: set[str] = set()

    for match in _INCLUDE_RE.finditer(content):
        module = match.group(1)
        if module not in seen:
            seen.add(module)
            imports.append(ImportInfo(module=module, source_file=file_path, is_external=True))

    for match in _GENERIC_IMPORT_RE.finditer(content):
        module = match.group(1).strip("'\"")
        if module not in seen:
            seen.add(module)
            imports.append(ImportInfo(module=module, source_file=file_path))

    return imports


def _extract_functions(content: str, file_path: str) -> list[FunctionInfo]:
    """Extract functions using generic patterns."""
    functions: list[FunctionInfo] = []
    seen: set[str] = set()

    for match in _GENERIC_FUNC_RE.finditer(content):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            functions.append(
                FunctionInfo(
                    name=name,
                    file_path=file_path,
                    line_number=content[: match.start()].count("\n") + 1,
                )
            )

    return functions
