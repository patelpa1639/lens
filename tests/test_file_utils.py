"""Tests for file utilities."""

from pathlib import Path

from lens.models import Language
from lens.utils.file_utils import (
    collect_files,
    count_lines,
    detect_language,
    is_binary,
    parse_gitignore,
    read_file_safe,
    should_ignore,
)


def test_detect_language_python():
    assert detect_language(Path("test.py")) == Language.PYTHON


def test_detect_language_js():
    assert detect_language(Path("app.js")) == Language.JAVASCRIPT


def test_detect_language_ts():
    assert detect_language(Path("app.tsx")) == Language.TYPESCRIPT


def test_detect_language_go():
    assert detect_language(Path("main.go")) == Language.GO


def test_detect_language_rust():
    assert detect_language(Path("main.rs")) == Language.RUST


def test_detect_language_dockerfile():
    assert detect_language(Path("Dockerfile")) == Language.DOCKERFILE


def test_detect_language_unknown():
    assert detect_language(Path("file.xyz")) == Language.OTHER


def test_count_lines_basic():
    content = "line1\nline2\n\n# comment\nline3"
    total, code, blank, comment = count_lines(content)
    assert total == 5
    assert blank == 1
    assert comment == 1
    assert code == 3


def test_count_lines_empty():
    total, code, blank, comment = count_lines("")
    assert total == 0


def test_is_binary_text(tmp_path):
    f = tmp_path / "text.py"
    f.write_text("print('hello')")
    assert is_binary(f) is False


def test_is_binary_with_null(tmp_path):
    f = tmp_path / "bin.dat"
    f.write_bytes(b"hello\x00world")
    assert is_binary(f) is True


def test_is_binary_png(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    assert is_binary(f) is True


def test_read_file_safe(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("hello world")
    content = read_file_safe(f)
    assert content == "hello world"


def test_read_file_safe_binary(tmp_path):
    f = tmp_path / "bin.dat"
    f.write_bytes(b"\x89PNG" + b"\x00" * 100)
    assert read_file_safe(f) is None


def test_read_file_safe_nonexistent(tmp_path):
    assert read_file_safe(tmp_path / "nope.py") is None


def test_parse_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pyc\n# comment\nnode_modules/\n")
    patterns = parse_gitignore(tmp_path)
    assert "*.pyc" in patterns
    assert "node_modules/" in patterns
    assert len(patterns) == 2  # comment excluded


def test_parse_gitignore_missing(tmp_path):
    patterns = parse_gitignore(tmp_path)
    assert patterns == []


def test_should_ignore_pycache(tmp_path):
    p = tmp_path / "__pycache__" / "test.pyc"
    assert should_ignore(p, tmp_path, []) is True


def test_should_ignore_node_modules(tmp_path):
    p = tmp_path / "node_modules" / "pkg" / "index.js"
    assert should_ignore(p, tmp_path, []) is True


def test_collect_files(tmp_python_project):
    files = collect_files(tmp_python_project)
    assert len(files) > 0
    paths = [str(f) for f in files]
    assert any("cli.py" in p for p in paths)


def test_collect_files_empty(tmp_path):
    files = collect_files(tmp_path)
    assert files == []
