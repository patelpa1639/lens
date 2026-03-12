```
 ██╗     ███████╗███╗   ██╗███████╗
 ██║     ██╔════╝████╗  ██║██╔════╝
 ██║     █████╗  ██╔██╗ ██║███████╗
 ██║     ██╔══╝  ██║╚██╗██║╚════██║
 ███████╗███████╗██║ ╚████║███████║
 ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝
```

**Explain any codebase in 30 seconds.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

Lens is a CLI tool that instantly generates interactive architecture maps, dependency graphs, and intelligence reports for any codebase. No AI APIs, no cloud — everything runs locally.

## Quick Install

```bash
pip install lens-cli
```

## Usage

```bash
# Full terminal analysis
lens scan .

# Interactive HTML architecture map
lens map .

# Plain English explanation
lens explain .

# Quick stats
lens stats .

# Export as JSON, Markdown, or HTML
lens export . --format json
lens export . --format md --output report.md

# Compare branches
lens diff main feature-branch
```

## What You Get

### `lens scan` — Terminal Analysis

Beautiful Rich-powered terminal output with:
- Project detection (language, framework, architecture pattern)
- Language breakdown with colored bar chart
- Entry points highlighted
- Hotspot detection (high-risk files)
- Dependency overview
- Annotated file tree

### `lens map` — Interactive HTML Report

A single self-contained HTML file featuring:
- Interactive file tree sidebar with search
- Force-directed dependency graph (zoom, drag, hover)
- Language breakdown donut chart
- Hotspot visualization table
- Stats dashboard
- Git activity data
- Dark mode developer aesthetic
- Works completely offline

### `lens explain` — Plain English

```
This is a Python CLI tool using Click. It contains 42 files with 3,847 lines
of code across 2 languages. Primary languages: Python (95.2%), Shell (4.8%).
There are 3 entry points, starting from cli.py. The project depends on 5
external packages. It includes tests, CI/CD.
```

## Supported Languages

| Language | Detection | Parsing | Dependency Mapping |
|----------|-----------|---------|-------------------|
| Python | Full | AST-based | imports, requirements.txt, pyproject.toml |
| JavaScript | Full | Regex | import/require, package.json |
| TypeScript | Full | Regex | import/require, package.json |
| Go | Full | Regex | import, go.mod |
| Rust | Full | Regex | use, Cargo.toml |
| Others | Basic | Heuristic | Generic patterns |

## Architecture Detection

Lens automatically identifies:
- **Monorepo** — packages/, apps/, workspaces
- **MVC** — models/views/controllers structure
- **Microservices** — services/ with individual configs
- **Serverless** — serverless.yml, SAM templates
- **Fullstack** — frontend + backend directories
- **CLI Tool** — console_scripts entry points
- **Library** — src/lib structure
- **API Service** — backend without frontend
- **Static Site** — Gatsby, Hugo, etc.

## Framework Detection

Python: Django, Flask, FastAPI
JavaScript/TypeScript: React, Next.js, Vue, Svelte, Express, Fastify
Go: Gin, Echo
Rust: Actix, Rocket

## Features

- **Zero API keys** — everything runs locally, no cloud dependencies
- **Works offline** — after pip install, no internet needed
- **Fast** — parallel file scanning, content-hash caching
- **Multi-language** — Python, JS/TS, Go, Rust, and generic fallback
- **Git-aware** — hotspot detection from commit history
- **Single HTML** — self-contained report, no CDN dependencies
- **Extensible** — easy to add new language scanners

## Export Formats

| Format | Command | Description |
|--------|---------|-------------|
| Terminal | `lens scan` | Rich terminal output |
| HTML | `lens map` | Interactive single-file report |
| JSON | `lens export --format json` | Full structured data |
| Markdown | `lens export --format md` | With Mermaid dependency diagrams |

## JSON Schema

The JSON export contains:
```json
{
  "version": "0.1.0",
  "project": { "primaryLanguage", "frameworks", "architecture", ... },
  "stats": { "totalFiles", "codeLines", "languageBreakdown", ... },
  "files": [{ "path", "language", "lines", "size" }],
  "dependencies": { "internal": [...], "external": [...], "circular": [...] },
  "hotspots": [{ "path", "score", "changeFrequency", "complexity" }],
  "entryPoints": ["..."],
  "explanation": "..."
}
```

## CLI Reference

```
lens scan [PATH]        Scan and display analysis in terminal
  --depth N             Max directory depth (default: 50)
  --ignore PATTERN      Extra patterns to ignore (repeatable)
  --no-git              Skip git history analysis

lens map [PATH]         Generate interactive HTML report
  -o, --output FILE     Output path (default: lens-report.html)
  --no-open             Don't auto-open in browser
  --no-git              Skip git history analysis

lens explain [PATH]     Plain English project explanation
  --no-git              Skip git history analysis

lens stats [PATH]       Quick statistics only
  --no-git              Skip git history analysis

lens export [PATH]      Export analysis
  -f, --format FMT      json | md | html
  -o, --output FILE     Output file path
  --no-git              Skip git history analysis

lens diff BRANCH1 BRANCH2 [PATH]   Compare two branches

lens --version          Show version
lens --help             Show help
```

## Comparison

| Feature | Lens | Reading Code Manually | GitHub UI |
|---------|------|-----------------------|-----------|
| Architecture detection | Automatic | Manual reading | None |
| Dependency graph | Interactive | Mental model | None |
| Multi-language | 6+ languages | - | Basic stats |
| Hotspot detection | Git-aware scoring | None | Commit history |
| Offline | Yes | Yes | No |
| Entry point finding | Automatic | Search manually | None |
| Export formats | 4 formats | None | None |
| Speed | Seconds | Hours | Minutes |

## Development

```bash
git clone https://github.com/patelpa1639/lens.git
cd lens
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install pytest pytest-cov ruff
pytest --cov=lens
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=lens --cov-report=term-missing

# Lint
ruff check lens/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests first (TDD)
4. Implement the feature
5. Run `pytest --cov=lens` and ensure 80%+ coverage
6. Run `ruff check` for linting
7. Commit and push
8. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with Python, Rich, and Click. No AI required.
