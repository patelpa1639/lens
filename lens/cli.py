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


if __name__ == "__main__":
    main()
