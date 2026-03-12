"""Tests for JavaScript/TypeScript scanner."""

from lens.scanner.js_scanner import scan_js_file


def test_scan_js_imports(tmp_js_project):
    root = tmp_js_project
    module = scan_js_file(root / "src" / "index.ts", root)
    assert module is not None
    assert len(module.imports) >= 2
    modules = [i.module for i in module.imports]
    assert "./App" in modules or any("App" in m for m in modules)


def test_scan_js_functions(tmp_js_project):
    root = tmp_js_project
    module = scan_js_file(root / "src" / "App.tsx", root)
    assert module is not None
    func_names = [f.name for f in module.functions]
    assert "App" in func_names


def test_scan_js_arrow_functions(tmp_js_project):
    root = tmp_js_project
    module = scan_js_file(root / "src" / "components" / "Header.tsx", root)
    assert module is not None
    func_names = [f.name for f in module.functions]
    assert "Header" in func_names


def test_scan_js_entry_point(tmp_js_project):
    root = tmp_js_project
    module = scan_js_file(root / "src" / "index.ts", root)
    assert module is not None
    assert module.entry_point is True


def test_scan_js_exports(tmp_js_project):
    root = tmp_js_project
    module = scan_js_file(root / "src" / "App.tsx", root)
    assert module is not None
    assert "App" in module.exports


def test_scan_js_nonexistent(tmp_path):
    result = scan_js_file(tmp_path / "nope.js", tmp_path)
    assert result is None
