"""Rank and sort search results by relevance."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from lens.search.indexer import IndexEntry, SearchIndex
from lens.search.query_parser import ParsedQuery
from lens.search.synonym_map import expand_synonyms


@dataclass
class SearchResult:
    """A single ranked search result."""

    file_path: Path
    line_number: int
    context: str
    score: float
    kind: str = "content"


def _git_recent_files(root: Path, limit: int = 200) -> set[str]:
    """Return the set of recently-modified file paths from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=M", "--name-only", "--pretty=format:", f"-{limit}"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
        )
        if result.returncode == 0:
            return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return set()


def rank_results(
    index: SearchIndex,
    query: ParsedQuery,
    root: Path,
    top_n: int = 30,
    use_git: bool = True,
) -> list[SearchResult]:
    """Score every matching index entry and return the top *top_n* results.

    Scoring rules:
    - exact match on keyword:    10x
    - function/class name match: 5x
    - filename match:            3x
    - generic content match:     1x
    - recent git file boost:     1.2x
    - test file penalty:         0.8x (unless query contains "test")
    """
    # Collect git-recent files for boosting
    recent_files: set[str] = set()
    if use_git:
        recent_files = _git_recent_files(root)

    query_has_test = "test" in query.keywords or any("test" in p.lower() for p in query.exact_phrases)

    # Gather all tokens to look up (keywords + synonym expansions)
    primary_keywords = set(query.keywords)
    synonym_keywords: set[str] = set()
    for kw in query.keywords:
        for syn in expand_synonyms(kw):
            if syn not in primary_keywords:
                synonym_keywords.add(syn)

    # Deduplicate results per (file, line) and accumulate scores
    seen: dict[tuple[Path, int], SearchResult] = {}

    def _score_entries(entries: list[IndexEntry], is_primary: bool) -> None:
        for entry in entries:
            # Apply filters
            if query.language_filter:
                lang = index.file_languages.get(entry.file_path, "").lower()
                if query.language_filter not in lang:
                    continue
            if query.type_filter:
                if query.type_filter == "function" and entry.kind != "function":
                    continue
                if query.type_filter == "class" and entry.kind != "class":
                    continue
            if query.filename_filter:
                if query.filename_filter not in entry.file_path.name.lower():
                    continue

            # Base score by kind
            if entry.kind == "function" or entry.kind == "class":
                base = 5.0
            elif entry.kind == "filename":
                base = 3.0
            else:
                base = 1.0

            # Exact-phrase bonus
            line_lower = entry.context.lower()
            for phrase in query.exact_phrases:
                if phrase.lower() in line_lower:
                    base *= 10.0

            # Primary keyword vs synonym
            if not is_primary:
                base *= 0.3  # synonyms are weaker signals

            # Git recency boost
            try:
                rel = str(entry.file_path.relative_to(root))
            except ValueError:
                rel = str(entry.file_path)
            if rel in recent_files:
                base *= 1.2

            # Test file penalty
            fname = entry.file_path.name.lower()
            if not query_has_test and ("test_" in fname or "_test." in fname or fname.startswith("test")):
                base *= 0.8

            key = (entry.file_path, entry.line_number)
            if key in seen:
                seen[key].score += base
            else:
                seen[key] = SearchResult(
                    file_path=entry.file_path,
                    line_number=entry.line_number,
                    context=entry.context,
                    score=base,
                    kind=entry.kind,
                )

    # Score primary keywords
    for kw in primary_keywords:
        _score_entries(index.lookup(kw), is_primary=True)

    # Score synonym keywords
    for kw in synonym_keywords:
        _score_entries(index.lookup(kw), is_primary=False)

    # Score exact phrases (look up each word in the phrase)
    for phrase in query.exact_phrases:
        words = phrase.lower().split()
        for word in words:
            _score_entries(index.lookup(word), is_primary=True)

    # Sort by score descending
    results = sorted(seen.values(), key=lambda r: r.score, reverse=True)
    return results[:top_n]
