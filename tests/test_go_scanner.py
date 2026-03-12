"""Tests for Go scanner."""

from lens.scanner.go_scanner import scan_go_file


def test_scan_go_main(tmp_go_project):
    root = tmp_go_project
    module = scan_go_file(root / "main.go", root)
    assert module is not None
    assert module.entry_point is True
    func_names = [f.name for f in module.functions]
    assert "main" in func_names


def test_scan_go_imports(tmp_go_project):
    root = tmp_go_project
    module = scan_go_file(root / "main.go", root)
    assert module is not None
    import_modules = [i.module for i in module.imports]
    assert "fmt" in import_modules


def test_scan_go_handlers(tmp_go_project):
    root = tmp_go_project
    module = scan_go_file(root / "handlers" / "user.go", root)
    assert module is not None
    func_names = [f.name for f in module.functions]
    assert "GetUser" in func_names
    assert "CreateUser" in func_names
    # Exported functions
    assert "GetUser" in module.exports


def test_scan_go_nonexistent(tmp_path):
    result = scan_go_file(tmp_path / "nope.go", tmp_path)
    assert result is None
