"""Lens CLI — all commands powered by Click."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console

import lens


@click.group()
@click.version_option(version=lens.__version__, prog_name="lens")
def main() -> None:
    """Lens — Explain any codebase in 30 seconds."""


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--depth", default=50, help="Max directory depth to scan.")
@click.option("--ignore", multiple=True, help="Extra patterns to ignore.")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def scan(path: str, depth: int, ignore: tuple[str, ...], no_git: bool) -> None:
    """Scan a codebase and display analysis in the terminal."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.engine import analyze_project
    from lens.renderer.terminal import render_terminal

    analysis = analyze_project(
        root,
        max_depth=depth,
        extra_ignores=list(ignore),
        skip_git=no_git,
        console=console,
    )
    render_terminal(analysis, console)


@main.command(name="map")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", default="lens-report.html", help="Output HTML file path.")
@click.option("--no-open", is_flag=True, help="Don't auto-open in browser.")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def map_cmd(path: str, output: str, no_open: bool, no_git: bool) -> None:
    """Generate an interactive HTML architecture map."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.engine import analyze_project
    from lens.renderer.html import render_html

    analysis = analyze_project(root, skip_git=no_git, console=console)
    output_path = Path(output)
    render_html(analysis, output_path)

    console.print(f"[green]Report generated: {output_path.resolve()}[/green]")

    if not no_open:
        webbrowser.open(f"file://{output_path.resolve()}")


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def explain(path: str, no_git: bool) -> None:
    """Generate a plain-English explanation of the codebase."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.engine import analyze_project

    analysis = analyze_project(root, skip_git=no_git, console=console)
    console.print()
    console.print(analysis.explanation)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def stats(path: str, no_git: bool) -> None:
    """Show quick project statistics."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.engine import analyze_project
    from lens.renderer.terminal import _render_header, _render_language_bar, _render_stats

    analysis = analyze_project(root, skip_git=no_git, console=console)
    _render_header(analysis, console)
    _render_stats(analysis, console)
    _render_language_bar(analysis, console)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "md", "html"]), default="json")
@click.option("--output", "-o", default=None, help="Output file path.")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def export(path: str, fmt: str, output: str | None, no_git: bool) -> None:
    """Export analysis in various formats."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.engine import analyze_project

    analysis = analyze_project(root, skip_git=no_git, console=console)

    if fmt == "json":
        from lens.renderer.json_out import render_json

        out_path = Path(output) if output else None
        result = render_json(analysis, out_path)
        if not output:
            console.print(result)
        else:
            console.print(f"[green]Exported to {output}[/green]")

    elif fmt == "md":
        from lens.renderer.markdown import render_markdown

        out_path = Path(output) if output else None
        result = render_markdown(analysis, out_path)
        if not output:
            console.print(result)
        else:
            console.print(f"[green]Exported to {output}[/green]")

    elif fmt == "html":
        from lens.renderer.html import render_html

        out_path = Path(output or "lens-report.html")
        render_html(analysis, out_path)
        console.print(f"[green]Exported to {out_path}[/green]")


