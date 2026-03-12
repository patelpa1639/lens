"""JSON export renderer."""

from __future__ import annotations

import json
from pathlib import Path

from lens.models import ProjectAnalysis


def render_json(analysis: ProjectAnalysis, output_path: Path | None = None) -> str:
    """Export analysis as structured JSON.

    If output_path is provided, writes to file and returns the path.
    Otherwise returns JSON string.
    """
    data = _build_json(analysis)
    json_str = json.dumps(data, indent=2, default=str)

    if output_path:
        output_path.write_text(json_str, encoding="utf-8")
        return str(output_path)

    return json_str


def _build_json(analysis: ProjectAnalysis) -> dict:
    """Build complete JSON structure."""
    return {
        "version": "0.1.0",
        "project": {
            "root": analysis.root_path,
            "primaryLanguage": analysis.detection.primary_language.value,
            "languages": {k.value: v for k, v in analysis.detection.languages.items()},
            "frameworks": [f.value for f in analysis.detection.frameworks],
            "architecture": analysis.architecture.value,
            "packageManager": analysis.detection.package_manager,
            "features": {
                "tests": analysis.detection.has_tests,
                "ci": analysis.detection.has_ci,
                "docker": analysis.detection.has_docker,
                "docs": analysis.detection.has_docs,
            },
        },
        "stats": {
            "totalFiles": analysis.stats.total_files,
            "totalLines": analysis.stats.total_lines,
            "codeLines": analysis.stats.code_lines,
            "blankLines": analysis.stats.blank_lines,
            "commentLines": analysis.stats.comment_lines,
            "languageBreakdown": analysis.stats.language_breakdown,
            "languagePercentages": analysis.stats.language_percentages,
            "avgFileSize": analysis.stats.avg_file_size,
            "largestFiles": [
                {"path": p, "sizeBytes": s} for p, s in analysis.stats.largest_files
            ],
        },
        "files": [
            {
                "path": f.relative_path,
                "language": f.language.value,
                "sizeBytes": f.size_bytes,
                "lines": {
                    "total": f.line_count,
                    "code": f.code_lines,
                    "blank": f.blank_lines,
                    "comment": f.comment_lines,
                },
            }
            for f in analysis.files
        ],
        "dependencies": {
            "internal": [
                {"source": d.source, "target": d.target, "names": d.import_names}
                for d in analysis.dependencies
            ],
            "external": analysis.external_deps,
            "circular": analysis.circular_deps,
        },
        "hotspots": [
            {
                "path": h.file_path,
                "score": h.score,
                "changeFrequency": h.change_frequency,
                "complexity": h.complexity,
                "sizeFactor": h.size_factor,
                "isDangerZone": h.is_danger_zone,
            }
            for h in analysis.hotspots
        ],
        "entryPoints": analysis.entry_points,
        "explanation": analysis.explanation,
    }
