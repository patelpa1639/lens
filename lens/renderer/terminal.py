"""Rich terminal output renderer."""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from lens.models import ProjectAnalysis


def render_terminal(analysis: ProjectAnalysis, console: Console | None = None) -> None:
    """Render full analysis to terminal using Rich."""
    console = console or Console()

    _render_header(analysis, console)
    _render_stats(analysis, console)
    _render_language_bar(analysis, console)
    _render_architecture(analysis, console)
    _render_entry_points(analysis, console)
    _render_dependencies(analysis, console)
    _render_hotspots(analysis, console)
    _render_file_tree(analysis, console)


def _render_header(analysis: ProjectAnalysis, console: Console) -> None:
    """Render the project header panel."""
    det = analysis.detection
    name = analysis.root_path.rstrip("/").split("/")[-1]

    lines = [
        f"[bold cyan]{name}[/bold cyan]",
        "",
        f"[dim]Language:[/dim]  {det.primary_language.value}",
    ]

    if det.frameworks:
        fw = ", ".join(f.value for f in det.frameworks)
        lines.append(f"[dim]Framework:[/dim] {fw}")

    lines.append(f"[dim]Architecture:[/dim] {analysis.architecture.value}")
    lines.append(f"[dim]Package Manager:[/dim] {det.package_manager or 'unknown'}")

    features = []
    if det.has_tests:
        features.append("[green]tests[/green]")
    if det.has_ci:
        features.append("[green]CI/CD[/green]")
    if det.has_docker:
        features.append("[green]Docker[/green]")
    if det.has_docs:
        features.append("[green]docs[/green]")
    if features:
        lines.append(f"[dim]Features:[/dim]    {' · '.join(features)}")

    console.print(Panel("\n".join(lines), title="[bold]LENS[/bold]", border_style="cyan"))


def _render_stats(analysis: ProjectAnalysis, console: Console) -> None:
    """Render project statistics."""
    stats = analysis.stats
    table = Table(title="Project Statistics", show_header=False, border_style="dim")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Total Files", f"{stats.total_files:,}")
    table.add_row("Lines of Code", f"{stats.code_lines:,}")
    table.add_row("Blank Lines", f"{stats.blank_lines:,}")
    table.add_row("Comment Lines", f"{stats.comment_lines:,}")
    table.add_row("Total Lines", f"{stats.total_lines:,}")

    if stats.avg_file_size:
        avg_kb = stats.avg_file_size / 1024
        table.add_row("Avg File Size", f"{avg_kb:.1f} KB")

    console.print(table)
    console.print()


def _render_language_bar(analysis: ProjectAnalysis, console: Console) -> None:
    """Render language breakdown as a colored bar."""
    stats = analysis.stats
    if not stats.language_percentages:
        return

    colors = [
        "blue", "green", "yellow", "red", "magenta", "cyan",
        "bright_blue", "bright_green", "bright_yellow", "bright_red",
    ]

    bar_width = 50
    parts: list[str] = []
    legend: list[str] = []

    for i, (lang, pct) in enumerate(stats.language_percentages.items()):
        if pct < 1:
            continue
        color = colors[i % len(colors)]
        width = max(1, int(pct / 100 * bar_width))
        parts.append(f"[{color}]{'█' * width}[/{color}]")
        legend.append(f"[{color}]■[/{color}] {lang} ({pct}%)")

    console.print(Panel("".join(parts), title="Language Breakdown", border_style="dim"))
    console.print(Columns(legend, padding=(0, 3)))
    console.print()


def _render_architecture(analysis: ProjectAnalysis, console: Console) -> None:
    """Render architecture pattern detection."""
    if analysis.explanation:
        console.print(Panel(analysis.explanation, title="Project Explanation", border_style="green"))
        console.print()


