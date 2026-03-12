"""Core data models shared across all Lens modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Language(Enum):
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    GO = "Go"
    RUST = "Rust"
    JAVA = "Java"
    RUBY = "Ruby"
    PHP = "PHP"
    C = "C"
    CPP = "C++"
    CSHARP = "C#"
    SWIFT = "Swift"
    KOTLIN = "Kotlin"
    SHELL = "Shell"
    HTML = "HTML"
    CSS = "CSS"
    SQL = "SQL"
    MARKDOWN = "Markdown"
    YAML = "YAML"
    JSON = "JSON"
    TOML = "TOML"
    DOCKERFILE = "Dockerfile"
    OTHER = "Other"


class ArchitecturePattern(Enum):
    MONOREPO = "Monorepo"
    MVC = "MVC"
    MICROSERVICES = "Microservices"
    SERVERLESS = "Serverless"
    CLI_TOOL = "CLI Tool"
    LIBRARY = "Library"
    FULLSTACK = "Fullstack"
    API_SERVICE = "API Service"
    STATIC_SITE = "Static Site"
    UNKNOWN = "Unknown"


class Framework(Enum):
    DJANGO = "Django"
    FLASK = "Flask"
    FASTAPI = "FastAPI"
    REACT = "React"
    NEXTJS = "Next.js"
    VUE = "Vue"
    SVELTE = "Svelte"
    EXPRESS = "Express"
    FASTIFY = "Fastify"
    GIN = "Gin"
    ECHO = "Echo"
    ACTIX = "Actix"
    ROCKET = "Rocket"
    SPRING = "Spring"
    RAILS = "Rails"
    LARAVEL = "Laravel"
    NONE = "None"


@dataclass
class FileInfo:
    """Information about a single file."""

    path: Path
    relative_path: str
    language: Language
    size_bytes: int
    line_count: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0


@dataclass
class ImportInfo:
    """A single import statement."""

    module: str
    names: list[str] = field(default_factory=list)
    is_relative: bool = False
    is_external: bool = False
    source_file: str = ""


@dataclass
class FunctionInfo:
    """A function or method definition."""

    name: str
    file_path: str
    line_number: int
    is_method: bool = False
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    complexity: int = 1


@dataclass
class ClassInfo:
    """A class definition."""

    name: str
    file_path: str
    line_number: int
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Parsed information about a single source file/module."""

    file_path: str
    language: Language
    imports: list[ImportInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    entry_point: bool = False


@dataclass
class DependencyEdge:
    """A dependency from one file to another."""

    source: str
    target: str
    import_names: list[str] = field(default_factory=list)


@dataclass
class GitFileHistory:
    """Git history for a single file."""

    file_path: str
    commit_count: int = 0
    last_modified: str = ""
    contributors: list[str] = field(default_factory=list)
    churn_score: float = 0.0


@dataclass
class HotspotInfo:
    """Hotspot score for a file."""

    file_path: str
    score: float = 0.0
    change_frequency: float = 0.0
    complexity: float = 0.0
    size_factor: float = 0.0
    is_danger_zone: bool = False


@dataclass
class ProjectDetection:
    """Result of project type detection."""

    primary_language: Language
    languages: dict[Language, int] = field(default_factory=dict)
    frameworks: list[Framework] = field(default_factory=list)
    package_manager: str = ""
    architecture: ArchitecturePattern = ArchitecturePattern.UNKNOWN
    has_tests: bool = False
    has_ci: bool = False
    has_docker: bool = False
    has_docs: bool = False


@dataclass
class ProjectStats:
    """Aggregated project statistics."""

    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    language_breakdown: dict[str, int] = field(default_factory=dict)
    language_percentages: dict[str, float] = field(default_factory=dict)
    avg_file_size: float = 0.0
    largest_files: list[tuple[str, int]] = field(default_factory=list)
    file_count_by_language: dict[str, int] = field(default_factory=dict)


@dataclass
class ProjectAnalysis:
    """Complete analysis result for a project."""

    root_path: str
    detection: ProjectDetection
    stats: ProjectStats
    files: list[FileInfo] = field(default_factory=list)
    modules: list[ModuleInfo] = field(default_factory=list)
    dependencies: list[DependencyEdge] = field(default_factory=list)
    external_deps: list[str] = field(default_factory=list)
    circular_deps: list[list[str]] = field(default_factory=list)
    hotspots: list[HotspotInfo] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    git_history: list[GitFileHistory] = field(default_factory=list)
    architecture: ArchitecturePattern = ArchitecturePattern.UNKNOWN
    explanation: str = ""
