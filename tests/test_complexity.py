"""Tests for complexity analysis."""

from lens.analyzer.complexity import analyze_complexity
from lens.models import ClassInfo, FunctionInfo, Language, ModuleInfo


def test_analyze_complexity_basic():
    modules = [
        ModuleInfo(
            file_path="app.py",
            language=Language.PYTHON,
            functions=[
                FunctionInfo(name="simple", file_path="app.py", line_number=1, complexity=1),
                FunctionInfo(name="complex", file_path="app.py", line_number=10, complexity=15),
            ],
        ),
    ]
    result = analyze_complexity(modules, threshold=10)
    assert result["total_functions"] == 2
    assert result["max_complexity"] == 15
    assert len(result["complex_functions"]) == 1
    assert result["complex_functions"][0]["name"] == "complex"


def test_analyze_complexity_with_methods():
    modules = [
        ModuleInfo(
            file_path="models.py",
            language=Language.PYTHON,
            classes=[
                ClassInfo(
                    name="User",
                    file_path="models.py",
                    line_number=1,
                    methods=[
                        FunctionInfo(name="save", file_path="models.py", line_number=5, complexity=12),
                    ],
                ),
            ],
        ),
    ]
    result = analyze_complexity(modules, threshold=10)
    assert result["total_functions"] == 1
    assert result["complex_functions"][0]["name"] == "User.save"


def test_analyze_complexity_empty():
    result = analyze_complexity([], threshold=10)
    assert result["total_functions"] == 0
    assert result["avg_complexity"] == 0
    assert result["max_complexity"] == 0
