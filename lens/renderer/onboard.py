"""Interactive onboarding guide renderer using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from lens.models import Language, ProjectAnalysis


def render_onboard(analysis: ProjectAnalysis, console: Console | None = None) -> None:
    """Render an interactive onboarding walkthrough."""
    console = console or Console()

    # Step 1: Welcome - what is this project?
    _render_welcome(analysis, console)

    # Step 2: Project structure overview
    _render_structure(analysis, console)

    # Step 3: Key entry points - where to start reading
    _render_start_here(analysis, console)

    # Step 4: Architecture & patterns
    _render_architecture(analysis, console)

    # Step 5: Dependencies - what does it use?
    _render_deps_overview(analysis, console)

    # Step 6: Quick tips
    _render_tips(analysis, console)


def _render_welcome(analysis: ProjectAnalysis, console: Console) -> None:
    """Render welcome panel with project summary."""
    det = analysis.detection
    name = analysis.root_path.rstrip("/").split("/")[-1]

    lines = [
        f"[bold cyan]{name}[/bold cyan]",
        "",
        f"[dim]Language:[/dim]    {det.primary_language.value}",
    ]

    if det.frameworks:
        fw = ", ".join(f.value for f in det.frameworks if f.value != "None")
        if fw:
            lines.append(f"[dim]Framework:[/dim]   {fw}")

    lines.append(f"[dim]Architecture:[/dim] {analysis.architecture.value}")

    if analysis.explanation:
        lines.append("")
        lines.append(analysis.explanation)

    console.print(Panel(
        "\n".join(lines),
        title="[bold]Welcome to the Codebase[/bold]",
        subtitle="Step 1 of 6",
        border_style="cyan",
    ))
    console.print()


def _render_structure(analysis: ProjectAnalysis, console: Console) -> None:
    """Render project structure as a tree."""
    name = analysis.root_path.rstrip("/").split("/")[-1]
    tree = Tree(f"[bold cyan]{name}/[/bold cyan]")

    # Collect top-level directories from file paths
    top_dirs: dict[str, str] = {}
    for f in analysis.files:
        parts = f.relative_path.split("/")
        if len(parts) > 1:
            top_dir = parts[0]
            if top_dir not in top_dirs:
                top_dirs[top_dir] = _describe_directory(top_dir)

    # Also infer from entry points if files list is empty
    if not top_dirs:
        for ep in analysis.entry_points:
            parts = ep.split("/")
            if len(parts) > 1:
                top_dir = parts[0]
                if top_dir not in top_dirs:
                    top_dirs[top_dir] = _describe_directory(top_dir)

    if not top_dirs:
        console.print(Panel(
            "[dim]No directory structure available.[/dim]",
            title="[bold]Project Structure[/bold]",
            subtitle="Step 2 of 6",
            border_style="cyan",
        ))
        console.print()
        return

    for dir_name in sorted(top_dirs):
        desc = top_dirs[dir_name]
        tree.add(f"[bold]{dir_name}/[/bold] [dim]- {desc}[/dim]")

    console.print(Panel(
        tree,
        title="[bold]Project Structure[/bold]",
        subtitle="Step 2 of 6",
        border_style="cyan",
    ))
    console.print()


def _describe_directory(name: str) -> str:
    """Infer a description for a top-level directory."""
    descriptions: dict[str, str] = {
        "src": "Source code",
        "lib": "Library code",
        "app": "Application code",
        "pkg": "Packages",
        "cmd": "Command entrypoints",
        "internal": "Internal packages",
        "api": "API definitions",
        "server": "Server code",
        "client": "Client code",
        "web": "Web frontend",
        "ui": "User interface",
        "core": "Core logic",
        "utils": "Utilities",
        "helpers": "Helper functions",
        "config": "Configuration",
        "configs": "Configuration",
        "settings": "Settings",
        "tests": "Test suite",
        "test": "Test suite",
        "spec": "Test specifications",
        "__tests__": "Test suite",
        "docs": "Documentation",
        "doc": "Documentation",
        "scripts": "Build/utility scripts",
        "bin": "Executable scripts",
        "tools": "Development tools",
        "migrations": "Database migrations",
        "models": "Data models",
        "views": "View layer",
        "controllers": "Controllers",
        "routes": "Route definitions",
        "middleware": "Middleware",
        "services": "Service layer",
        "static": "Static assets",
        "public": "Public assets",
        "assets": "Assets",
        "templates": "Templates",
        "components": "UI components",
        "pages": "Page components",
        "styles": "Stylesheets",
        "types": "Type definitions",
        "interfaces": "Interface definitions",
        "proto": "Protocol buffer definitions",
        "vendor": "Vendored dependencies",
        "third_party": "Third-party code",
        "examples": "Example code",
        "fixtures": "Test fixtures",
        "data": "Data files",
        "resources": "Resources",
        "deploy": "Deployment configuration",
        "infra": "Infrastructure code",
        ".github": "GitHub workflows and config",
        ".circleci": "CircleCI configuration",
    }
    return descriptions.get(name.lower(), "Project directory")


def _render_start_here(analysis: ProjectAnalysis, console: Console) -> None:
    """Render entry points table with reading guidance."""
    if not analysis.entry_points:
        console.print(Panel(
            "[dim]No entry points detected.[/dim]",
            title="[bold]Start Here[/bold]",
            subtitle="Step 3 of 6",
            border_style="green",
        ))
        console.print()
        return

    table = Table(
        title="Start Here - Read These First",
        border_style="green",
        title_style="bold green",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("File", style="green")
    table.add_column("Type", style="dim")
    table.add_column("Tip", style="italic")

    for i, ep in enumerate(analysis.entry_points[:5], 1):
        ep_type = _classify_entry_point(ep)
        tip = _reading_tip(ep)
        table.add_row(str(i), ep, ep_type, tip)

    console.print(Panel(
        table,
        title="[bold]Start Here[/bold]",
        subtitle="Step 3 of 6",
        border_style="green",
    ))
    console.print()


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


def _reading_tip(path: str) -> str:
    """Generate a reading tip for an entry point."""
    name = path.split("/")[-1].lower()
    if "cli" in name or "command" in name:
        return "Start here to understand CLI commands"
    if "main" in name or "__main__" in name:
        return "Main execution flow starts here"
    if "app" in name or "server" in name:
        return "Application setup and configuration"
    if "route" in name or "api" in name:
        return "API endpoints and routing"
    if "index" in name:
        return "Module entry point"
    return "Read this first, then follow imports"


def _render_architecture(analysis: ProjectAnalysis, console: Console) -> None:
    """Render architecture pattern overview."""
    lines: list[str] = []

    lines.append(f"[bold]Pattern:[/bold] {analysis.architecture.value}")
    lines.append("")

    if analysis.explanation:
        lines.append(analysis.explanation)
    else:
        lines.append("[dim]No architecture description available.[/dim]")

    console.print(Panel(
        "\n".join(lines),
        title="[bold]Architecture & Patterns[/bold]",
        subtitle="Step 4 of 6",
        border_style="magenta",
    ))
    console.print()


def _render_deps_overview(analysis: ProjectAnalysis, console: Console) -> None:
    """Render dependencies split into internal and external."""
    has_internal = bool(analysis.dependencies)
    has_external = bool(analysis.external_deps)

    if not has_internal and not has_external:
        console.print(Panel(
            "[dim]No dependencies detected.[/dim]",
            title="[bold]Dependencies[/bold]",
            subtitle="Step 5 of 6",
            border_style="blue",
        ))
        console.print()
        return

    table = Table(
        title="Dependencies Overview",
        border_style="blue",
        title_style="bold blue",
    )

    # Internal dependencies: top imported modules
    if has_internal:
        table.add_column("Internal (top modules)", style="yellow")
    if has_external:
        table.add_column("External (packages)", style="cyan")

    # Collect internal module targets, count occurrences
    internal_targets: dict[str, int] = {}
    for dep in analysis.dependencies:
        target = dep.target
        internal_targets[target] = internal_targets.get(target, 0) + 1

    sorted_internal = sorted(internal_targets.items(), key=lambda x: x[1], reverse=True)[:10]
    external_top = analysis.external_deps[:10]

    max_rows = max(len(sorted_internal), len(external_top))

    for i in range(max_rows):
        row: list[str] = []
        if has_internal:
            if i < len(sorted_internal):
                mod, count = sorted_internal[i]
                row.append(f"{mod} ({count} imports)")
            else:
                row.append("")
        if has_external:
            if i < len(external_top):
                row.append(external_top[i])
            else:
                row.append("")
        table.add_row(*row)

    console.print(Panel(
        table,
        title="[bold]Dependencies[/bold]",
        subtitle="Step 5 of 6",
        border_style="blue",
    ))
    console.print()


def _render_tips(analysis: ProjectAnalysis, console: Console) -> None:
    """Render contextual tips based on what was detected."""
    det = analysis.detection
    tips: list[str] = []

    if det.has_tests:
        test_cmd = _test_command(det.primary_language)
        tips.append(f"Run tests with: [bold]{test_cmd}[/bold]")

    if det.has_docker:
        tips.append("Use Docker for development environment")

    if det.has_ci:
        tips.append("CI/CD is configured -- check PRs for automated checks")

    tips.append("Start by reading entry points, then follow imports")

    if analysis.hotspots:
        tips.append("Check hotspots for files that change often and have high complexity")

    bullet_lines = "\n".join(f"  [bold cyan]*[/bold cyan] {tip}" for tip in tips)

    console.print(Panel(
        bullet_lines,
        title="[bold]Quick Tips[/bold]",
        subtitle="Step 6 of 6",
        border_style="yellow",
    ))
    console.print()


def _test_command(language: Language) -> str:
    """Return the typical test command for a language."""
    commands: dict[Language, str] = {
        Language.PYTHON: "pytest",
        Language.JAVASCRIPT: "npm test",
        Language.TYPESCRIPT: "npm test",
        Language.GO: "go test ./...",
        Language.RUST: "cargo test",
        Language.JAVA: "mvn test",
        Language.RUBY: "bundle exec rspec",
        Language.PHP: "phpunit",
    }
    return commands.get(language, "check project docs for test instructions")
