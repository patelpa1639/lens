"""Rust source file scanner using regex parsing."""

from __future__ import annotations

import re
from pathlib import Path

from lens.models import FunctionInfo, ImportInfo, Language, ModuleInfo
from lens.utils.file_utils import read_file_safe

_USE_RE = re.compile(r"^use\s+([^;]+);", re.MULTILINE)
_FN_RE = re.compile(
    r"(pub\s+)?(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)", re.MULTILINE
)
_STRUCT_RE = re.compile(r"(?:pub\s+)?struct\s+(\w+)", re.MULTILINE)
_ENUM_RE = re.compile(r"(?:pub\s+)?enum\s+(\w+)", re.MULTILINE)
_TRAIT_RE = re.compile(r"(?:pub\s+)?trait\s+(\w+)", re.MULTILINE)
_IMPL_RE = re.compile(r"impl\s+(?:<[^>]*>\s+)?(\w+)", re.MULTILINE)
_MOD_RE = re.compile(r"^(?:pub\s+)?mod\s+(\w+);", re.MULTILINE)


def scan_rust_file(file_path: Path, root: Path) -> ModuleInfo | None:
    """Parse a Rust file and extract structure information."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    relative = str(file_path.relative_to(root))
    module = ModuleInfo(file_path=relative, language=Language.RUST)

    module.imports = _extract_imports(content, relative)
    module.functions = _extract_functions(content, relative)
    module.exports = _extract_exports(content)
    module.entry_point = _is_entry_point(content, file_path)

    return module


def _extract_imports(content: str, file_path: str) -> list[ImportInfo]:
    """Extract use statements."""
    imports: list[ImportInfo] = []
    for match in _USE_RE.finditer(content):
        use_path = match.group(1).strip()
        # Parse the use path
        parts = use_path.replace("::", "/").split("/")
        module_name = use_path.replace("/", "::")
        is_external = parts[0] not in ("crate", "self", "super") if parts else True

        imports.append(
            ImportInfo(
                module=module_name,
                names=[parts[-1].strip("{} ").split(",")[0].strip() if parts else ""],
                is_relative=parts[0] in ("self", "super") if parts else False,
                is_external=is_external,
                source_file=file_path,
            )
        )
    return imports


def _extract_functions(content: str, file_path: str) -> list[FunctionInfo]:
    """Extract function definitions."""
    functions: list[FunctionInfo] = []
    for match in _FN_RE.finditer(content):
        name = match.group(2)
        params_str = match.group(3)
        params = []
        if params_str.strip():
            for p in params_str.split(","):
                p = p.strip()
                if p and p != "self" and p != "&self" and p != "&mut self":
                    param_name = p.split(":")[0].strip()
                    params.append(param_name)

        prefix = content[max(0, match.start() - 20) : match.start()]
        functions.append(
            FunctionInfo(
                name=name,
                file_path=file_path,
                line_number=content[: match.start()].count("\n") + 1,
                is_async="async" in prefix,
                parameters=params,
            )
        )
    return functions


def _extract_exports(content: str) -> list[str]:
    """Extract pub items."""
    exports: list[str] = []
    for match in _FN_RE.finditer(content):
        if match.group(1):  # has pub prefix
            exports.append(match.group(2))
    for match in _STRUCT_RE.finditer(content):
        prefix = content[max(0, match.start() - 10) : match.start()]
        if "pub " in prefix:
            exports.append(match.group(1))
    for match in _TRAIT_RE.finditer(content):
        prefix = content[max(0, match.start() - 10) : match.start()]
        if "pub " in prefix:
            exports.append(match.group(1))
    return exports


def _is_entry_point(content: str, file_path: Path) -> bool:
    """Check if this is a binary entry point."""
    if file_path.name == "main.rs":
        return bool(re.search(r"fn\s+main\s*\(\s*\)", content))
    if file_path.name == "lib.rs":
        return True  # Library root
    return False
