"""Cyclomatic complexity analysis."""

from __future__ import annotations

from lens.models import ModuleInfo


def analyze_complexity(modules: list[ModuleInfo], threshold: int = 10) -> dict:
    """Analyze complexity across all modules.

    Returns a dict with:
        - complex_functions: list of functions exceeding threshold
        - avg_complexity: average complexity across all functions
        - max_complexity: highest complexity found
        - total_functions: total function count
    """
    all_functions: list[dict] = []
    complex_functions: list[dict] = []

    for module in modules:
        for func in module.functions:
            entry = {
                "name": func.name,
                "file": module.file_path,
                "line": func.line_number,
                "complexity": func.complexity,
            }
            all_functions.append(entry)
            if func.complexity > threshold:
                complex_functions.append(entry)

        for cls in module.classes:
            for method in cls.methods:
                entry = {
                    "name": f"{cls.name}.{method.name}",
                    "file": module.file_path,
                    "line": method.line_number,
                    "complexity": method.complexity,
                }
                all_functions.append(entry)
                if method.complexity > threshold:
                    complex_functions.append(entry)

    complexities = [f["complexity"] for f in all_functions]
    avg = sum(complexities) / len(complexities) if complexities else 0
    max_c = max(complexities) if complexities else 0

    complex_functions.sort(key=lambda x: x["complexity"], reverse=True)

    return {
        "complex_functions": complex_functions[:20],
        "avg_complexity": round(avg, 1),
        "max_complexity": max_c,
        "total_functions": len(all_functions),
    }
