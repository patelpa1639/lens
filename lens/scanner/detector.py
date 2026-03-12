"""Auto-detect project language, framework, and type."""

from __future__ import annotations

from pathlib import Path

from lens.models import (
    ArchitecturePattern,
    Framework,
    Language,
    ProjectDetection,
)
from lens.utils.file_utils import collect_files, detect_language

# Config files that indicate language/framework
_LANGUAGE_MARKERS: dict[str, Language] = {
    "pyproject.toml": Language.PYTHON,
    "setup.py": Language.PYTHON,
    "setup.cfg": Language.PYTHON,
    "requirements.txt": Language.PYTHON,
    "Pipfile": Language.PYTHON,
    "poetry.lock": Language.PYTHON,
    "package.json": Language.JAVASCRIPT,
    "tsconfig.json": Language.TYPESCRIPT,
    "go.mod": Language.GO,
    "go.sum": Language.GO,
    "Cargo.toml": Language.RUST,
    "Cargo.lock": Language.RUST,
    "pom.xml": Language.JAVA,
    "build.gradle": Language.JAVA,
    "build.gradle.kts": Language.KOTLIN,
    "Gemfile": Language.RUBY,
    "composer.json": Language.PHP,
    "Package.swift": Language.SWIFT,
}

_FRAMEWORK_MARKERS: dict[str, Framework] = {
    "manage.py": Framework.DJANGO,
    "next.config.js": Framework.NEXTJS,
    "next.config.mjs": Framework.NEXTJS,
    "next.config.ts": Framework.NEXTJS,
    "nuxt.config.ts": Framework.VUE,
    "svelte.config.js": Framework.SVELTE,
    "vite.config.ts": Framework.REACT,  # Could be Vue too, but common with React
}

_PACKAGE_MANAGERS: dict[str, str] = {
    "pyproject.toml": "pip",
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "poetry.lock": "poetry",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "go.mod": "go modules",
    "go.sum": "go modules",
    "Cargo.toml": "cargo",
    "Cargo.lock": "cargo",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
}


def detect_project(root: Path) -> ProjectDetection:
    """Detect project language, framework, and architecture."""
    root = root.resolve()
    detection = ProjectDetection(primary_language=Language.OTHER)

    # Scan for marker files
    marker_languages: list[Language] = []
    for marker, lang in _LANGUAGE_MARKERS.items():
        if (root / marker).exists():
            marker_languages.append(lang)

    # Detect frameworks
    for marker, framework in _FRAMEWORK_MARKERS.items():
        if (root / marker).exists():
            detection.frameworks.append(framework)

    # Detect framework from package.json dependencies
    _detect_js_frameworks(root, detection)

    # Detect framework from Python dependencies
    _detect_python_frameworks(root, detection)

    # Detect package manager
    for marker, pm in _PACKAGE_MANAGERS.items():
        if (root / marker).exists():
            detection.package_manager = pm
            break

    # Count files by language
    files = collect_files(root)
    lang_counts: dict[Language, int] = {}
    for f in files:
        lang = detect_language(f)
        if lang not in (Language.OTHER, Language.MARKDOWN, Language.YAML, Language.JSON, Language.TOML):
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    detection.languages = lang_counts

    # Determine primary language
    if lang_counts:
        detection.primary_language = max(lang_counts, key=lang_counts.get)  # type: ignore[arg-type]
    elif marker_languages:
        detection.primary_language = marker_languages[0]

    # Detect project features
    detection.has_tests = _has_tests(root)
    detection.has_ci = _has_ci(root)
    detection.has_docker = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()
    detection.has_docs = (root / "docs").is_dir() or (root / "README.md").exists()

    # Detect architecture pattern
    detection.architecture = _detect_architecture(root, detection)

    return detection


