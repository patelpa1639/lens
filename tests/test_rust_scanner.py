"""Tests for Rust scanner."""

from lens.scanner.rust_scanner import scan_rust_file


def test_scan_rust_main(tmp_rust_project):
    root = tmp_rust_project
    module = scan_rust_file(root / "src" / "main.rs", root)
    assert module is not None
    assert module.entry_point is True
    func_names = [f.name for f in module.functions]
    assert "main" in func_names


def test_scan_rust_imports(tmp_rust_project):
    root = tmp_rust_project
    module = scan_rust_file(root / "src" / "main.rs", root)
    assert module is not None
    import_modules = [i.module for i in module.imports]
    assert any("io" in m for m in import_modules)
    assert any("serde" in m for m in import_modules)


def test_scan_rust_lib(tmp_rust_project):
    root = tmp_rust_project
    module = scan_rust_file(root / "src" / "lib.rs", root)
    assert module is not None
    assert module.entry_point is True  # lib.rs is library root
    func_names = [f.name for f in module.functions]
    assert "add" in func_names


def test_scan_rust_exports(tmp_rust_project):
    root = tmp_rust_project
    module = scan_rust_file(root / "src" / "lib.rs", root)
    assert module is not None
    assert "add" in module.exports


def test_scan_rust_nonexistent(tmp_path):
    result = scan_rust_file(tmp_path / "nope.rs", tmp_path)
    assert result is None
