"""Comprehensive tests for the lens search feature."""

from __future__ import annotations

from pathlib import Path

import pytest

from lens.search.formatter import format_results, get_context_lines, group_by_file
from lens.search.indexer import build_index
from lens.search.query_parser import parse_query
from lens.search.ranker import SearchResult, rank_results
from lens.search.synonym_map import expand_synonyms, get_all_synonyms

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_search_project(tmp_path: Path) -> Path:
    """Create a small multi-file project for search tests."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "app.py").write_text(
        "# Main application entry point\n"
        "from src.models import User\n"
        "from src.utils import load_config\n"
        "\n"
        "def main():\n"
        '    config = load_config("settings.json")\n'
        "    print(config)\n"
    )

    (src / "models.py").write_text(
        "# Database models\n"
        "class User:\n"
        "    def __init__(self, name: str, email: str):\n"
        "        self.name = name\n"
        "        self.email = email\n"
        "\n"
        "    def greet(self):\n"
        "        return f'Hello {self.name}'\n"
        "\n"
        "class Admin(User):\n"
        "    role = 'admin'\n"
    )

    (src / "utils.py").write_text(
        "import json\n"
        "import os\n"
        "\n"
        "def load_config(path):\n"
        '    """Load JSON configuration from disk."""\n'
        "    with open(path) as f:\n"
        "        return json.load(f)\n"
        "\n"
        "def get_env(key, default=None):\n"
        "    return os.environ.get(key, default)\n"
    )

    (src / "auth.py").write_text(
        "# Authentication helpers\n"
        "import hashlib\n"
        "\n"
        "def hash_password(password: str) -> str:\n"
        "    return hashlib.sha256(password.encode()).hexdigest()\n"
        "\n"
        "def verify_token(token: str) -> bool:\n"
        "    return len(token) > 0\n"
    )

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_models.py").write_text(
        "from src.models import User\n"
        "\n"
        "def test_user_greet():\n"
        '    u = User("Alice", "alice@example.com")\n'
        '    assert u.greet() == "Hello Alice"\n'
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Query parser tests
# ---------------------------------------------------------------------------


class TestQueryParser:
    def test_simple_keywords(self) -> None:
        q = parse_query("user model")
        assert "user" in q.keywords
        assert "model" in q.keywords

    def test_stop_word_removal(self) -> None:
        q = parse_query("the user is a model")
        assert "the" not in q.keywords
        assert "is" not in q.keywords
        assert "a" not in q.keywords
        assert "user" in q.keywords
        assert "model" in q.keywords

    def test_quoted_phrase(self) -> None:
        q = parse_query('"load config" utils')
        assert "load config" in q.exact_phrases
        assert "utils" in q.keywords

    def test_lang_operator(self) -> None:
        q = parse_query("user lang:python")
        assert q.language_filter == "python"
        assert "user" in q.keywords

    def test_type_function_operator(self) -> None:
        q = parse_query("load type:function")
        assert q.type_filter == "function"
        assert "load" in q.keywords

    def test_type_class_operator(self) -> None:
        q = parse_query("User type:class")
        assert q.type_filter == "class"

    def test_in_operator(self) -> None:
        q = parse_query("greet in:models")
        assert q.filename_filter == "models"
        assert "greet" in q.keywords

    def test_multiple_operators(self) -> None:
        q = parse_query("user lang:python type:class")
        assert q.language_filter == "python"
        assert q.type_filter == "class"
        assert "user" in q.keywords

    def test_empty_query(self) -> None:
        q = parse_query("")
        assert q.keywords == []
        assert q.exact_phrases == []

    def test_only_stop_words(self) -> None:
        q = parse_query("the a an is are")
        assert q.keywords == []


# ---------------------------------------------------------------------------
# Synonym map tests
# ---------------------------------------------------------------------------


class TestSynonymMap:
    def test_known_synonym(self) -> None:
        syns = expand_synonyms("auth")
        assert "login" in syns
        assert "password" in syns
        assert "token" in syns

    def test_database_synonyms(self) -> None:
        syns = expand_synonyms("database")
        assert "db" in syns
        assert "sql" in syns
        assert "model" in syns

    def test_unknown_keyword(self) -> None:
        assert expand_synonyms("xyzzy") == []

    def test_case_insensitive(self) -> None:
        assert expand_synonyms("AUTH") == expand_synonyms("auth")

    def test_get_all_synonyms(self) -> None:
        result = get_all_synonyms(["auth", "xyzzy", "config"])
        assert "auth" in result
        assert "config" in result
        assert "xyzzy" not in result

    def test_error_synonyms(self) -> None:
        syns = expand_synonyms("error")
        assert "exception" in syns
        assert "raise" in syns

    def test_test_synonyms(self) -> None:
        syns = expand_synonyms("test")
        assert "mock" in syns
        assert "fixture" in syns


# ---------------------------------------------------------------------------
# Indexer tests
# ---------------------------------------------------------------------------


class TestIndexer:
    def test_build_index_not_empty(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        assert len(idx.entries) > 0

    def test_function_indexed(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        entries = idx.lookup("load_config")
        assert any(e.kind == "function" for e in entries)

    def test_class_indexed(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        entries = idx.lookup("User")
        assert any(e.kind == "class" for e in entries)

    def test_content_indexed(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        entries = idx.lookup("json")
        assert len(entries) > 0

    def test_case_insensitive_lookup(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        assert idx.lookup("user") == idx.lookup("USER")

    def test_file_languages_populated(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        assert len(idx.file_languages) > 0
        langs = set(idx.file_languages.values())
        assert "Python" in langs

    def test_filename_indexed(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        entries = idx.lookup("auth")
        # Should have a "filename" kind entry from auth.py
        assert any(e.kind == "filename" for e in entries)


# ---------------------------------------------------------------------------
# Ranker tests
# ---------------------------------------------------------------------------


class TestRanker:
    def test_basic_ranking(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("User")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0
        # Scores should be descending
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_function_type_filter(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("load type:function")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert all(r.kind == "function" for r in results)

    def test_class_type_filter(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("User type:class")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert all(r.kind == "class" for r in results)

    def test_filename_filter(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("user in:models")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert all("models" in r.file_path.name.lower() for r in results)

    def test_test_file_penalty(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("User")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        # Find results in test files vs non-test files with similar content
        test_scores = [r.score for r in results if "test_" in r.file_path.name]
        non_test_scores = [r.score for r in results if "test_" not in r.file_path.name]
        if test_scores and non_test_scores:
            # The best non-test score should be >= best test score
            assert max(non_test_scores) >= max(test_scores)

    def test_test_query_no_penalty(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("test user")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        # Should still return test file results
        assert any("test_" in r.file_path.name for r in results)

    def test_top_n_limit(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("user")
        results = rank_results(idx, q, tmp_search_project, top_n=3, use_git=False)
        assert len(results) <= 3

    def test_exact_phrase_boost(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query('"load config"')
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0
        # The best result should be from utils.py where the phrase exists
        top = results[0]
        assert "utils" in top.file_path.name.lower() or "app" in top.file_path.name.lower()

    def test_language_filter(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("user lang:python")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        # All results should be Python
        for r in results:
            assert idx.file_languages.get(r.file_path, "").lower() == "python"

    def test_synonym_expansion(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        # Searching for "auth" should also find password/token via synonyms
        q = parse_query("auth")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Formatter tests
# ---------------------------------------------------------------------------


class TestFormatter:
    def test_group_by_file(self) -> None:
        results = [
            SearchResult(file_path=Path("/a.py"), line_number=1, context="x", score=5.0),
            SearchResult(file_path=Path("/a.py"), line_number=5, context="y", score=3.0),
            SearchResult(file_path=Path("/b.py"), line_number=2, context="z", score=4.0),
        ]
        groups = group_by_file(results)
        assert len(groups) == 2
        assert groups[0].file_path == Path("/a.py")
        assert len(groups[0].hits) == 2
        assert groups[1].file_path == Path("/b.py")

    def test_get_context_lines(self, tmp_search_project: Path) -> None:
        fpath = tmp_search_project / "src" / "models.py"
        ctx = get_context_lines(fpath, 2, context=1)
        # Should have lines around line 2
        line_nums = [ln for ln, _ in ctx]
        assert 2 in line_nums
        assert 1 in line_nums
        assert 3 in line_nums

    def test_format_results_no_crash(self, tmp_search_project: Path) -> None:
        """Ensure format_results runs without errors."""
        from io import StringIO

        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, force_terminal=True)

        idx = build_index(tmp_search_project)
        q = parse_query("User")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        # Should not raise
        format_results(results, q.keywords, console=console)
        output = buf.getvalue()
        assert "match" in output.lower() or "no results" in output.lower()

    def test_format_empty_results(self) -> None:
        from io import StringIO

        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, force_terminal=True)
        format_results([], ["test"], console=console)
        assert "no results" in buf.getvalue().lower()


# ---------------------------------------------------------------------------
# End-to-end search test
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_search_finds_function(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("load_config")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0
        # Top result should be in utils.py
        top = results[0]
        assert "utils" in top.file_path.name

    def test_search_finds_class(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("Admin type:class")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0
        assert any(r.kind == "class" for r in results)

    def test_search_with_filename_filter(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("password in:auth")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0
        assert all("auth" in r.file_path.name for r in results)

    def test_search_quoted_phrase(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query('"hash_password"')
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert len(results) > 0

    def test_search_no_results(self, tmp_search_project: Path) -> None:
        idx = build_index(tmp_search_project)
        q = parse_query("zznonexistentzz")
        results = rank_results(idx, q, tmp_search_project, use_git=False)
        assert results == []
