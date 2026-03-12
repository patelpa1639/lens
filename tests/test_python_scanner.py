"""Tests for Python scanner."""


from lens.scanner.python_scanner import scan_python_file


def test_scan_python_imports(tmp_python_project):
    root = tmp_python_project
    module = scan_python_file(root / "myapp" / "cli.py", root)
    assert module is not None
    assert len(module.imports) >= 2
    import_modules = [i.module for i in module.imports]
    assert "click" in import_modules


def test_scan_python_classes(tmp_python_project):
    root = tmp_python_project
    module = scan_python_file(root / "myapp" / "models.py", root)
    assert module is not None
    assert len(module.classes) == 1
    assert module.classes[0].name == "User"
    assert len(module.classes[0].methods) == 1


def test_scan_python_functions(tmp_python_project):
    root = tmp_python_project
    module = scan_python_file(root / "myapp" / "utils.py", root)
    assert module is not None
    assert len(module.functions) == 2
    func_names = [f.name for f in module.functions]
    assert "load_config" in func_names
    assert "get_env" in func_names


def test_scan_python_entry_point(tmp_python_project):
    root = tmp_python_project
    module = scan_python_file(root / "myapp" / "cli.py", root)
    assert module is not None
    assert module.entry_point is True


def test_scan_python_complexity(tmp_python_project):
    root = tmp_python_project
    module = scan_python_file(root / "myapp" / "utils.py", root)
    assert module is not None
    for func in module.functions:
        assert func.complexity >= 1


def test_scan_syntax_error(tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def foo(\n")  # Syntax error
    module = scan_python_file(bad_file, tmp_path)
    assert module is not None  # Should not crash
    assert module.file_path == "bad.py"


def test_scan_nonexistent_file(tmp_path):
    result = scan_python_file(tmp_path / "nope.py", tmp_path)
    assert result is None
