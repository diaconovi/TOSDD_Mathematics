"""Unit tests for the entry-point signature validator."""

import types

import pytest

from math_job_operator.infrastructure.job_runtime.entry_point import (
    InvalidEntryPointError,
    validate_entry_point,
)


def _module_from_source(source: str) -> types.ModuleType:
    module = types.ModuleType("test_job")
    exec(source, module.__dict__)  # noqa: S102 - test-only, trusted source
    return module


def test_valid_entry_point_passes() -> None:
    module = _module_from_source("def run(arg: str) -> list:\n    return []\n")
    validate_entry_point(module)  # must not raise


def test_missing_run_is_rejected() -> None:
    module = _module_from_source("def other() -> None:\n    pass\n")
    with pytest.raises(InvalidEntryPointError):
        validate_entry_point(module)


def test_wrong_parameter_name_is_rejected() -> None:
    module = _module_from_source("def run(value: str) -> list:\n    return []\n")
    with pytest.raises(InvalidEntryPointError):
        validate_entry_point(module)


def test_extra_required_parameter_is_rejected() -> None:
    module = _module_from_source("def run(arg: str, extra: int) -> list:\n    return []\n")
    with pytest.raises(InvalidEntryPointError):
        validate_entry_point(module)


def test_wrong_parameter_type_is_rejected() -> None:
    module = _module_from_source("def run(arg: int) -> list:\n    return []\n")
    with pytest.raises(InvalidEntryPointError):
        validate_entry_point(module)


def test_wrong_return_annotation_is_rejected() -> None:
    module = _module_from_source("def run(arg: str) -> dict:\n    return {}\n")
    with pytest.raises(InvalidEntryPointError):
        validate_entry_point(module)


def test_run_not_callable_is_rejected() -> None:
    module = _module_from_source("run = 'not a function'\n")
    with pytest.raises(InvalidEntryPointError):
        validate_entry_point(module)
