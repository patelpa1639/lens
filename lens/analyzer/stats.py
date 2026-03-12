"""Project statistics aggregation."""

from __future__ import annotations

from lens.models import FileInfo, ProjectStats


def calculate_stats(files: list[FileInfo]) -> ProjectStats:
    """Calculate aggregate project statistics from file info list."""
    stats = ProjectStats()

    if not files:
        return stats

    stats.total_files = len(files)
    stats.total_lines = sum(f.line_count for f in files)
    stats.code_lines = sum(f.code_lines for f in files)
    stats.blank_lines = sum(f.blank_lines for f in files)
    stats.comment_lines = sum(f.comment_lines for f in files)

    # Language breakdown (lines of code)
    lang_lines: dict[str, int] = {}
    lang_files: dict[str, int] = {}
    for f in files:
        lang_name = f.language.value
        lang_lines[lang_name] = lang_lines.get(lang_name, 0) + f.code_lines
        lang_files[lang_name] = lang_files.get(lang_name, 0) + 1

    stats.language_breakdown = dict(sorted(lang_lines.items(), key=lambda x: x[1], reverse=True))
    stats.file_count_by_language = dict(sorted(lang_files.items(), key=lambda x: x[1], reverse=True))

    # Calculate percentages
    total_code = stats.code_lines or 1
    stats.language_percentages = {
        lang: round(lines / total_code * 100, 1) for lang, lines in stats.language_breakdown.items()
    }

    # File size stats
    sizes = [f.size_bytes for f in files]
    stats.avg_file_size = sum(sizes) / len(sizes) if sizes else 0

    # Largest files
    sorted_files = sorted(files, key=lambda f: f.size_bytes, reverse=True)
    stats.largest_files = [(f.relative_path, f.size_bytes) for f in sorted_files[:10]]

    return stats
