"""List-jobs and list-approved-packages use cases (FR-001, FR-001a, FR-010, FR-015)."""

from math_job_operator.domain.entities import Job
from math_job_operator.domain.repositories import JobRepository
from math_job_operator.infrastructure.job_runtime.loader import build_job, load_job_module_from_source

APPROVED_JOB_PACKAGES = ["requests", "pymongo", "to_session_manager", "to_collector_client"]
"""Third-party packages job scripts may import. Never includes the service's own
framework dependencies (fastapi, uvicorn, pydantic) — those are always disallowed
regardless of this list (FR-015)."""


def list_jobs(immutable_jobs: dict[str, Job], job_repository: JobRepository) -> list[Job]:
    """Combine the immutable filesystem index with every stored mutable job (FR-001).

    Example:
        >>> list_jobs({}, job_repository)  # doctest: +SKIP
    """
    mutable_jobs = []
    for record in job_repository.list_all():
        module = load_job_module_from_source(record.name, record.source)
        mutable_jobs.append(build_job(record.name, module, "mutable"))

    return [*immutable_jobs.values(), *mutable_jobs]


def list_approved_packages() -> list[str]:
    """Return the static list of packages approved for job scripts (FR-010)."""
    return list(APPROVED_JOB_PACKAGES)
