"""Shared test fixtures — fake repos for testing."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_python_project(tmp_path: Path) -> Path:
    """Create a minimal Python project for testing."""
    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "myapp"\nversion = "1.0.0"\n'
        'dependencies = ["flask>=2.0", "sqlalchemy"]\n\n'
        "[project.scripts]\nmyapp = \"myapp.cli:main\"\n"
    )
    (tmp_path / "requirements.txt").write_text("flask>=2.0\nsqlalchemy>=1.4\npytest\n")

    # Source files
    src = tmp_path / "myapp"
    src.mkdir()
    (src / "__init__.py").write_text('"""My App."""\n__version__ = "1.0.0"\n')
    (src / "cli.py").write_text(
        "import click\nfrom myapp.models import User\n\n"
        "@click.command()\ndef main():\n    pass\n\n"
        'if __name__ == "__main__":\n    main()\n'
    )
    (src / "models.py").write_text(
        "from sqlalchemy import Column, Integer, String\n\n"
        "class User:\n"
        "    id = Column(Integer)\n"
        "    name = Column(String)\n\n"
        "    def greet(self):\n"
        "        return f'Hello {self.name}'\n"
    )
    (src / "utils.py").write_text(
        "import os\nimport json\n\n"
        "def load_config(path):\n"
        "    with open(path) as f:\n"
        "        return json.load(f)\n\n"
        "def get_env(key, default=None):\n"
        "    return os.environ.get(key, default)\n"
    )

    # Tests
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_models.py").write_text(
        "def test_user():\n    assert True\n"
    )

    return tmp_path


@pytest.fixture
def tmp_js_project(tmp_path: Path) -> Path:
    """Create a minimal JavaScript project for testing."""
    (tmp_path / "package.json").write_text(
        '{"name": "myapp", "version": "1.0.0", '
        '"dependencies": {"react": "^18.0", "next": "^14.0"}, '
        '"devDependencies": {"jest": "^29.0"}}'
    )
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

    src = tmp_path / "src"
    src.mkdir()
    (src / "index.ts").write_text(
        "import { App } from './App';\n"
        "import express from 'express';\n\n"
        "const app = express();\n"
        "app.listen(3000);\n"
    )
    (src / "App.tsx").write_text(
        "import React from 'react';\n"
        "import { Header } from './components/Header';\n\n"
        "export function App() {\n"
        "  return <div><Header /></div>;\n"
        "}\n"
    )

    components = src / "components"
    components.mkdir()
    (components / "Header.tsx").write_text(
        "import React from 'react';\n\n"
        "export const Header = () => {\n"
        "  return <header>Hello</header>;\n"
        "};\n"
    )

    return tmp_path


@pytest.fixture
def tmp_go_project(tmp_path: Path) -> Path:
    """Create a minimal Go project for testing."""
    (tmp_path / "go.mod").write_text(
        "module github.com/user/myapp\n\ngo 1.21\n\n"
        "require (\n\tgithub.com/gin-gonic/gin v1.9.0\n)\n"
    )

    (tmp_path / "main.go").write_text(
        'package main\n\nimport (\n\t"fmt"\n\t"github.com/gin-gonic/gin"\n)\n\n'
        "func main() {\n\tr := gin.Default()\n\tfmt.Println(r)\n}\n"
    )

    pkg = tmp_path / "handlers"
    pkg.mkdir()
    (pkg / "user.go").write_text(
        'package handlers\n\nimport "net/http"\n\n'
        "func GetUser(w http.ResponseWriter, r *http.Request) {\n"
        '\tw.Write([]byte("ok"))\n}\n\n'
        "func CreateUser(w http.ResponseWriter, r *http.Request) {\n"
        '\tw.Write([]byte("created"))\n}\n'
    )

    return tmp_path


@pytest.fixture
def tmp_rust_project(tmp_path: Path) -> Path:
    """Create a minimal Rust project for testing."""
    (tmp_path / "Cargo.toml").write_text(
        "[package]\nname = \"myapp\"\nversion = \"0.1.0\"\n\n"
        "[dependencies]\nserde = \"1.0\"\ntokio = { version = \"1\", features = [\"full\"] }\n"
    )

    src = tmp_path / "src"
    src.mkdir()
    (src / "main.rs").write_text(
        "use std::io;\nuse serde::Serialize;\n\n"
        "#[derive(Serialize)]\n"
        "pub struct Config {\n    pub name: String,\n}\n\n"
        "fn main() {\n    println!(\"Hello\");\n}\n"
    )
    (src / "lib.rs").write_text(
        "pub mod config;\n\n"
        "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n"
    )

    return tmp_path


@pytest.fixture
def tmp_monorepo(tmp_path: Path) -> Path:
    """Create a minimal monorepo for testing."""
    (tmp_path / "package.json").write_text('{"name": "monorepo", "private": true}')
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

    for name in ["web", "api", "shared"]:
        pkg = tmp_path / "packages" / name
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text(f'{{"name": "@mono/{name}", "version": "1.0.0"}}')
        (pkg / "index.ts").write_text(f'export const name = "{name}";\n')

    return tmp_path
