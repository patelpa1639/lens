"""Git history scanner using GitPython."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from lens.models import GitFileHistory


def scan_git_history(root: Path, days: int = 90) -> list[GitFileHistory]:
    """Scan git history for file change frequency and contributors."""
    try:
        from git import InvalidGitRepositoryError, Repo
    except ImportError:
        return []

    try:
        repo = Repo(root, search_parent_directories=True)
    except (InvalidGitRepositoryError, Exception):
        return []

    if repo.bare:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    file_data: dict[str, GitFileHistory] = {}

    try:
        for commit in repo.iter_commits(max_count=500):
            commit_date = commit.committed_datetime
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)

            if commit_date < cutoff:
                break

            author = str(commit.author)

            for path in commit.stats.files:
                if path not in file_data:
                    file_data[path] = GitFileHistory(file_path=path)

                entry = file_data[path]
                entry.commit_count += 1
                if author not in entry.contributors:
                    entry.contributors.append(author)
                if not entry.last_modified or str(commit_date) > entry.last_modified:
                    entry.last_modified = str(commit_date)
    except Exception:
        pass

    # Calculate churn scores (normalized 0-100)
    if file_data:
        max_commits = max(e.commit_count for e in file_data.values()) or 1
        for entry in file_data.values():
            entry.churn_score = round((entry.commit_count / max_commits) * 100, 1)

    return list(file_data.values())


def get_contributors(root: Path) -> list[tuple[str, int]]:
    """Get list of contributors and their commit counts."""
    try:
        from git import Repo

        repo = Repo(root, search_parent_directories=True)
    except Exception:
        return []

    contributors: dict[str, int] = {}
    try:
        for commit in repo.iter_commits(max_count=1000):
            author = str(commit.author)
            contributors[author] = contributors.get(author, 0) + 1
    except Exception:
        pass

    return sorted(contributors.items(), key=lambda x: x[1], reverse=True)
