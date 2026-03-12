"""Format search results for terminal output using Rich."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.text import Text

from lens.search.ranker import SearchResult


@dataclass
class GroupedResult:
    """Search results grouped by file."""

    file_path: Path
    hits: list[SearchResult] = field(default_factory=list)


def group_by_file(results: list[SearchResult]) -> list[GroupedResult]:
    """Group a flat list of *SearchResult* by file path, preserving score order."""
    groups: dict[Path, GroupedResult] = {}
    for r in results:
        if r.file_path not in groups:
            groups[r.file_path] = GroupedResult(file_path=r.file_path)
        groups[r.file_path].hits.append(r)
    return list(groups.values())


def _highlight_terms(line: str, terms: list[str]) -> Text:
    """Return a Rich *Text* object with matching terms highlighted."""
    text = Text(line)
    lower_line = line.lower()
    for term in terms:
        lower_term = term.lower()
        start = 0
        while True:
            idx = lower_line.find(lower_term, start)
            if idx == -1:
                break
            text.stylize("bold yellow", idx, idx + len(lower_term))
            start = idx + 1
    return text


def get_context_lines(file_path: Path, line_number: int, context: int = 3) -> list[tuple[int, str]]:
    """Read surrounding lines from a file for context display.

    Returns a list of ``(line_number, text)`` pairs.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [(line_number, "")]
    lines = content.splitlines()
    start = max(0, line_number - 1 - context)
    end = min(len(lines), line_number + context)
    return [(i + 1, lines[i]) for i in range(start, end)]


def format_results(
    results: list[SearchResult],
    terms: list[str],
    console: Console | None = None,
    context_lines: int = 3,
    show_score: bool = True,
) -> None:
    """Pretty-print grouped search results to the terminal."""
    if console is None:
        console = Console()

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    groups = group_by_file(results)
    total = sum(len(g.hits) for g in groups)
    console.print(f"\n[bold green]Found {total} match(es) across {len(groups)} file(s)[/bold green]\n")

    for group in groups:
        header = f"[bold cyan]{escape(str(group.file_path))}[/bold cyan]"
        console.print(header)

        for hit in group.hits:
            score_str = f"  [dim](score: {hit.score:.1f})[/dim]" if show_score else ""
            console.print(f"  Line {hit.line_number} [{hit.kind}]{score_str}")

            ctx = get_context_lines(hit.file_path, hit.line_number, context=context_lines)
            for ln, text in ctx:
                marker = ">" if ln == hit.line_number else " "
                prefix = f"  {marker} {ln:>4} | "
                highlighted = _highlight_terms(text, terms)
                line_text = Text(prefix)
                line_text.append(highlighted)
                console.print(line_text)
            console.print()

        console.print()
