"""Tests for content-hash caching."""


from lens.utils.cache import clear_cache, get_cached, set_cached


def test_cache_roundtrip(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    data = {"imports": ["os"], "functions": ["main"]}
    set_cached(test_file, data)
    result = get_cached(test_file)
    assert result is not None
    assert result["imports"] == ["os"]


def test_cache_miss(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("unique_content_that_was_never_cached_12345")
    result = get_cached(test_file)
    assert result is None


def test_cache_invalidation(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("v1")
    set_cached(test_file, {"version": 1})

    # Change file content
    test_file.write_text("v2")
    result = get_cached(test_file)
    assert result is None  # Cache should miss


def test_cache_nonexistent_file(tmp_path):
    result = get_cached(tmp_path / "nope.py")
    assert result is None


def test_clear_cache():
    count = clear_cache()
    assert isinstance(count, int)


def test_set_cached_nonexistent(tmp_path):
    # Should not crash
    set_cached(tmp_path / "nope.py", {"data": True})
