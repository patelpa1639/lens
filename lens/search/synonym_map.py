"""Synonym mapping for expanding search queries with related terms."""

from __future__ import annotations

# Each key maps to a list of related terms that often co-occur in code.
SYNONYM_MAP: dict[str, list[str]] = {
    "http": ["request", "api", "endpoint", "route", "handler"],
    "request": ["http", "api", "endpoint", "route", "handler"],
    "api": ["http", "request", "endpoint", "route", "handler"],
    "endpoint": ["http", "request", "api", "route", "handler"],
    "route": ["http", "request", "api", "endpoint", "handler"],
    "handler": ["http", "request", "api", "endpoint", "route"],
    "database": ["db", "sql", "query", "model", "schema", "migration"],
    "db": ["database", "sql", "query", "model", "schema", "migration"],
    "sql": ["database", "db", "query", "model", "schema", "migration"],
    "schema": ["database", "db", "sql", "query", "model", "migration"],
    "migration": ["database", "db", "sql", "query", "model", "schema"],
    "auth": ["login", "password", "session", "token", "jwt", "oauth"],
    "login": ["auth", "password", "session", "token", "jwt", "oauth"],
    "password": ["auth", "login", "session", "token", "jwt", "oauth"],
    "token": ["auth", "login", "password", "session", "jwt", "oauth"],
    "jwt": ["auth", "login", "password", "session", "token", "oauth"],
    "oauth": ["auth", "login", "password", "session", "token", "jwt"],
    "session": ["auth", "login", "password", "token", "jwt", "oauth"],
    "test": ["spec", "assert", "mock", "fixture"],
    "spec": ["test", "assert", "mock", "fixture"],
    "assert": ["test", "spec", "mock", "fixture"],
    "mock": ["test", "spec", "assert", "fixture"],
    "fixture": ["test", "spec", "assert", "mock"],
    "config": ["settings", "env", "environment", "options"],
    "settings": ["config", "env", "environment", "options"],
    "env": ["config", "settings", "environment", "options"],
    "environment": ["config", "settings", "env", "options"],
    "options": ["config", "settings", "env", "environment"],
    "error": ["exception", "raise", "catch", "try", "handle"],
    "exception": ["error", "raise", "catch", "try", "handle"],
    "raise": ["error", "exception", "catch", "try", "handle"],
    "catch": ["error", "exception", "raise", "try", "handle"],
    "handle": ["error", "exception", "raise", "catch", "try"],
}


def expand_synonyms(keyword: str) -> list[str]:
    """Return synonym expansions for a keyword (lowercase).

    Returns an empty list if no synonyms are known.
    """
    return SYNONYM_MAP.get(keyword.lower(), [])


def get_all_synonyms(keywords: list[str]) -> dict[str, list[str]]:
    """Return a mapping of each keyword to its synonyms.

    Only keywords that have known synonyms are included.
    """
    result: dict[str, list[str]] = {}
    for kw in keywords:
        syns = expand_synonyms(kw)
        if syns:
            result[kw.lower()] = syns
    return result
