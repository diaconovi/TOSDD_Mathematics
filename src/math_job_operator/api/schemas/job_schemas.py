"""Pydantic request/response schemas for `/api/v1/jobs*` endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from math_job_operator.domain.entities import JSONValue, JobType


class JobSummary(BaseModel):
    """One entry in the `GET /api/v1/jobs` catalog response."""

    name: str
    description: str
    job_type: JobType
    return_type: str


class JobRunRequest(BaseModel):
    """One entry in the `POST /api/v1/jobs` request batch."""

    name: str
    args: list[dict[str, JSONValue]] = []
    depends_on: str | None = None


class JobRunResult(BaseModel):
    """One entry in the `POST /api/v1/jobs` response batch."""

    name: str
    finished_at: datetime
    duration: float
    status: Literal["completed", "error"]
    output: JSONValue = None
