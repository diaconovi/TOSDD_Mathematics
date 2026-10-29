"""Unit tests for the process entrypoint: host/port resolution, validation, and handoff to uvicorn."""

from pathlib import Path

import pytest

from math_job_operator import server

REQUIRED_ENV = {
    "MONGO_URL": "127.0.0.1",
    "MONGO_PORT": "27017",
    "MONGO_ACCOUNT_DB": "mathematics_test",
}


class RecordedRun:
    """Stand-in for `uvicorn.run` that records its call instead of starting a server."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))

    @property
    def only_call(self) -> tuple[tuple[object, ...], dict[str, object]]:
        assert len(self.calls) == 1
        return self.calls[0]


@pytest.fixture
def uvicorn_run(monkeypatch: pytest.MonkeyPatch) -> RecordedRun:
    recorder = RecordedRun()
    monkeypatch.setattr("math_job_operator.server.uvicorn.run", recorder)
    return recorder


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the developer's real `.env` and shell exports out of every test."""
    monkeypatch.chdir(tmp_path)
    for name in ("PORT", "HOST", *REQUIRED_ENV):
        monkeypatch.delenv(name, raising=False)


def write_env(tmp_path: Path, *lines: str) -> None:
    required = [f"{key}={value}" for key, value in REQUIRED_ENV.items()]
    (tmp_path / ".env").write_text("\n".join([*required, *lines]) + "\n")


# --- User Story 1: start on the configured port -------------------------------------


def test_port_and_host_from_env_file(tmp_path: Path, uvicorn_run: RecordedRun) -> None:
    write_env(tmp_path, "PORT=8081", "HOST=0.0.0.0")

    server.main([])

    args, kwargs = uvicorn_run.only_call
    assert args == ("math_job_operator.api.main:app",)
    assert kwargs == {"host": "0.0.0.0", "port": 8081, "reload": False}


def test_reload_flag_passes_through(tmp_path: Path, uvicorn_run: RecordedRun) -> None:
    write_env(tmp_path, "PORT=8081")

    server.main(["--reload"])

    _, kwargs = uvicorn_run.only_call
    assert kwargs["reload"] is True
    assert kwargs["port"] == 8081


def test_startup_line_reports_resolved_address(
    tmp_path: Path, uvicorn_run: RecordedRun, capsys: pytest.CaptureFixture[str]
) -> None:
    write_env(tmp_path, "PORT=8081")

    server.main([])

    assert (
        "Starting Math Job Operator API on 127.0.0.1:8081 (reload=false)"
        in capsys.readouterr().out
    )


# --- User Story 2: defaults and fail-fast validation --------------------------------


def test_defaults_when_unconfigured(tmp_path: Path, uvicorn_run: RecordedRun) -> None:
    write_env(tmp_path)

    server.main([])

    _, kwargs = uvicorn_run.only_call
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8000


@pytest.mark.parametrize(
    ("env_line", "name"),
    [
        ("PORT=", "PORT"),
        ("PORT=abc", "PORT"),
        ("PORT=0", "PORT"),
        ("PORT=70000", "PORT"),
        ("HOST=", "HOST"),
    ],
)
def test_invalid_values_refuse_to_start(
    tmp_path: Path,
    uvicorn_run: RecordedRun,
    capsys: pytest.CaptureFixture[str],
    env_line: str,
    name: str,
) -> None:
    write_env(tmp_path, env_line)

    with pytest.raises(SystemExit) as excinfo:
        server.main([])

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert f"Invalid configuration: {name}=" in captured.err
    assert captured.out == ""
    assert uvicorn_run.calls == []


def test_whitespace_is_trimmed(tmp_path: Path, uvicorn_run: RecordedRun) -> None:
    write_env(tmp_path, "PORT= 8081 ", "HOST= 0.0.0.0 ")

    server.main([])

    _, kwargs = uvicorn_run.only_call
    assert kwargs["port"] == 8081
    assert kwargs["host"] == "0.0.0.0"


# --- User Story 3: one-off overrides -------------------------------------------------


def test_process_env_overrides_env_file(
    tmp_path: Path, uvicorn_run: RecordedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_env(tmp_path, "PORT=8081", "HOST=127.0.0.1")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("HOST", "0.0.0.0")

    server.main([])

    _, kwargs = uvicorn_run.only_call
    assert kwargs["port"] == 9090
    assert kwargs["host"] == "0.0.0.0"


def test_cli_flags_override_env_and_env_file(
    tmp_path: Path, uvicorn_run: RecordedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_env(tmp_path, "PORT=8081")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("HOST", "0.0.0.0")

    server.main(["--port", "9191", "--host", "localhost"])

    _, kwargs = uvicorn_run.only_call
    assert kwargs["port"] == 9191
    assert kwargs["host"] == "localhost"


def test_cli_port_out_of_range_refused(
    tmp_path: Path, uvicorn_run: RecordedRun, capsys: pytest.CaptureFixture[str]
) -> None:
    write_env(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        server.main(["--port", "70000"])

    assert excinfo.value.code == 2
    assert "Invalid configuration: PORT=70000" in capsys.readouterr().err
    assert uvicorn_run.calls == []
