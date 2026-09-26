"""Domain entities for the Math Job Operator API.

See specs/001-job-operator-api/data-model.md for the authoritative field/validation reference.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

type JSONValue = str | int | float | bool | None | dict[str, JSONValue] | list[JSONValue]
"""Any JSON-representable value. Used instead of bare `Any` (Constitution Principle I).

Example:
    >>> value: JSONValue = {"epic": "AWXSG", "prices": [1.0, 2.5], "ok": True}
"""

JobType = Literal["mutable", "immutable"]
JobStatus = Literal["completed", "error"]


@dataclass(frozen=True, slots=True)
class Job:
    """A catalog entry for a runnable job.

    `name` is always normalized: lowercased with its file extension stripped (FR-007),
    and matched case-insensitively against every other job (FR-007a).
    """

    name: str
    description: str
    job_type: JobType
    return_type: str
    entry_point: Callable[[str], list[JSONValue]]


@dataclass(frozen=True, slots=True)
class JobRunRequest:
    """One entry in the ordered batch submitted to `POST /api/v1/jobs`."""

    name: str
    args: list[dict[str, JSONValue]]
    depends_on: str | None = None


@dataclass(frozen=True, slots=True)
class JobRunResult:
    """The outcome of one executed (or rejected) `JobRunRequest`."""

    name: str
    finished_at: datetime
    duration: float
    status: JobStatus
    output: JSONValue


@dataclass(frozen=True, slots=True)
class SharedVariable:
    """A named value available to every job execution.

    `name` is always normalized to uppercase (FR-013); `value` may be any JSON type
    (FR-013a).
    """

    name: str
    value: JSONValue


@dataclass(frozen=True, slots=True)
class ApprovedPackage:
    """A third-party package job scripts are permitted to import (FR-010)."""

    name: str
