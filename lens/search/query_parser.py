"""Parse natural language search queries into structured representations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "about",
        "that",
        "this",
        "it",
        "its",
        "and",
        "or",
        "but",
        "not",
        "no",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
        "too",
        "very",
        "just",
        "how",
        "what",
        "where",
        "when",
        "which",
        "who",
        "whom",
        "why",
        "me",
        "my",
        "i",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "they",
        "them",
        "their",
    }
)

# Operators recognised in queries: lang:python, type:function, type:class, in:filename
_OPERATOR_RE = re.compile(r"(lang|type|in):(\S+)", re.IGNORECASE)
# Quoted phrases
_QUOTED_RE = re.compile(r'"([^"]+)"')


@dataclass
class ParsedQuery:
    """Structured representation of a user search query."""

    keywords: list[str] = field(default_factory=list)
    exact_phrases: list[str] = field(default_factory=list)
    language_filter: str | None = None
    type_filter: str | None = None  # "function" or "class"
    filename_filter: str | None = None


def parse_query(raw_query: str) -> ParsedQuery:
    """Parse a raw query string into a structured *ParsedQuery*.

    Supports:
    - Quoted phrases (``"exact match"``) treated as exact-match tokens.
    - Operators: ``lang:python``, ``type:function``, ``type:class``, ``in:filename``.
    - Stop-word removal for remaining plain keywords.
    """
    result = ParsedQuery()
    remaining = raw_query

    # 1. Extract quoted phrases
    for match in _QUOTED_RE.finditer(remaining):
        result.exact_phrases.append(match.group(1))
    remaining = _QUOTED_RE.sub("", remaining)

    # 2. Extract operators
    for match in _OPERATOR_RE.finditer(remaining):
        op, value = match.group(1).lower(), match.group(2).lower()
        if op == "lang":
            result.language_filter = value
        elif op == "type":
            result.type_filter = value
        elif op == "in":
            result.filename_filter = value
    remaining = _OPERATOR_RE.sub("", remaining)

    # 3. Tokenize remaining text, remove stop words
    tokens = re.findall(r"[a-zA-Z0-9_]+", remaining)
    result.keywords = [t.lower() for t in tokens if t.lower() not in STOP_WORDS]

    return result
