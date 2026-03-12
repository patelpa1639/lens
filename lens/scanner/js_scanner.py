"""JavaScript/TypeScript source file scanner using regex parsing."""

from __future__ import annotations

import re
from pathlib import Path

from lens.models import ClassInfo, FunctionInfo, ImportInfo, Language, ModuleInfo
from lens.utils.file_utils import detect_language, read_file_safe

# Regex patterns for JS/TS parsing
_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:(?:(?:(\w+)(?:\s*,\s*)?)?(?:\{([^}]*)\})?\s+from\s+)?['"]([^'"]+)['"]|(\w+)\s+from\s+['"]([^'"]+)['"]))|"""
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)

_EXPORT_RE = re.compile(
    r"""export\s+(?:default\s+)?(?:(?:function|class|const|let|var|interface|type|enum)\s+(\w+)|(\{[^}]*\}))""",
    re.MULTILINE,
)

_FUNCTION_RE = re.compile(
    r"""(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)""", re.MULTILINE
)

_ARROW_FUNC_RE = re.compile(
    r"""(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>""",
    re.MULTILINE,
)

_CLASS_RE = re.compile(
    r"""(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?""", re.MULTILINE
)

_METHOD_RE = re.compile(
    r"""(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{""", re.MULTILINE
)

# Framework detection patterns
_REACT_PATTERNS = [
    re.compile(r"""(?:from|require)\s*\(?['"]react['"]\)?"""),
    re.compile(r"""<\w+[\s/>]"""),  # JSX
]
_NEXTJS_PATTERNS = [
    re.compile(r"""(?:from|require)\s*\(?['"]next[/'"]\)?"""),
    re.compile(r"""getServerSideProps|getStaticProps|getStaticPaths"""),
]


def scan_js_file(file_path: Path, root: Path) -> ModuleInfo | None:
    """Parse a JavaScript/TypeScript file and extract structure."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    relative = str(file_path.relative_to(root))
    language = detect_language(file_path)
    if language == Language.OTHER:
        language = Language.JAVASCRIPT

    module = ModuleInfo(file_path=relative, language=language)
    module.imports = _extract_imports(content, relative)
    module.functions = _extract_functions(content, relative)
    module.classes = _extract_classes(content, relative)
    module.exports = _extract_exports(content)
    module.entry_point = _is_entry_point(content, file_path)

    return module


def _extract_imports(content: str, file_path: str) -> list[ImportInfo]:
    """Extract import/require statements."""
    imports: list[ImportInfo] = []
    seen: set[str] = set()

    for match in _IMPORT_RE.finditer(content):
        groups = match.groups()
        # ES6 import
        module_name = groups[2] or groups[4] or groups[5]
        if not module_name or module_name in seen:
            continue
        seen.add(module_name)

        names: list[str] = []
        if groups[0]:  # default import
            names.append(groups[0])
        if groups[1]:  # named imports
            names.extend(n.strip().split(" as ")[0].strip() for n in groups[1].split(",") if n.strip())
        if groups[3]:  # simple default
            names.append(groups[3])

        is_relative = module_name.startswith(".")
        is_external = not is_relative and not module_name.startswith("@/")

        imports.append(
            ImportInfo(
                module=module_name,
                names=names,
                is_relative=is_relative,
                is_external=is_external,
                source_file=file_path,
            )
        )

    return imports


def _extract_functions(content: str, file_path: str) -> list[FunctionInfo]:
    """Extract function declarations and arrow functions."""
    functions: list[FunctionInfo] = []
    seen: set[str] = set()

    for match in _FUNCTION_RE.finditer(content):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            params = [p.strip().split(":")[0].strip() for p in match.group(2).split(",") if p.strip()]
            functions.append(
                FunctionInfo(
                    name=name,
                    file_path=file_path,
                    line_number=content[: match.start()].count("\n") + 1,
                    is_async="async" in content[max(0, match.start() - 10) : match.start()],
                    parameters=params,
                )
            )

    for match in _ARROW_FUNC_RE.finditer(content):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            functions.append(
                FunctionInfo(
                    name=name,
                    file_path=file_path,
                    line_number=content[: match.start()].count("\n") + 1,
                    is_async="async" in content[max(0, match.start() - 10) : match.start()],
                )
            )

    return functions


def _extract_classes(content: str, file_path: str) -> list[ClassInfo]:
    """Extract class declarations."""
    classes: list[ClassInfo] = []
    for match in _CLASS_RE.finditer(content):
        name = match.group(1)
        bases = [match.group(2)] if match.group(2) else []
        classes.append(
            ClassInfo(
                name=name,
                file_path=file_path,
                line_number=content[: match.start()].count("\n") + 1,
                bases=bases,
            )
        )
    return classes


def _extract_exports(content: str) -> list[str]:
    """Extract exported names."""
    exports: list[str] = []
    for match in _EXPORT_RE.finditer(content):
        if match.group(1):
            exports.append(match.group(1))
        elif match.group(2):
            # Named exports like { foo, bar }
            names = match.group(2).strip("{}").split(",")
            exports.extend(n.strip().split(" as ")[0].strip() for n in names if n.strip())
    return exports


def _is_entry_point(content: str, file_path: Path) -> bool:
    """Check if this is an entry point file."""
    name = file_path.stem.lower()
    if name in ("index", "main", "app", "server", "entry"):
        return True
    if "createServer" in content or "app.listen" in content:
        return True
    if any(p.search(content) for p in _NEXTJS_PATTERNS):
        if name in ("page", "layout", "route"):
            return True
    return False