@main.command()
@click.argument("branch1")
@click.argument("branch2")
@click.argument("path", default=".", type=click.Path(exists=True))
def diff(branch1: str, branch2: str, path: str) -> None:
    """Compare two branches and show what changed."""
    console = Console()
    root = Path(path).resolve()

    try:
        from git import Repo

        repo = Repo(root, search_parent_directories=True)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    from rich.table import Table

    try:
        diff_index = repo.commit(branch1).diff(repo.commit(branch2))
    except Exception as e:
        console.print(f"[red]Error comparing branches: {e}[/red]")
        sys.exit(1)

    added = [d.b_path for d in diff_index if d.new_file]
    deleted = [d.a_path for d in diff_index if d.deleted_file]
    modified = [d.a_path for d in diff_index if not d.new_file and not d.deleted_file]

    console.print(f"\n[bold]Comparing [cyan]{branch1}[/cyan] → [cyan]{branch2}[/cyan][/bold]\n")

    table = Table(title="Changes Summary", border_style="dim")
    table.add_column("Type", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("[green]Added[/green]", str(len(added)))
    table.add_row("[red]Deleted[/red]", str(len(deleted)))
    table.add_row("[yellow]Modified[/yellow]", str(len(modified)))
    console.print(table)

    if added:
        console.print("\n[green]New files:[/green]")
        for f in added[:20]:
            console.print(f"  + {f}")

    if deleted:
        console.print("\n[red]Deleted files:[/red]")
        for f in deleted[:20]:
            console.print(f"  - {f}")

    if modified:
        console.print("\n[yellow]Modified files:[/yellow]")
        for f in modified[:20]:
            console.print(f"  ~ {f}")


@main.command()
@click.argument("query")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--max-results", "-n", default=20, help="Maximum number of results.")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def search(query: str, path: str, max_results: int, no_git: bool) -> None:
    """Search the codebase with natural language queries."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.search.formatter import format_results
    from lens.search.indexer import build_index
    from lens.search.query_parser import parse_query
    from lens.search.ranker import rank_results

    index = build_index(root)
    parsed = parse_query(query)
    results = rank_results(index, parsed, root, top_n=max_results, use_git=not no_git)
    format_results(results, parsed.keywords, console)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def health(path: str, no_git: bool) -> None:
    """Calculate codebase health score (0-100)."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from rich.panel import Panel
    from rich.table import Table

    from lens.analyzer.health import calculate_health
    from lens.engine import analyze_project

    analysis = analyze_project(root, skip_git=no_git, console=console)
    report = calculate_health(analysis, root)

    # Grade color
    grade_colors = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}
    color = grade_colors.get(report.grade, "white")

    console.print()
    console.print(
        Panel(
            f"[bold {color}]{report.overall_score:.0f}/100  Grade: {report.grade}[/bold {color}]",
            title="[bold]Codebase Health[/bold]",
            border_style=color,
        )
    )

    table = Table(title="Category Breakdown", border_style="dim")
    table.add_column("Category", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right", style="dim")
    table.add_column("Bar")

    for cat in report.categories:
        cat_color = "green" if cat.score >= 75 else "yellow" if cat.score >= 50 else "red"
        bar_width = int(cat.score / 100 * 20)
        bar = f"[{cat_color}]{'█' * bar_width}[/{cat_color}][dim]{'░' * (20 - bar_width)}[/dim]"
        table.add_row(cat.name, f"[{cat_color}]{cat.score:.0f}[/{cat_color}]", f"{cat.weight:.0%}", bar)

    console.print(table)

    if report.recommendations:
        console.print()
        console.print("[bold]Recommendations:[/bold]")
        for rec in report.recommendations:
            console.print(f"  [yellow]>[/yellow] {rec}")
    console.print()


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--severity", type=click.Choice(["critical", "warning", "info", "all"]), default="all", help="Filter by severity.")
@click.option("--ignore", multiple=True, help="Extra patterns to ignore.")
def todo(path: str, severity: str, ignore: tuple[str, ...]) -> None:
    """Find TODO, FIXME, HACK, and other markers in code."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from rich.table import Table

    from lens.analyzer.markers import scan_markers

    report = scan_markers(root, extra_ignores=list(ignore) if ignore else None)

    if severity != "all":
        filtered = [m for m in report.markers if m.severity == severity]
    else:
        filtered = report.markers

    if not filtered:
        console.print("[green]No markers found.[/green]")
        return

    table = Table(title=f"Code Markers ({len(filtered)} found)", border_style="dim")
    table.add_column("Severity", style="bold")
    table.add_column("Type")
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right")
    table.add_column("Text", max_width=60)

    severity_colors = {"critical": "red", "warning": "yellow", "info": "blue"}

    for m in filtered:
        color = severity_colors.get(m.severity, "white")
        table.add_row(
            f"[{color}]{m.severity}[/{color}]",
            m.marker_type,
            m.file_path,
            str(m.line_number),
            m.text.strip()[:60],
        )

    console.print(table)
    console.print()
    console.print(f"[bold]Summary:[/bold] {report.by_severity}")


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def size(path: str, no_git: bool) -> None:
    """Show visual space breakdown of the codebase."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from rich.panel import Panel
    from rich.table import Table

    from lens.analyzer.size import analyze_size
    from lens.engine import analyze_project

    analysis = analyze_project(root, skip_git=no_git, console=console)
    report = analyze_size(analysis.files, root)

    def _fmt_size(b: int) -> str:
        if b >= 1_048_576:
            return f"{b / 1_048_576:.1f} MB"
        if b >= 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b} B"

    console.print()
    console.print(
        Panel(
            f"[bold]{report.total_files:,} files[/bold]  |  [bold]{_fmt_size(report.total_size_bytes)}[/bold] total",
            title="[bold]Project Size[/bold]",
            border_style="cyan",
        )
    )

    # By directory
    if report.by_directory:
        table = Table(title="By Directory", border_style="dim")
        table.add_column("Directory", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("Bar")

        colors = ["blue", "green", "yellow", "red", "magenta", "cyan"]
        for i, entry in enumerate(report.by_directory[:15]):
            color = colors[i % len(colors)]
            bar_width = max(1, int(entry.percentage / 100 * 30))
            bar = f"[{color}]{'█' * bar_width}[/{color}] {entry.percentage:.1f}%"
            table.add_row(entry.name, _fmt_size(entry.size_bytes), str(entry.file_count), bar)

        console.print(table)

    # By language
    if report.by_language:
        table = Table(title="By Language", border_style="dim")
        table.add_column("Language", style="bold")
        table.add_column("Size", justify="right")
        table.add_column("Lines", justify="right")
        table.add_column("Bar")

        for i, entry in enumerate(report.by_language[:10]):
            color = colors[i % len(colors)]
            bar_width = max(1, int(entry.percentage / 100 * 30))
            bar = f"[{color}]{'█' * bar_width}[/{color}] {entry.percentage:.1f}%"
            table.add_row(entry.name, _fmt_size(entry.size_bytes), f"{entry.code_lines:,}", bar)

        console.print(table)

    # Largest files
    if report.largest_files:
        console.print()
        console.print("[bold]Largest Files:[/bold]")
        for fpath, fsize in report.largest_files[:10]:
            console.print(f"  {fpath} [dim]({_fmt_size(fsize)})[/dim]")
    console.print()


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
def onboard(path: str, no_git: bool) -> None:
    """Interactive codebase walkthrough for new developers."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from lens.engine import analyze_project
    from lens.renderer.onboard import render_onboard

    analysis = analyze_project(root, skip_git=no_git, console=console)
    render_onboard(analysis, console)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low", "all"]), default="all", help="Minimum severity to show.")
@click.option("--ignore", multiple=True, help="Extra patterns to ignore.")
def security(path: str, severity: str, ignore: tuple[str, ...]) -> None:
    """Scan for common security issues."""
    console = Console()
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[red]Error: {path} is not a directory[/red]")
        sys.exit(1)

    from rich.panel import Panel
    from rich.table import Table

    from lens.analyzer.security import scan_security

    report = scan_security(root, extra_ignores=list(ignore) if ignore else None)

    severity_order = ["critical", "high", "medium", "low"]
    if severity != "all":
        min_idx = severity_order.index(severity)
        filtered = [f for f in report.findings if severity_order.index(f.severity) <= min_idx]
    else:
        filtered = report.findings

    # Risk score panel
    risk_color = "red" if report.risk_score >= 50 else "yellow" if report.risk_score >= 20 else "green"
    console.print()
    console.print(
        Panel(
            f"[bold {risk_color}]Risk Score: {report.risk_score:.0f}/100[/bold {risk_color}]\n{report.summary}",
            title="[bold]Security Scan[/bold]",
            border_style=risk_color,
        )
    )

    if filtered:
        table = Table(title=f"Findings ({len(filtered)})", border_style="dim")
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("File", style="cyan")
        table.add_column("Line", justify="right")
        table.add_column("Description", max_width=50)

        severity_colors = {"critical": "red bold", "high": "red", "medium": "yellow", "low": "blue"}
        for f in filtered:
            color = severity_colors.get(f.severity, "white")
            table.add_row(
                f"[{color}]{f.severity.upper()}[/{color}]",
                f.category,
                f.file_path,
                str(f.line_number),
                f.description,
            )
        console.print(table)
    else:
        console.print("[green]No security issues found.[/green]")

    console.print()

    # Exit with code 1 if critical/high findings (CI-friendly)
    critical_high = sum(1 for f in report.findings if f.severity in ("critical", "high"))
    if critical_high:
        sys.exit(1)


if __name__ == "__main__":
    main()
