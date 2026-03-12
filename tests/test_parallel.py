"""Tests for parallel scanning utilities."""

from pathlib import Path

from lens.utils.parallel import parallel_map


def test_parallel_map_basic(tmp_path):
    files = []
    for i in range(10):
        f = tmp_path / f"file_{i}.txt"
        f.write_text(f"content {i}")
        files.append(f)

    results = parallel_map(lambda p: p.read_text(), files)
    assert len(results) == 10
    assert "content 0" in results


def test_parallel_map_small_list(tmp_path):
    """Lists <= 3 items use sequential processing."""
    f1 = tmp_path / "a.txt"
    f1.write_text("a")
    results = parallel_map(lambda p: p.read_text(), [f1])
    assert results == ["a"]


def test_parallel_map_empty():
    results = parallel_map(lambda p: p.name, [])
    assert results == []


def test_parallel_map_with_errors(tmp_path):
    files = [tmp_path / "nope.txt"]  # Doesn't exist

    def reader(p: Path) -> str:
        raise FileNotFoundError()

    results = parallel_map(reader, files * 5)
    assert results == []  # Errors are filtered out
