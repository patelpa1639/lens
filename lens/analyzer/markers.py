"""Marker scanning — find TODO/FIXME/HACK/BUG/XXX/NOTE/OPTIMIZE comments in source files."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lens.utils.file_utils import collect_files, read_file_safe

# Marker keywords grouped by severity
SEVERITY_MAP: dict[str, str] = {
    "FIXME": "critical",
    "BUG": "critical",
    "XXX": "critical",
    "TODO": "warning",
    "HACK": "warning",
    "OPTIMIZE": "warning",
    "NOTE": "info",
}

ALL_MARKERS = list(SEVERITY_MAP.keys())

# Pattern that matches marker keywords (case-insensitive) optionally followed by
# a colon or parenthesised author, then the rest of the line.
_MARKER_RE = re.compile(
    r"\b(" + "|".join(ALL_MARKERS) + r")\b\s*[:(\-]?\s*(.*)",
    re.IGNORECASE,
)


@dataclass
class MarkerMatch:
    file_path: str
    line_number: int
    marker_type: str  # "TODO", "FIXME", "HACK", "BUG", "XXX", "NOTE", "OPTIMIZE"
    severity: str  # "critical", "warning", "info"
    text: str  # The full line text
    context: str  # Surrounding context (1 line before/after)


@dataclass
class MarkerReport:
    markers: list[MarkerMatch] = field(default_factory=list)
    total_count: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    by_file: dict[str, list[MarkerMatch]] = field(default_factory=dict)


def _get_context(lines: list[str], index: int) -> str:
    """Return 1 line before and after *index*, joined by newlines."""
    start = max(0, index - 1)
    end = min(len(lines), index + 2)  # exclusive
    return "\n".join(lines[start:end])


def _scan_file(file_path: Path, root: Path) -> list[MarkerMatch]:
    """Scan a single file for marker comments."""
    content = read_file_safe(file_path)
    if content is None:
        return []

    lines = content.splitlines()
    matches: list[MarkerMatch] = []
    rel_path = str(file_path.relative_to(root))

    for idx, line in enumerate(lines):
        m = _MARKER_RE.search(line)
        if m is None:
            continue
        marker_word = m.group(1).upper()
        severity = SEVERITY_MAP.get(marker_word, "info")
        context = _get_context(lines, idx)
        matches.append(
            MarkerMatch(
                file_path=rel_path,
                line_number=idx + 1,
                marker_type=marker_word,
                severity=severity,
                text=line,
                context=context,
            )
        )

    return matches


def scan_markers(root: Path, extra_ignores: list[str] | None = None) -> MarkerReport:
    """Scan all files under *root* for TODO/FIXME/HACK markers."""
    root = root.resolve()
    files = collect_files(root, extra_ignores=extra_ignores)

    all_matches: list[MarkerMatch] = []
    for fp in files:
        all_matches.extend(_scan_file(fp, root))

    # Build aggregate counts
    by_severity: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    by_file: dict[str, list[MarkerMatch]] = defaultdict(list)

    for match in all_matches:
        by_severity[match.severity] += 1
        by_type[match.marker_type] += 1
        by_file[match.file_path].append(match)

    return MarkerReport(
        markers=all_matches,
        total_count=len(all_matches),
        by_severity=dict(by_severity),
        by_type=dict(by_type),
        by_file=dict(by_file),
    )
