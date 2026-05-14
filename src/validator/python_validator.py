from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

FORBIDDEN_PYTHON_IMPORTS = [
    "os", "subprocess", "shutil", "sys",
    "socket", "http.server", "requests", "urllib",
    "importlib", "inspect", "ctypes", "multiprocessing",
    "threading", "asyncio",
]

FORBIDDEN_PYTHON_FUNCTIONS = [
    "eval", "exec", "compile", "__import__",
    "open", "globals", "locals", "getattr", "setattr",
]


@dataclass
class PythonValidationResult:
    is_valid: bool
    is_safe: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ast_parsed: bool = False
    imports: list[str] = field(default_factory=list)


class PythonValidator:
    def validate(self, code: str) -> PythonValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not code or not code.strip():
            errors.append("Empty code")
            return PythonValidationResult(is_valid=False, is_safe=True, errors=errors, warnings=warnings)

        try:
            tree = ast.parse(code)
            ast_parsed = True
            imports = self._extract_imports(tree)
        except SyntaxError as e:
            errors.append(f"Python syntax error: {e}")
            return PythonValidationResult(is_valid=False, is_safe=True, errors=errors, warnings=warnings)

        is_safe = self._check_safety(code, tree, errors, warnings)

        return PythonValidationResult(
            is_valid=len(errors) == 0,
            is_safe=is_safe,
            errors=errors,
            warnings=warnings,
            ast_parsed=ast_parsed,
            imports=imports,
        )

    def _check_safety(
        self,
        code: str,
        tree: ast.AST,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        is_safe = True

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in FORBIDDEN_PYTHON_IMPORTS:
                        errors.append(f"Security: forbidden import '{alias.name}'")
                        is_safe = False
                    warnings.append(f"External import: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    if root in FORBIDDEN_PYTHON_IMPORTS:
                        errors.append(f"Security: forbidden import from '{node.module}'")
                        is_safe = False
                    warnings.append(f"External import from: {node.module}")

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_PYTHON_FUNCTIONS:
                    errors.append(f"Security: forbidden function call '{node.func.id}'")
                    is_safe = False

        return is_safe

    @staticmethod
    def _extract_imports(tree: ast.AST) -> list[str]:
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports
