"""Build an inverted index over source files for fast keyword search."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lens.utils.file_utils import collect_files, detect_language, read_file_safe


@dataclass
class IndexEntry:
    """A single occurrence of a token in the codebase."""

    file_path: Path
    line_number: int
    context: str  # the line text
    kind: str = "content"  # "function", "class", "import", "comment", "string", "content"


@dataclass
class SearchIndex:
    """Inverted index: token -> list of occurrences."""

    entries: dict[str, list[IndexEntry]] = field(default_factory=dict)
    file_languages: dict[Path, str] = field(default_factory=dict)

    def add(self, token: str, entry: IndexEntry) -> None:
        """Add an entry for *token* (always stored lowercase)."""
        key = token.lower()
        if key not in self.entries:
            self.entries[key] = []
        self.entries[key].append(entry)

    def lookup(self, token: str) -> list[IndexEntry]:
        """Return all entries for *token*."""
        return self.entries.get(token.lower(), [])


# Patterns used to identify structural tokens
_PYTHON_FUNC_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")
_PYTHON_CLASS_RE = re.compile(r"^\s*class\s+(\w+)")
_JS_FUNC_RE = re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()")
_JS_CLASS_RE = re.compile(r"(?:^|\s)class\s+(\w+)")
_GO_FUNC_RE = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)")
_RUST_FN_RE = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)")
_RUST_STRUCT_RE = re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)")
_IMPORT_RE = re.compile(
    r"(?:^import\s+.+|^from\s+\S+\s+import\s+.+|"
    r"(?:const|let|var)\s+.+=\s*require\(.+\)|"
    r'^use\s+[\w:]+|^import\s+"[^"]+")',
    re.MULTILINE,
)
_COMMENT_RE = re.compile(r"(?:#|//)\s*(.*)")
_WORD_RE = re.compile(r"[a-zA-Z_]\w*")


def _tokenize_line(line: str) -> list[str]:
    """Split a line into lowercase word tokens."""
    return [m.lower() for m in _WORD_RE.findall(line)]


def build_index(root: Path, max_depth: int = 50, extra_ignores: list[str] | None = None) -> SearchIndex:
    """Walk *root*, read every source file and build an inverted index.

    Indexes function names, class names, imports, comments, and general content.
    """
    index = SearchIndex()
    files = collect_files(root, max_depth=max_depth, extra_ignores=extra_ignores)

    for fpath in files:
        content = read_file_safe(fpath)
        if content is None:
            continue

        lang = detect_language(fpath)
        index.file_languages[fpath] = lang.value

        lines = content.splitlines()
        for line_num_0, line in enumerate(lines):
            line_number = line_num_0 + 1

            # --- structural matches ---
            kind = "content"

            # Functions
            func_match = (
                _PYTHON_FUNC_RE.match(line)
                or _JS_FUNC_RE.search(line)
                or _GO_FUNC_RE.match(line)
                or _RUST_FN_RE.match(line)
            )
            if func_match:
                name = next((g for g in func_match.groups() if g), None)
                if name:
                    entry = IndexEntry(file_path=fpath, line_number=line_number, context=line, kind="function")
                    index.add(name, entry)
                    kind = "function"

            # Classes / structs
            class_match = (
                _PYTHON_CLASS_RE.match(line)
                or _JS_CLASS_RE.search(line)
                or _RUST_STRUCT_RE.match(line)
            )
            if class_match:
                name = next((g for g in class_match.groups() if g), None)
                if name:
                    entry = IndexEntry(file_path=fpath, line_number=line_number, context=line, kind="class")
                    index.add(name, entry)
                    kind = "class"

            # Imports
            if _IMPORT_RE.match(line.strip()):
                kind = "import"

            # Comments
            comment_match = _COMMENT_RE.search(line)
            if comment_match:
                kind = "comment"

            # Index every word token on this line
            tokens = _tokenize_line(line)
            for tok in tokens:
                if len(tok) < 2:
                    continue
                entry = IndexEntry(file_path=fpath, line_number=line_number, context=line, kind=kind)
                index.add(tok, entry)

        # Also index the filename stem as a token pointing to line 1
        for tok in _tokenize_line(fpath.stem):
            if len(tok) >= 2:
                first_line = lines[0] if lines else ""
                entry = IndexEntry(file_path=fpath, line_number=1, context=first_line, kind="filename")
                index.add(tok, entry)

    return index
