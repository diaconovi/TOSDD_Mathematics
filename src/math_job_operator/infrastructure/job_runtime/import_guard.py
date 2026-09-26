"""Static (AST-based) rejection of job scripts that import core service dependencies."""

import ast

DISALLOWED_TOP_LEVEL_MODULES = frozenset({"fastapi", "uvicorn", "pydantic"})


class DisallowedImportError(Exception):
    """Raised when a job script imports one of the service's own framework dependencies."""

    def __init__(self, module_name: str) -> None:
        super().__init__(
            f"job scripts may not import {module_name!r} "
            "(a core service dependency); see FR-015"
        )
        self.module_name = module_name


def check_source_imports(source: str) -> None:
    """Raise `DisallowedImportError` if `source` imports a disallowed module.

    Only the imported module's top-level package name is checked, so both
    `import fastapi` and `from fastapi.routing import APIRoute` are rejected.

    Example:
        >>> check_source_imports("import requests")
        >>> check_source_imports("import fastapi")  # doctest: +SKIP
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".", maxsplit=1)[0]
                if top_level in DISALLOWED_TOP_LEVEL_MODULES:
                    raise DisallowedImportError(top_level)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            top_level = node.module.split(".", maxsplit=1)[0]
            if top_level in DISALLOWED_TOP_LEVEL_MODULES:
                raise DisallowedImportError(top_level)
