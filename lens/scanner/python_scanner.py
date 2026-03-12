"""Python source file scanner using the ast module."""

from __future__ import annotations

import ast
from pathlib import Path

from lens.models import ClassInfo, FunctionInfo, ImportInfo, Language, ModuleInfo
from lens.utils.file_utils import read_file_safe


def scan_python_file(file_path: Path, root: Path) -> ModuleInfo | None:
    """Parse a Python file and extract structure information."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    relative = str(file_path.relative_to(root))
    module = ModuleInfo(file_path=relative, language=Language.PYTHON)

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return module  # Return minimal info on parse failure

    module.imports = _extract_imports(tree, relative)
    module.functions = _extract_functions(tree, relative)
    module.classes = _extract_classes(tree, relative)
    module.entry_point = _is_entry_point(tree, content)

    return module


def _extract_imports(tree: ast.Module, file_path: str) -> list[ImportInfo]:
    """Extract all import statements from an AST."""
    imports: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        is_relative=False,
                        source_file=file_path,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append(
                ImportInfo(
                    module=module_name,
                    names=names,
                    is_relative=node.level > 0,
                    source_file=file_path,
                )
            )
    return imports


def _extract_functions(tree: ast.Module, file_path: str) -> list[FunctionInfo]:
    """Extract top-level function definitions."""
    functions: list[FunctionInfo] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(
                FunctionInfo(
                    name=node.name,
                    file_path=file_path,
                    line_number=node.lineno,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    decorators=[_decorator_name(d) for d in node.decorator_list],
                    parameters=[arg.arg for arg in node.args.args if arg.arg != "self"],
                    complexity=_compute_complexity(node),
                )
            )
    return functions


def _extract_classes(tree: ast.Module, file_path: str) -> list[ClassInfo]:
    """Extract class definitions with their methods."""
    classes: list[ClassInfo] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods: list[FunctionInfo] = []
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(
                        FunctionInfo(
                            name=item.name,
                            file_path=file_path,
                            line_number=item.lineno,
                            is_method=True,
                            is_async=isinstance(item, ast.AsyncFunctionDef),
                            decorators=[_decorator_name(d) for d in item.decorator_list],
                            parameters=[
                                arg.arg for arg in item.args.args if arg.arg != "self"
                            ],
                            complexity=_compute_complexity(item),
                        )
                    )
            classes.append(
                ClassInfo(
                    name=node.name,
                    file_path=file_path,
                    line_number=node.lineno,
                    bases=[_node_name(b) for b in node.bases],
                    methods=methods,
                    decorators=[_decorator_name(d) for d in node.decorator_list],
                )
            )
    return classes


def _decorator_name(node: ast.expr) -> str:
    """Get the name of a decorator."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_node_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return "unknown"


def _node_name(node: ast.expr) -> str:
    """Get a string representation of an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_node_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Constant):
        return str(node.value)
    return "unknown"


def _compute_complexity(node: ast.AST) -> int:
    """Compute cyclomatic complexity of a function/method."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.Assert, ast.comprehension)):
            complexity += 1
    return complexity


def _is_entry_point(tree: ast.Module, content: str) -> bool:
    """Check if this file is an entry point."""
    # Check for if __name__ == "__main__"
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            try:
                test = node.test
                if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name):
                    if test.left.id == "__name__":
                        return True
            except AttributeError:
                pass
    # Check for click commands or main function at top level
    if "click.command" in content or "click.group" in content or "@app.route" in content:
        return True
    return False
