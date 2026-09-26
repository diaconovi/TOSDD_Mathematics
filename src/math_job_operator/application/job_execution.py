"""Dependency-graph scheduling and execution for `POST /api/v1/jobs` (FR-002 through FR-006c)."""

import asyncio
import json
import logging
import types
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import cast
from zoneinfo import ZoneInfo

from math_job_operator.domain.entities import JSONValue, Job, JobRunRequest, JobRunResult, JobStatus
from math_job_operator.domain.repositories import JobRepository, VariableRepository
from math_job_operator.infrastructure.job_runtime.loader import (
    build_job,
    load_job_module_from_source,
)
from math_job_operator.infrastructure.signaling.redis_signal_bus import RedisSignalBus

logger = logging.getLogger(__name__)


def _lookup_job(name: str, immutable_jobs: dict[str, Job], job_repository: JobRepository) -> Job | None:
    """Resolve a job name against the combined immutable + mutable catalog."""
    normalized = name.strip().lower()
    if normalized in immutable_jobs:
        return immutable_jobs[normalized]

    record = job_repository.get_by_name(normalized)
    if record is None:
        return None
    module = load_job_module_from_source(record.name, record.source)
    return build_job(record.name, module, "mutable")


async def run_job_batch(
    requests: list[JobRunRequest],
    *,
    immutable_jobs: dict[str, Job],
    job_repository: JobRepository,
    variable_repository: VariableRepository,
    signal_bus: RedisSignalBus,
    time_zone: str,
) -> list[JobRunResult]:
    """Execute every job in `requests`, resolving same-batch dependencies, and return results.

    Implements FR-002 through FR-006c: concurrent execution, dependency waiting, `upstream`
    variable injection, upstream-failure propagation, unknown-job/dangling-dependency
    handling, and non-serializable-output handling.

    Example:
        >>> results = await run_job_batch(  # doctest: +SKIP
        ...     [JobRunRequest(name="fetch", args=[{"epic": "AWXSG"}])],
        ...     immutable_jobs=immutable_jobs, job_repository=job_repository,
        ...     variable_repository=variable_repository, signal_bus=signal_bus,
        ...     time_zone="UTC",
        ... )
    """
    batch_id = uuid.uuid4().hex
    requested_names = {request.name.strip().lower() for request in requests}

    resolved: dict[str, Job | None] = {
        request.name.strip().lower(): _lookup_job(request.name, immutable_jobs, job_repository)
        for request in requests
    }

    results: dict[str, JobRunResult] = {}
    tasks: dict[str, asyncio.Task[None]] = {}

    async def execute_one(request: JobRunRequest) -> None:
        normalized_name = request.name.strip().lower()
        job = resolved[normalized_name]

        if job is None:
            result = _error_result(request.name, time_zone, "job not found")
            results[normalized_name] = result
            await signal_bus.publish_completion(batch_id, normalized_name, "error")
            return

        if request.depends_on is not None:
            upstream_name = request.depends_on.strip().lower()
            if upstream_name not in requested_names:
                result = _error_result(
                    request.name, time_zone, f"dependency '{request.depends_on}' not found"
                )
                results[normalized_name] = result
                await signal_bus.publish_completion(batch_id, normalized_name, "error")
                return

            upstream_status = await signal_bus.wait_for_completion(batch_id, upstream_name)
            if upstream_status == "error":
                result = _error_result(
                    request.name,
                    time_zone,
                    f"upstream job '{request.depends_on}' failed",
                )
                results[normalized_name] = result
                await signal_bus.publish_completion(batch_id, normalized_name, "error")
                return
            upstream_output = results[upstream_name].output
        else:
            upstream_output = None

        result = await _invoke_job(
            request, job, variable_repository, time_zone, upstream_output
        )
        results[normalized_name] = result
        await signal_bus.publish_completion(batch_id, normalized_name, result.status)

    for request in requests:
        tasks[request.name.strip().lower()] = asyncio.create_task(execute_one(request))

    await asyncio.gather(*tasks.values())

    return [results[request.name.strip().lower()] for request in requests]


async def _invoke_job(
    request: JobRunRequest,
    job: Job,
    variable_repository: VariableRepository,
    time_zone: str,
    upstream_output: JSONValue,
) -> JobRunResult:
    """Run one job's `run()` entry point and build its `JobRunResult` (FR-002a, FR-004, FR-006, FR-006c, FR-014, FR-020)."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    started_at = datetime.now(ZoneInfo(time_zone))
    logger.info("job %s started at %s", request.name, started_at.isoformat())

    variables = {v.name: v.value for v in variable_repository.get_all()}
    context: dict[str, JSONValue] = dict(variables)
    if request.depends_on is not None:
        context["upstream"] = upstream_output

    arg = json.dumps(request.args)

    output: JSONValue
    status: JobStatus
    try:
        raw_output = await asyncio.to_thread(_run_with_context, job, arg, context)
        json.dumps(raw_output)  # FR-006c: verify the output is JSON-serializable
        output = cast(JSONValue, raw_output)
        status = "completed"
    except Exception as exc:  # noqa: BLE001 - any job failure becomes an "error" result
        output = str(exc)
        status = "error"

    duration = loop.time() - start
    finished_at = datetime.now(ZoneInfo(time_zone))
    logger.info(
        "job %s finished at %s status=%s duration=%.3fs",
        request.name,
        finished_at.isoformat(),
        status,
        duration,
    )
    return JobRunResult(
        name=request.name,
        finished_at=finished_at,
        duration=duration,
        status=status,
        output=output,
    )


def _run_with_context(job: Job, arg: str, context: Mapping[str, object]) -> list[object]:
    """Run a job's entry point with `context` visible as module-level names.

    Builds a *new* function object sharing the original's code but backed by a fresh,
    per-call globals dict (a copy of the module's globals merged with `context`), rather
    than mutating the module's own `__globals__` in place. Immutable jobs are loaded once
    at startup and their module object is reused across every request, so mutating it
    directly would race under concurrent execution (FR-003); this keeps each call isolated
    regardless of job type.
    """
    entry_point = job.entry_point
    isolated_globals = {**getattr(entry_point, "__globals__", {}), **context}
    isolated_run = types.FunctionType(
        entry_point.__code__,
        isolated_globals,
        entry_point.__name__,
        entry_point.__defaults__,
        entry_point.__closure__,
    )
    return cast("list[object]", isolated_run(arg))


def _error_result(name: str, time_zone: str, detail: str) -> JobRunResult:
    logger.info("job %s finished immediately status=error detail=%s", name, detail)
    return JobRunResult(
        name=name,
        finished_at=datetime.now(ZoneInfo(time_zone)),
        duration=0.0,
        status="error",
        output=detail,
    )