def _render_entry_points(analysis: ProjectAnalysis, console: Console) -> None:
    """Render entry points."""
    if not analysis.entry_points:
        return

    table = Table(title="Entry Points", border_style="green")
    table.add_column("File", style="green")
    table.add_column("Type", style="dim")

    for ep in analysis.entry_points[:15]:
        ep_type = _classify_entry_point(ep)
        table.add_row(ep, ep_type)

    console.print(table)
    console.print()


def _render_dependencies(analysis: ProjectAnalysis, console: Console) -> None:
    """Render external dependencies."""
    if not analysis.external_deps:
        return

    table = Table(title=f"External Dependencies ({len(analysis.external_deps)})", border_style="blue")
    table.add_column("Package", style="cyan")

    # Show in columns
    deps = analysis.external_deps[:30]
    for dep in deps:
        table.add_row(dep)

    console.print(table)

    if analysis.circular_deps:
        console.print()
        console.print(f"[yellow]⚠ {len(analysis.circular_deps)} circular dependency(ies) detected[/yellow]")
        for cycle in analysis.circular_deps[:3]:
            console.print(f"  [dim]{'  →  '.join(cycle)}[/dim]")

    console.print()


def _render_hotspots(analysis: ProjectAnalysis, console: Console) -> None:
    """Render hotspot files."""
    if not analysis.hotspots:
        return

    table = Table(title="Hotspots (highest risk files)", border_style="red")
    table.add_column("File", style="white")
    table.add_column("Score", justify="right")
    table.add_column("Churn", justify="right", style="dim")
    table.add_column("Complexity", justify="right", style="dim")
    table.add_column("Status")

    for hs in analysis.hotspots[:10]:
        score_color = "red" if hs.score > 70 else "yellow" if hs.score > 40 else "green"
        status = "[red bold]DANGER[/red bold]" if hs.is_danger_zone else "[green]OK[/green]"
        table.add_row(
            hs.file_path,
            f"[{score_color}]{hs.score}[/{score_color}]",
            f"{hs.change_frequency}",
            f"{hs.complexity}",
            status,
        )

    console.print(table)
    console.print()


def _render_file_tree(analysis: ProjectAnalysis, console: Console) -> None:
    """Render file tree with annotations."""
    if not analysis.files:
        return

    root_name = analysis.root_path.rstrip("/").split("/")[-1]
    tree = Tree(f"[bold cyan]{root_name}/[/bold cyan]")
    dirs: dict[str, Tree] = {}

    entry_set = set(analysis.entry_points)
    danger_set = {h.file_path for h in analysis.hotspots if h.is_danger_zone}

    # Sort files by path
    sorted_files = sorted(analysis.files, key=lambda f: f.relative_path)

    for f in sorted_files[:100]:  # Limit tree size
        parts = f.relative_path.split("/")
        current = tree
        for i, part in enumerate(parts[:-1]):
            dir_path = "/".join(parts[: i + 1])
            if dir_path not in dirs:
                dirs[dir_path] = current.add(f"[bold]{part}/[/bold]")
            current = dirs[dir_path]

        # File node with annotations
        filename = parts[-1]
        annotations: list[str] = []
        if f.relative_path in entry_set:
            annotations.append("[green]★ entry[/green]")
        if f.relative_path in danger_set:
            annotations.append("[red]⚠ hotspot[/red]")

        label = f"{filename} [dim]({f.code_lines} loc)[/dim]"
        if annotations:
            label += " " + " ".join(annotations)
        current.add(label)

    console.print(tree)


def _classify_entry_point(path: str) -> str:
    """Classify what type of entry point a file is."""
    name = path.split("/")[-1].lower()
    if "cli" in name or "command" in name:
        return "CLI"
    if "main" in name or "__main__" in name:
        return "Main"
    if "app" in name or "server" in name:
        return "Application"
    if "route" in name or "api" in name:
        return "API"
    if "index" in name:
        return "Index"
    if "manage" in name:
        return "Management"
    return "Entry"
