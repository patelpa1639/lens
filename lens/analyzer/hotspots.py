"""Hotspot detection — identify high-risk files based on change frequency and complexity."""

from __future__ import annotations

from lens.models import FileInfo, GitFileHistory, HotspotInfo, ModuleInfo


def calculate_hotspots(
    files: list[FileInfo],
    modules: list[ModuleInfo],
    git_history: list[GitFileHistory],
    top_n: int = 20,
) -> list[HotspotInfo]:
    """Calculate hotspot scores combining git churn, complexity, and size.

    Score formula: (change_frequency * 0.4) + (complexity * 0.35) + (size_factor * 0.25)
    Normalized to 0-100 scale.
    """
    git_map = {g.file_path: g for g in git_history}
    complexity_map = _build_complexity_map(modules)
    size_map = {f.relative_path: f.code_lines for f in files}

    # Get max values for normalization
    max_churn = max((g.commit_count for g in git_history), default=1) or 1
    max_complexity = max(complexity_map.values(), default=1) or 1
    max_size = max(size_map.values(), default=1) or 1

    hotspots: list[HotspotInfo] = []

    for file_info in files:
        rel = file_info.relative_path
        git = git_map.get(rel)

        change_freq = (git.commit_count / max_churn * 100) if git else 0
        complexity = (complexity_map.get(rel, 1) / max_complexity * 100)
        size_factor = (size_map.get(rel, 0) / max_size * 100)

        score = (change_freq * 0.4) + (complexity * 0.35) + (size_factor * 0.25)
        is_danger = score > 70 and change_freq > 50 and complexity > 50

        hotspots.append(
            HotspotInfo(
                file_path=rel,
                score=round(score, 1),
                change_frequency=round(change_freq, 1),
                complexity=round(complexity, 1),
                size_factor=round(size_factor, 1),
                is_danger_zone=is_danger,
            )
        )

    hotspots.sort(key=lambda h: h.score, reverse=True)
    return hotspots[:top_n]


def _build_complexity_map(modules: list[ModuleInfo]) -> dict[str, float]:
    """Build a map of file path to aggregate complexity score."""
    complexity_map: dict[str, float] = {}
    for module in modules:
        total = 0.0
        for func in module.functions:
            total += func.complexity
        for cls in module.classes:
            for method in cls.methods:
                total += method.complexity
        if total > 0:
            complexity_map[module.file_path] = total
    return complexity_map
