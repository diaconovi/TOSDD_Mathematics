"""Upload/replace-a-mutable-job use case (FR-007 through FR-009, FR-007a)."""

from math_job_operator.api.schemas.errors import ProblemDetailError
from math_job_operator.domain.entities import Job
from math_job_operator.domain.repositories import JobRepository
from math_job_operator.infrastructure.filesystem.immutable_job_loader import (
    normalize_job_name,
)
from math_job_operator.infrastructure.job_runtime.entry_point import InvalidEntryPointError
from math_job_operator.infrastructure.job_runtime.import_guard import DisallowedImportError
from math_job_operator.infrastructure.job_runtime.loader import (
    build_job,
    load_job_module_from_source,
)


def upload_job(
    filename: str,
    source: str,
    immutable_jobs: dict[str, Job],
    job_repository: JobRepository,
) -> Job:
    """Validate and store an uploaded job script, creating or replacing a mutable job.

    Raises:
        ProblemDetailError: 409 if the derived name matches an immutable job (FR-008);
            422 if the script is invalid (disallowed import or bad entry point, FR-009).

    Example:
        >>> upload_job(  # doctest: +SKIP
        ...     "my_job.py", "def run(arg: str) -> list:\\n    return []\\n",
        ...     immutable_jobs={}, job_repository=job_repository,
        ... )
    """
    name = normalize_job_name(filename)

    if name in immutable_jobs:
        raise ProblemDetailError(
            status_code=409,
            title="Conflict",
            detail=f"'{name}' is an immutable job and cannot be overwritten",
        )

    try:
        module = load_job_module_from_source(name, source)
    except (DisallowedImportError, InvalidEntryPointError, SyntaxError) as exc:
        raise ProblemDetailError(
            status_code=422, title="Unprocessable Entity", detail=str(exc)
        ) from exc

    job_repository.upsert(name, source)
    return build_job(name, module, "mutable")
