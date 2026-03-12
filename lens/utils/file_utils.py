"""File utilities — reading, .gitignore respect, binary detection, language detection."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from lens.models import Language

# Max file size to read (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Binary file signatures (first bytes)
_BINARY_SIGNATURES = [
    b"\x7fELF",
    b"MZ",
    b"\x89PNG",
    b"\xff\xd8\xff",
    b"GIF8",
    b"PK\x03\x04",
    b"\x1f\x8b",
]

EXTENSION_LANGUAGE_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".pyi": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".java": Language.JAVA,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".hpp": Language.CPP,
    ".cs": Language.CSHARP,
    ".swift": Language.SWIFT,
    ".kt": Language.KOTLIN,
    ".kts": Language.KOTLIN,
    ".sh": Language.SHELL,
    ".bash": Language.SHELL,
    ".zsh": Language.SHELL,
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".css": Language.CSS,
    ".scss": Language.CSS,
    ".less": Language.CSS,
    ".sql": Language.SQL,
    ".md": Language.MARKDOWN,
    ".markdown": Language.MARKDOWN,
    ".yml": Language.YAML,
    ".yaml": Language.YAML,
    ".json": Language.JSON,
    ".toml": Language.TOML,
}

FILENAME_LANGUAGE_MAP: dict[str, Language] = {
    "Dockerfile": Language.DOCKERFILE,
    "Makefile": Language.SHELL,
    "Rakefile": Language.RUBY,
    "Gemfile": Language.RUBY,
}

# Default ignore patterns (always skip these)
DEFAULT_IGNORES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    "coverage",
    "htmlcov",
    ".DS_Store",
}


def is_binary(file_path: Path) -> bool:
    """Check if a file is binary by reading its first bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(512)
            if not chunk:
                return False
            for sig in _BINARY_SIGNATURES:
                if chunk.startswith(sig):
                    return True
            # Check for null bytes (common in binary files)
            if b"\x00" in chunk:
                return True
            return False
    except (OSError, PermissionError):
        return True


def detect_language(file_path: Path) -> Language:
    """Detect the programming language of a file."""
    name = file_path.name
    if name in FILENAME_LANGUAGE_MAP:
        return FILENAME_LANGUAGE_MAP[name]
    suffix = file_path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(suffix, Language.OTHER)


def read_file_safe(file_path: Path, max_size: int = MAX_FILE_SIZE) -> str | None:
    """Read a file safely with size limits and encoding handling."""
    try:
        if file_path.stat().st_size > max_size:
            return None
        if is_binary(file_path):
            return None
        return file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError, UnicodeDecodeError):
        return None


def count_lines(content: str) -> tuple[int, int, int, int]:
    """Count total, code, blank, and comment lines. Returns (total, code, blank, comment)."""
    if not content:
        return 0, 0, 0, 0
    lines = content.splitlines()
    total = len(lines)
    blank = sum(1 for line in lines if not line.strip())
    # Simple comment detection (covers most languages)
    comment = sum(
        1
        for line in lines
        if line.strip().startswith(("#", "//", "/*", "*", "<!--", "--", ";"))
    )
    code = total - blank - comment
    return total, max(code, 0), blank, comment


def parse_gitignore(root: Path) -> list[str]:
    """Parse .gitignore file and return patterns."""
    gitignore_path = root / ".gitignore"
    patterns: list[str] = []
    if gitignore_path.exists():
        try:
            content = gitignore_path.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        except OSError:
            pass
    return patterns


def should_ignore(path: Path, root: Path, gitignore_patterns: list[str], extra_ignores: list[str] | None = None) -> bool:
    """Check if a path should be ignored."""
    rel = str(path.relative_to(root))
    parts = path.parts

    # Check default ignores
    for part in parts:
        for pattern in DEFAULT_IGNORES:
            if fnmatch.fnmatch(part, pattern):
                return True

    # Check gitignore patterns
    all_patterns = gitignore_patterns + (extra_ignores or [])
    for pattern in all_patterns:
        # Handle directory patterns
        clean = pattern.rstrip("/")
        if fnmatch.fnmatch(rel, clean) or fnmatch.fnmatch(rel, clean + "/*"):
            return True
        for part in parts:
            if fnmatch.fnmatch(part, clean):
                return True

    return False


def collect_files(
    root: Path,
    max_depth: int = 50,
    extra_ignores: list[str] | None = None,
) -> list[Path]:
    """Collect all source files from a directory, respecting .gitignore."""
    root = root.resolve()
    gitignore_patterns = parse_gitignore(root)
    files: list[Path] = []

    def _walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(directory.iterdir())
        except (OSError, PermissionError):
            return

        for entry in entries:
            if should_ignore(entry, root, gitignore_patterns, extra_ignores):
                continue
            if entry.is_dir():
                _walk(entry, depth + 1)
            elif entry.is_file():
                if not is_binary(entry):
                    files.append(entry)

    _walk(root, 0)
    return files
