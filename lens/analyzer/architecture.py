"""Architecture pattern detection."""

from __future__ import annotations

from pathlib import Path

from lens.models import ArchitecturePattern, Framework, ProjectDetection


def detect_architecture(root: Path, detection: ProjectDetection) -> ArchitecturePattern:
    """Detect the architecture pattern of the project.

    Uses directory structure, framework detection, and file patterns
    to determine the overall architecture.
    """
    root = root.resolve()
    scores: dict[ArchitecturePattern, int] = {p: 0 for p in ArchitecturePattern}

    # Monorepo signals
    if (root / "packages").is_dir():
        scores[ArchitecturePattern.MONOREPO] += 3
    if (root / "apps").is_dir():
        scores[ArchitecturePattern.MONOREPO] += 3
    if (root / "lerna.json").exists():
        scores[ArchitecturePattern.MONOREPO] += 5
    if (root / "pnpm-workspace.yaml").exists():
        scores[ArchitecturePattern.MONOREPO] += 5
    if (root / "nx.json").exists():
        scores[ArchitecturePattern.MONOREPO] += 5

    # Microservices signals
    if (root / "services").is_dir():
        scores[ArchitecturePattern.MICROSERVICES] += 3
        # Count subdirectories with their own config
        services_dir = root / "services"
        service_count = sum(
            1
            for d in services_dir.iterdir()
            if d.is_dir()
            and any((d / f).exists() for f in ["Dockerfile", "package.json", "go.mod", "pyproject.toml"])
        )
        if service_count >= 2:
            scores[ArchitecturePattern.MICROSERVICES] += 4
    if (root / "docker-compose.yml").exists():
        scores[ArchitecturePattern.MICROSERVICES] += 1

    # Serverless signals
    if (root / "serverless.yml").exists() or (root / "serverless.yaml").exists():
        scores[ArchitecturePattern.SERVERLESS] += 5
    if (root / "sam.yaml").exists() or (root / "template.yaml").exists():
        scores[ArchitecturePattern.SERVERLESS] += 5
    if (root / "netlify.toml").exists() or (root / "vercel.json").exists():
        scores[ArchitecturePattern.SERVERLESS] += 2

    # Fullstack signals
    has_frontend = any(
        (root / d).is_dir()
        for d in ["frontend", "client", "web", "src/components", "src/pages", "pages"]
    )
    has_backend = any(
        (root / d).is_dir() for d in ["backend", "server", "api", "src/api", "src/routes"]
    )
    if has_frontend and has_backend:
        scores[ArchitecturePattern.FULLSTACK] += 4
    if Framework.NEXTJS in detection.frameworks:
        scores[ArchitecturePattern.FULLSTACK] += 3

    # MVC signals
    mvc_dirs = ["models", "views", "controllers", "templates"]
    mvc_count = sum(1 for d in mvc_dirs if (root / d).is_dir())
    if mvc_count >= 2:
        scores[ArchitecturePattern.MVC] += mvc_count * 2
    if Framework.DJANGO in detection.frameworks:
        scores[ArchitecturePattern.MVC] += 3
    if Framework.RAILS in detection.frameworks:
        scores[ArchitecturePattern.MVC] += 3

    # API service signals
    if has_backend and not has_frontend:
        scores[ArchitecturePattern.API_SERVICE] += 3
    if Framework.FASTAPI in detection.frameworks or Framework.EXPRESS in detection.frameworks:
        scores[ArchitecturePattern.API_SERVICE] += 2

    # CLI tool signals
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "[project.scripts]" in content or "console_scripts" in content:
                scores[ArchitecturePattern.CLI_TOOL] += 4
        except OSError:
            pass
    if (root / "bin").is_dir():
        scores[ArchitecturePattern.CLI_TOOL] += 2

    # Library signals
    if (root / "src" / "lib").is_dir() or (root / "lib").is_dir():
        scores[ArchitecturePattern.LIBRARY] += 2
    setup_py = root / "setup.py"
    if setup_py.exists():
        scores[ArchitecturePattern.LIBRARY] += 2

    # Static site signals
    static_configs = ["gatsby-config.js", "hugo.toml", "_config.yml", "mkdocs.yml", "docusaurus.config.js"]
    if any((root / c).exists() for c in static_configs):
        scores[ArchitecturePattern.STATIC_SITE] += 5

    # Find highest score
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] == 0:
        return ArchitecturePattern.UNKNOWN
    return best
