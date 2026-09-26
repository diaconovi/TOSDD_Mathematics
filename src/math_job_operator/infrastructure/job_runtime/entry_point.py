"""Validates that a loaded job module exposes `def run(arg: str) -> list` (FR-009)."""

import inspect
import types
import typing


class InvalidEntryPointError(Exception):
    """Raised when a job module doesn't expose the required `run` entry point."""


def validate_entry_point(module: types.ModuleType) -> None:
    """Raise `InvalidEntryPointError` unless `module.run` matches `(arg: str) -> list`.

    Example:
        >>> import types
        >>> m = types.ModuleType("ok")
        >>> exec("def run(arg: str) -> list:\\n    return []", m.__dict__)
        >>> validate_entry_point(m)
    """
    run = getattr(module, "run", None)
    if run is None or not callable(run):
        raise InvalidEntryPointError("module does not define a callable 'run' entry point")

    signature = inspect.signature(run)
    parameters = list(signature.parameters.values())
    if len(parameters) != 1 or parameters[0].name != "arg":
        raise InvalidEntryPointError(
            "'run' must accept exactly one parameter named 'arg'"
        )

    try:
        hints = typing.get_type_hints(run)
    except Exception as exc:  # noqa: BLE001 - any hint-resolution failure is invalid
        raise InvalidEntryPointError(f"could not resolve 'run' type hints: {exc}") from exc

    if hints.get("arg") is not str:
        raise InvalidEntryPointError("'run's 'arg' parameter must be annotated 'str'")
    if hints.get("return") is not list:
        raise InvalidEntryPointError("'run' must be annotated to return 'list'")
