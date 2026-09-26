"""Dynamic job loading: from a filesystem file (immutable) or Mongo source (mutable)."""

import importlib.util
import inspect
import types
from pathlib import Path

from math_job_operator.domain.entities import Job, JobType
from math_job_operator.infrastructure.job_runtime.entry_point import validate_entry_point
from math_job_operator.infrastructure.job_runtime.import_guard import check_source_imports

DEFAULT_RETURN_TYPE = "list"


def load_job_module_from_file(path: Path) -> types.ModuleType:
    """Load an immutable job's module from a `.py` file on disk.

    Validates the import guard and entry-point signature before returning.

    Example:
        >>> load_job_module_from_file(Path("jobs/immutable/awxsg_example.py"))  # doctest: +SKIP
    """
    check_source_imports(path.read_text())

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load a module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    validate_entry_point(module)
    return module


def build_job(name: str, module: types.ModuleType, job_type: JobType) -> Job:
    """Build a `Job` catalog entry from an already-validated, loaded module.

    `description` comes from a module-level `DESCRIPTION` constant, falling back to the
    module's docstring, then an empty string. `return_type` comes from a module-level
    `RETURN_TYPE` constant (FR-001a), defaulting to `"list"` (FR-009's fixed annotation).

    Example:
        >>> import types
        >>> m = types.ModuleType("m")
        >>> exec("def run(arg: str) -> list:\\n    return []", m.__dict__)
        >>> build_job("m", m, "mutable").return_type
        'list'
    """
    description = getattr(module, "DESCRIPTION", None) or inspect.getdoc(module) or ""
    return_type = getattr(module, "RETURN_TYPE", None) or DEFAULT_RETURN_TYPE
    return Job(
        name=name,
        description=description,
        job_type=job_type,
        return_type=return_type,
        entry_point=module.run,
    )


def load_job_module_from_source(name: str, source: str) -> types.ModuleType:
    """Load a mutable job's module by compiling `source` into a fresh module namespace.

    Validates the import guard and entry-point signature before returning.

    Example:
        >>> load_job_module_from_source(
        ...     "my_job", "def run(arg: str) -> list:\\n    return []"
        ... )  # doctest: +ELLIPSIS
        <module 'my_job'>
    """
    check_source_imports(source)

    module = types.ModuleType(name)
    code = compile(source, f"<mutable:{name}>", "exec")
    exec(code, module.__dict__)  # noqa: S102 - source is a validated, approved-package-only job

    validate_entry_point(module)
    return module
