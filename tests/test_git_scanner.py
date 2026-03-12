"""Tests for git scanner."""


from lens.scanner.git_scanner import get_contributors, scan_git_history


def test_scan_git_history_no_repo(tmp_path):
    """Non-git directory should return empty list."""
    result = scan_git_history(tmp_path)
    assert result == []


def test_scan_git_history_with_repo(tmp_path):
    """Git repo with commits should return history."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    (tmp_path / "test.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

    result = scan_git_history(tmp_path)
    assert len(result) >= 1
    assert result[0].commit_count >= 1


def test_get_contributors_no_repo(tmp_path):
    result = get_contributors(tmp_path)
    assert result == []


def test_get_contributors_with_repo(tmp_path):
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    (tmp_path / "test.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

    result = get_contributors(tmp_path)
    assert len(result) >= 1
    assert result[0][0] == "Test"
