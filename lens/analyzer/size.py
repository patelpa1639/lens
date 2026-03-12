"""Analyze disk space usage by directory, language, and file type."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from lens.models import FileInfo


@dataclass
class SizeEntry:
    """A single row in a size breakdown table."""

    name: str
    size_bytes: int
    file_count: int
    percentage: float
    code_lines: int


@dataclass
class SizeReport:
    """Complete size analysis of a project."""

    total_size_bytes: int
    total_files: int
    by_directory: list[SizeEntry]  # Top-level dirs sorted by size desc
    by_language: list[SizeEntry]  # Languages sorted by size desc
    by_extension: list[SizeEntry]  # File extensions sorted by size desc
    largest_files: list[tuple[str, int]]  # (path, size) top 10


def analyze_size(files: list[FileInfo], root: Path) -> SizeReport:
    """Analyze size distribution of a project."""
    if not files:
        return SizeReport(
            total_size_bytes=0,
            total_files=0,
            by_directory=[],
            by_language=[],
            by_extension=[],
            largest_files=[],
        )

    total_size = sum(f.size_bytes for f in files)
    total_files = len(files)

    by_directory = _group_by_directory(files, total_size)
    by_language = _group_by_language(files, total_size)
    by_extension = _group_by_extension(files, total_size)

    sorted_files = sorted(files, key=lambda f: f.size_bytes, reverse=True)
    largest_files = [(f.relative_path, f.size_bytes) for f in sorted_files[:10]]

    return SizeReport(
        total_size_bytes=total_size,
        total_files=total_files,
        by_directory=by_directory,
        by_language=by_language,
        by_extension=by_extension,
        largest_files=largest_files,
    )


def _top_level_dir(relative_path: str) -> str:
    """Extract the top-level directory from a relative path."""
    parts = Path(relative_path).parts
    if len(parts) <= 1:
        return "./"
    return parts[0]


def _build_entries(
    groups: dict[str, list[FileInfo]], total_size: int
) -> list[SizeEntry]:
    """Build sorted SizeEntry list from grouped files."""
    entries: list[SizeEntry] = []
    for name, group_files in groups.items():
        size = sum(f.size_bytes for f in group_files)
        percentage = (size / total_size * 100) if total_size > 0 else 0.0
        entries.append(
            SizeEntry(
                name=name,
                size_bytes=size,
                file_count=len(group_files),
                percentage=round(percentage, 1),
                code_lines=sum(f.code_lines for f in group_files),
            )
        )
    entries.sort(key=lambda e: e.size_bytes, reverse=True)
    return entries


def _group_by_directory(
    files: list[FileInfo], total_size: int
) -> list[SizeEntry]:
    """Group files by their top-level directory."""
    groups: dict[str, list[FileInfo]] = defaultdict(list)
    for f in files:
        groups[_top_level_dir(f.relative_path)].append(f)
    return _build_entries(groups, total_size)


def _group_by_language(
    files: list[FileInfo], total_size: int
) -> list[SizeEntry]:
    """Group files by language."""
    groups: dict[str, list[FileInfo]] = defaultdict(list)
    for f in files:
        groups[f.language.value].append(f)
    return _build_entries(groups, total_size)


def _group_by_extension(
    files: list[FileInfo], total_size: int
) -> list[SizeEntry]:
    """Group files by file extension."""
    groups: dict[str, list[FileInfo]] = defaultdict(list)
    for f in files:
        ext = Path(f.relative_path).suffix
        key = ext if ext else "(no ext)"
        groups[key].append(f)
    return _build_entries(groups, total_size)
