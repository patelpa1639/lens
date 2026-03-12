"""Content-hash caching for scan results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "lens"


def _file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    hasher = hashlib.sha256()
    try:
        hasher.update(file_path.read_bytes())
    except OSError:
        return ""
    return hasher.hexdigest()


def _cache_path(content_hash: str) -> Path:
    """Get cache file path for a given content hash."""
    return CACHE_DIR / f"{content_hash}.json"


def get_cached(file_path: Path) -> dict | None:
    """Retrieve cached analysis for a file if content hasn't changed."""
    content_hash = _file_hash(file_path)
    if not content_hash:
        return None
    cache_file = _cache_path(content_hash)
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def set_cached(file_path: Path, data: dict) -> None:
    """Cache analysis result keyed by file content hash."""
    content_hash = _file_hash(file_path)
    if not content_hash:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(content_hash)
    try:
        cache_file.write_text(json.dumps(data, default=str))
    except OSError:
        pass


def clear_cache() -> int:
    """Clear all cached data. Returns number of files removed."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)
        count += 1
    return count