def _detect_js_frameworks(root: Path, detection: ProjectDetection) -> None:
    """Detect JavaScript frameworks from package.json."""
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return
    try:
        import json

        pkg = json.loads(pkg_path.read_text())
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        framework_deps = {
            "react": Framework.REACT,
            "next": Framework.NEXTJS,
            "vue": Framework.VUE,
            "svelte": Framework.SVELTE,
            "express": Framework.EXPRESS,
            "fastify": Framework.FASTIFY,
        }

        for dep, framework in framework_deps.items():
            if dep in all_deps and framework not in detection.frameworks:
                detection.frameworks.append(framework)
    except (ValueError, OSError):
        pass


def _detect_python_frameworks(root: Path, detection: ProjectDetection) -> None:
    """Detect Python frameworks from pyproject.toml or requirements.txt."""
    framework_packages = {
        "django": Framework.DJANGO,
        "flask": Framework.FLASK,
        "fastapi": Framework.FASTAPI,
    }

    # Check pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text().lower()
            for pkg, framework in framework_packages.items():
                if pkg in content and framework not in detection.frameworks:
                    detection.frameworks.append(framework)
        except OSError:
            pass

    # Check requirements.txt
    req = root / "requirements.txt"
    if req.exists():
        try:
            content = req.read_text().lower()
            for pkg, framework in framework_packages.items():
                if pkg in content and framework not in detection.frameworks:
                    detection.frameworks.append(framework)
        except OSError:
            pass


def _has_tests(root: Path) -> bool:
    """Check if project has tests."""
    test_indicators = [
        root / "tests",
        root / "test",
        root / "__tests__",
        root / "spec",
    ]
    for d in test_indicators:
        if d.is_dir():
            return True
    # Check for test config files
    test_configs = ["pytest.ini", "jest.config.js", "jest.config.ts", ".mocharc.yml", "vitest.config.ts"]
    return any((root / c).exists() for c in test_configs)


def _has_ci(root: Path) -> bool:
    """Check if project has CI/CD configuration."""
    ci_paths = [
        root / ".github" / "workflows",
        root / ".gitlab-ci.yml",
        root / ".circleci",
        root / "Jenkinsfile",
        root / ".travis.yml",
    ]
    return any(p.exists() for p in ci_paths)


def _detect_architecture(root: Path, detection: ProjectDetection) -> ArchitecturePattern:
    """Detect architecture pattern from project structure."""
    has_frontend = any(
        (root / d).is_dir()
        for d in ["frontend", "client", "web", "app", "src/components", "src/pages", "pages", "app"]
    )
    has_backend = any(
        (root / d).is_dir() for d in ["backend", "server", "api", "src/api", "src/routes"]
    )

    # Monorepo detection
    if (root / "packages").is_dir() or (root / "apps").is_dir():
        return ArchitecturePattern.MONOREPO
    if (root / "lerna.json").exists() or (root / "pnpm-workspace.yaml").exists():
        return ArchitecturePattern.MONOREPO

    # Microservices
    if (root / "services").is_dir() or (root / "microservices").is_dir():
        return ArchitecturePattern.MICROSERVICES

    # Serverless
    if (root / "serverless.yml").exists() or (root / "sam.yaml").exists():
        return ArchitecturePattern.SERVERLESS

    # Fullstack
    if has_frontend and has_backend:
        return ArchitecturePattern.FULLSTACK

    # MVC (Django, Rails, etc.)
    if any(
        (root / d).is_dir()
        for d in ["models", "views", "controllers", "templates"]
    ):
        return ArchitecturePattern.MVC

    # API service
    if has_backend and not has_frontend:
        return ArchitecturePattern.API_SERVICE

    # CLI tool
    if detection.primary_language == Language.PYTHON:
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "[project.scripts]" in content or "console_scripts" in content:
                    return ArchitecturePattern.CLI_TOOL
            except OSError:
                pass

    # Library
    if (root / "src").is_dir() and not has_frontend:
        return ArchitecturePattern.LIBRARY

    return ArchitecturePattern.UNKNOWN
