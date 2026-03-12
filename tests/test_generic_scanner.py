"""Tests for generic/fallback scanner."""


from lens.scanner.generic_scanner import scan_generic_file


def test_scan_c_file(tmp_path):
    f = tmp_path / "main.c"
    f.write_text('#include <stdio.h>\n#include "mylib.h"\n\nint main() {\n    return 0;\n}\n')
    module = scan_generic_file(f, tmp_path)
    assert module is not None
    assert len(module.imports) >= 1
    import_modules = [i.module for i in module.imports]
    assert "stdio.h" in import_modules


def test_scan_generic_functions(tmp_path):
    f = tmp_path / "script.rb"
    f.write_text("def hello(name)\n  puts name\nend\n\ndef goodbye\n  puts 'bye'\nend\n")
    module = scan_generic_file(f, tmp_path)
    assert module is not None
    func_names = [fn.name for fn in module.functions]
    assert "hello" in func_names
    assert len(func_names) >= 1


def test_scan_generic_nonexistent(tmp_path):
    result = scan_generic_file(tmp_path / "nope.c", tmp_path)
    assert result is None
