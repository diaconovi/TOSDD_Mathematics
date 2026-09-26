"""Loads every immutable job from the filesystem at startup into a normalized index."""

from pathlib import Path

from math_job_operator.domain.entities import Job
from math_job_operator.infrastructure.job_runtime.loader import (
    build_job,
    load_job_module_from_file,
)


def normalize_job_name(filename: str) -> str:
    """Strip the extension and lowercase the remainder (FR-007, FR-007a).

    Example:
        >>> normalize_job_name("AWXSG_Example.PY")
        'awxsg_example'
    """
    return Path(filename).stem.lower()


def load_immutable_jobs(directory: Path) -> dict[str, Job]:
    """Scan `directory` for `.py` files and build the normalized immutable-job index.

    Example:
        >>> load_immutable_jobs(Path("jobs/immutable"))  # doctest: +SKIP
    """
    index: dict[str, Job] = {}
    if not directory.is_dir():
        return index

    for path in sorted(directory.glob("*.py")):
        name = normalize_job_name(path.name)
        module = load_job_module_from_file(path)
        index[name] = build_job(name, module, "immutable")

    return index
