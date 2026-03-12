"""Markdown export renderer with Mermaid diagrams."""

from __future__ import annotations

from pathlib import Path

from lens.models import ProjectAnalysis


def render_markdown(analysis: ProjectAnalysis, output_path: Path | None = None) -> str:
    """Generate markdown summary of the analysis."""
    lines: list[str] = []
    name = analysis.root_path.rstrip("/").split("/")[-1]

    lines.append(f"# {name}")
    lines.append("")

    # Explanation
    if analysis.explanation:
        lines.append(analysis.explanation)
        lines.append("")

    # Stats table
    stats = analysis.stats
    lines.append("## Statistics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Files | {stats.total_files:,} |")
    lines.append(f"| Lines of Code | {stats.code_lines:,} |")
    lines.append(f"| Languages | {len(stats.language_breakdown)} |")
    lines.append(f"| Architecture | {analysis.architecture.value} |")
    lines.append("")

    # Language breakdown
    lines.append("## Languages")
    lines.append("")
    for lang, pct in stats.language_percentages.items():
        if pct >= 1:
            bar_len = int(pct / 2)
            lines.append(f"- **{lang}** ({pct}%) {'█' * bar_len}")
    lines.append("")

    # Entry points
    if analysis.entry_points:
        lines.append("## Entry Points")
        lines.append("")
        for ep in analysis.entry_points[:10]:
            lines.append(f"- `{ep}`")
        lines.append("")

    # Dependency diagram (Mermaid)
    if analysis.dependencies:
        lines.append("## Dependency Graph")
        lines.append("")
        lines.append("```mermaid")
        lines.append("graph LR")
        seen: set[str] = set()
        for dep in analysis.dependencies[:30]:
            src = dep.source.replace("/", "_").replace(".", "_")
            tgt = dep.target.replace("/", "_").replace(".", "_")
            key = f"{src}->{tgt}"
            if key not in seen:
                seen.add(key)
                lines.append(f"    {src}[{dep.source}] --> {tgt}[{dep.target}]")
        lines.append("```")
        lines.append("")

    # External deps
    if analysis.external_deps:
        lines.append("## External Dependencies")
        lines.append("")
        lines.append(", ".join(f"`{d}`" for d in analysis.external_deps[:30]))
        lines.append("")

    # Hotspots
    if analysis.hotspots:
        lines.append("## Hotspots")
        lines.append("")
        lines.append("| File | Score | Status |")
        lines.append("|------|-------|--------|")
        for h in analysis.hotspots[:10]:
            status = "DANGER" if h.is_danger_zone else "OK"
            lines.append(f"| `{h.file_path}` | {h.score} | {status} |")
        lines.append("")

    content = "\n".join(lines)

    if output_path:
        output_path.write_text(content, encoding="utf-8")

    return content
