"""Core analysis engine — orchestrates scanners, analyzers, and renderers."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from lens.analyzer.architecture import detect_architecture
from lens.analyzer.complexity import analyze_complexity
from lens.analyzer.dependencies import build_dependency_graph
from lens.analyzer.entry_points import find_entry_points
from lens.analyzer.hotspots import calculate_hotspots
from lens.analyzer.stats import calculate_stats
from lens.models import (
    ArchitecturePattern,
    FileInfo,
    Language,
    ModuleInfo,
    ProjectAnalysis,
    ProjectDetection,
    ProjectStats,
)
from lens.scanner.detector import detect_project
from lens.scanner.generic_scanner import scan_generic_file
from lens.scanner.git_scanner import scan_git_history
from lens.scanner.go_scanner import scan_go_file
from lens.scanner.js_scanner import scan_js_file
from lens.scanner.python_scanner import scan_python_file
from lens.scanner.rust_scanner import scan_rust_file
from lens.utils.file_utils import collect_files, count_lines, detect_language, read_file_safe


def analyze_project(
    root: Path,
    max_depth: int = 50,
    extra_ignores: list[str] | None = None,
    skip_git: bool = False,
    console: Console | None = None,
) -> ProjectAnalysis:
    """Run full analysis on a project directory."""
    root = root.resolve()
    console = console or Console()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # Phase 1: Detect project type
        progress.add_task("Detecting project type...", total=None)
        detection = detect_project(root)

        # Phase 2: Collect files
        progress.add_task("Scanning files...", total=None)
        file_paths = collect_files(root, max_depth=max_depth, extra_ignores=extra_ignores)

        # Phase 3: Build file info
        progress.add_task("Analyzing files...", total=None)
        files = _build_file_info(file_paths, root)

        # Phase 4: Parse modules
        progress.add_task("Parsing source code...", total=None)
        modules = _parse_modules(file_paths, root)

        # Phase 5: Git history
        git_history = []
        if not skip_git:
            progress.add_task("Analyzing git history...", total=None)
            git_history = scan_git_history(root)

        # Phase 6: Run analyzers
        progress.add_task("Running analysis...", total=None)
        stats = calculate_stats(files)
        architecture = detect_architecture(root, detection)
        deps, ext_deps, circular = build_dependency_graph(modules, root)
        entry_points = find_entry_points(modules, root)
        hotspots = calculate_hotspots(files, modules, git_history)
        analyze_complexity(modules)  # Compute complexity scores (side effect on modules)

        # Phase 7: Generate explanation
        explanation = _generate_explanation(detection, stats, architecture, entry_points, ext_deps)

    return ProjectAnalysis(
        root_path=str(root),
        detection=detection,
        stats=stats,
        files=files,
        modules=modules,
        dependencies=deps,
        external_deps=ext_deps,
        circular_deps=circular,
        hotspots=hotspots,
        entry_points=entry_points,
        git_history=git_history,
        architecture=architecture,
        explanation=explanation,
    )


def _build_file_info(file_paths: list[Path], root: Path) -> list[FileInfo]:
    """Build FileInfo objects for all files."""
    files: list[FileInfo] = []
    for path in file_paths:
        language = detect_language(path)
        try:
            size = path.stat().st_size
        except OSError:
            continue

        content = read_file_safe(path)
        if content is not None:
            total, code, blank, comment = count_lines(content)
        else:
            total = code = blank = comment = 0

        files.append(
            FileInfo(
                path=path,
                relative_path=str(path.relative_to(root)),
                language=language,
                size_bytes=size,
                line_count=total,
                code_lines=code,
                blank_lines=blank,
                comment_lines=comment,
            )
        )
    return files


def _parse_modules(file_paths: list[Path], root: Path) -> list[ModuleInfo]:
    """Parse all source files into ModuleInfo objects."""
    modules: list[ModuleInfo] = []

    scanner_map = {
        Language.PYTHON: scan_python_file,
        Language.JAVASCRIPT: scan_js_file,
        Language.TYPESCRIPT: scan_js_file,
        Language.GO: scan_go_file,
        Language.RUST: scan_rust_file,
    }

    for path in file_paths:
        language = detect_language(path)
        scanner = scanner_map.get(language)

        if scanner:
            module = scanner(path, root)
        else:
            module = scan_generic_file(path, root)

        if module:
            modules.append(module)

    return modules


def _generate_explanation(
    detection: ProjectDetection,
    stats: ProjectStats,
    architecture: ArchitecturePattern,
    entry_points: list[str],
    ext_deps: list[str],
) -> str:
    """Generate a plain-English explanation of the project."""
    parts: list[str] = []

    # What is it?
    lang = detection.primary_language.value
    arch = architecture.value

    if detection.frameworks:
        fw = " and ".join(f.value for f in detection.frameworks[:2])
        parts.append(f"This is a {lang} {arch.lower()} using {fw}.")
    else:
        parts.append(f"This is a {lang} {arch.lower()}.")

    # Size
    if stats.code_lines > 0:
        parts.append(
            f"It contains {stats.total_files:,} files with {stats.code_lines:,} lines of code"
            f" across {len(stats.language_breakdown)} language(s)."
        )

    # Languages
    top_langs = list(stats.language_percentages.items())[:3]
    if len(top_langs) > 1:
        lang_parts = [f"{lang} ({pct}%)" for lang, pct in top_langs]
        parts.append(f"Primary languages: {', '.join(lang_parts)}.")

    # Entry points
    if entry_points:
        ep_count = len(entry_points)
        main_ep = entry_points[0].split("/")[-1]
        parts.append(f"There are {ep_count} entry point(s), starting from {main_ep}.")

    # Dependencies
    if ext_deps:
        parts.append(f"The project depends on {len(ext_deps)} external package(s).")

    # Features
    features = []
    if detection.has_tests:
        features.append("tests")
    if detection.has_ci:
        features.append("CI/CD")
    if detection.has_docker:
        features.append("Docker")
    if features:
        parts.append(f"It includes {', '.join(features)}.")

    return " ".join(parts)
