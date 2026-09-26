"""FastAPI dependency accessors, reading shared singletons off `app.state`."""

from fastapi import Request

from math_job_operator.config import Settings
from math_job_operator.domain.entities import Job
from math_job_operator.domain.repositories import JobRepository, VariableRepository
from math_job_operator.infrastructure.signaling.redis_signal_bus import RedisSignalBus


def get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def get_job_repository(request: Request) -> JobRepository:
    return request.app.state.job_repository  # type: ignore[no-any-return]


def get_variable_repository(request: Request) -> VariableRepository:
    return request.app.state.variable_repository  # type: ignore[no-any-return]


def get_immutable_jobs(request: Request) -> dict[str, Job]:
    return request.app.state.immutable_jobs  # type: ignore[no-any-return]


def get_signal_bus(request: Request) -> RedisSignalBus:
    return request.app.state.signal_bus  # type: ignore[no-any-return]
