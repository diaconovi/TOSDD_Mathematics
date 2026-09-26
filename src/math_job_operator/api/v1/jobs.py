"""`/api/v1/jobs*` endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile

from math_job_operator.api.deps import (
    get_immutable_jobs,
    get_job_repository,
    get_settings,
    get_signal_bus,
    get_variable_repository,
)
from math_job_operator.api.schemas.job_schemas import JobRunRequest, JobRunResult, JobSummary
from math_job_operator.api.schemas.variable_schemas import VariableOut
from math_job_operator.application.job_catalog import list_approved_packages, list_jobs
from math_job_operator.application.job_execution import run_job_batch
from math_job_operator.application.job_upload import upload_job
from math_job_operator.application.variable_management import list_variables
from math_job_operator.config import Settings
from math_job_operator.domain.entities import Job, JobRunRequest as DomainJobRunRequest
from math_job_operator.domain.repositories import JobRepository, VariableRepository
from math_job_operator.infrastructure.signaling.redis_signal_bus import RedisSignalBus

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
async def get_jobs(
    immutable_jobs: dict[str, Job] = Depends(get_immutable_jobs),
    job_repository: JobRepository = Depends(get_job_repository),
) -> list[JobSummary]:
    """List every available job, immutable and mutable (FR-001)."""
    jobs = list_jobs(immutable_jobs, job_repository)
    return [
        JobSummary(
            name=job.name,
            description=job.description,
            job_type=job.job_type,
            return_type=job.return_type,
        )
        for job in jobs
    ]


@router.get("/dependencies", response_model=list[str])
async def get_dependencies() -> list[str]:
    """List the third-party packages approved for job scripts to import (FR-010)."""
    return list_approved_packages()


@router.get("/variables", response_model=list[VariableOut])
async def get_job_variables(
    variable_repository: VariableRepository = Depends(get_variable_repository),
) -> list[VariableOut]:
    """List the current set of shared variables available to all jobs (FR-011)."""
    return [VariableOut(name=v.name, value=v.value) for v in list_variables(variable_repository)]


@router.put("", response_model=JobSummary)
async def put_job(
    file: UploadFile = File(...),
    immutable_jobs: dict[str, Job] = Depends(get_immutable_jobs),
    job_repository: JobRepository = Depends(get_job_repository),
) -> JobSummary:
    """Upload or replace a mutable job script (FR-007 through FR-009, FR-007a)."""
    source = (await file.read()).decode("utf-8")
    job = upload_job(file.filename or "", source, immutable_jobs, job_repository)
    return JobSummary(
        name=job.name,
        description=job.description,
        job_type=job.job_type,
        return_type=job.return_type,
    )


@router.post("", response_model=list[JobRunResult])
async def run_jobs(
    requests: list[JobRunRequest],
    immutable_jobs: dict[str, Job] = Depends(get_immutable_jobs),
    job_repository: JobRepository = Depends(get_job_repository),
    variable_repository: VariableRepository = Depends(get_variable_repository),
    signal_bus: RedisSignalBus = Depends(get_signal_bus),
    settings: Settings = Depends(get_settings),
) -> list[JobRunResult]:
    """Run a batch of jobs, resolving same-batch dependencies (FR-002 through FR-006c)."""
    domain_requests = [
        DomainJobRunRequest(name=r.name, args=r.args, depends_on=r.depends_on)
        for r in requests
    ]
    domain_results = await run_job_batch(
        domain_requests,
        immutable_jobs=immutable_jobs,
        job_repository=job_repository,
        variable_repository=variable_repository,
        signal_bus=signal_bus,
        time_zone=settings.TIME_ZONE,
    )
    return [
        JobRunResult(
            name=r.name,
            finished_at=r.finished_at,
            duration=r.duration,
            status=r.status,
            output=r.output,
        )
        for r in domain_results
    ]
