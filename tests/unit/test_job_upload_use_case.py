"""Unit tests for the upload-job use case."""

from unittest.mock import MagicMock

import pytest

from math_job_operator.api.schemas.errors import ProblemDetailError
from math_job_operator.application.job_upload import upload_job
from math_job_operator.domain.entities import Job
from math_job_operator.domain.repositories import JobRepository

VALID_SOURCE = "def run(arg: str) -> list:\n    return []\n"
INVALID_ENTRY_POINT_SOURCE = "def run(value: int) -> list:\n    return []\n"
DISALLOWED_IMPORT_SOURCE = "import pydantic\ndef run(arg: str) -> list:\n    return []\n"


def _fake_repository() -> JobRepository:
    return MagicMock(spec=JobRepository)


def test_upload_normalizes_name_from_filename() -> None:
    repository = _fake_repository()

    job = upload_job("My_Job.PY", VALID_SOURCE, immutable_jobs={}, job_repository=repository)

    assert job.name == "my_job"
    assert job.job_type == "mutable"
    repository.upsert.assert_called_once_with("my_job", VALID_SOURCE)


def test_upload_rejects_immutable_name_collision_case_insensitively() -> None:
    repository = _fake_repository()
    immutable_jobs = {"awxsg_example": MagicMock(spec=Job)}

    with pytest.raises(ProblemDetailError) as exc_info:
        upload_job(
            "AWXSG_Example.py",
            VALID_SOURCE,
            immutable_jobs=immutable_jobs,
            job_repository=repository,
        )

    assert exc_info.value.status_code == 409
    repository.upsert.assert_not_called()


def test_upload_replaces_existing_mutable_job() -> None:
    repository = _fake_repository()

    upload_job("job_x.py", VALID_SOURCE, immutable_jobs={}, job_repository=repository)

    repository.upsert.assert_called_once_with("job_x", VALID_SOURCE)


def test_upload_rejects_invalid_entry_point_signature() -> None:
    repository = _fake_repository()

    with pytest.raises(ProblemDetailError) as exc_info:
        upload_job(
            "bad_job.py",
            INVALID_ENTRY_POINT_SOURCE,
            immutable_jobs={},
            job_repository=repository,
        )

    assert exc_info.value.status_code == 422
    repository.upsert.assert_not_called()


def test_upload_rejects_disallowed_import() -> None:
    repository = _fake_repository()

    with pytest.raises(ProblemDetailError) as exc_info:
        upload_job(
            "bad_job.py",
            DISALLOWED_IMPORT_SOURCE,
            immutable_jobs={},
            job_repository=repository,
        )

    assert exc_info.value.status_code == 422
    repository.upsert.assert_not_called()
