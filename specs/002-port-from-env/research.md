# Research: Listening Port & Host from Environment Configuration

All Technical Context unknowns are resolved below. The behavioral claims were checked against the
locked dependency versions (uvicorn 0.53.0, pydantic 2.13.5, pydantic-settings 2.15.0) with a
throwaway probe script on 2026-10-29.

## R1 — Root cause of the current behavior

- **Finding**: The documented start command is
  `uv run uvicorn math_job_operator.api.main:app --reload --port "${PORT:-8000}"`. The shell
  expands `${PORT:-8000}` before uvicorn starts, and the shell never reads `.env`. `Settings.PORT`
  (`src/math_job_operator/config.py`) is loaded from `.env` correctly, but no code ever reads it.
  The uvicorn CLI chooses its port before the application module is imported, so nothing inside
  the app can change it.
- **Consequence**: The fix has to be a start entrypoint that reads `Settings` *before* the server
  starts and passes the host and port to uvicorn itself.

## R2 — Entrypoint shape

- **Decision**: Add a small launcher module, `src/math_job_operator/server.py`, with a
  `main(argv: Sequence[str] | None = None) -> None` function. It:
  1. parses optional `--host`, `--port` and `--reload` arguments with `argparse`;
  2. builds `Settings`, passing any explicitly given `--host`/`--port` as init keyword arguments;
  3. calls `uvicorn.run("math_job_operator.api.main:app", host=..., port=..., reload=...)`.

  It is registered as a console script in `pyproject.toml`
  (`[project.scripts] math-job-operator = "math_job_operator.server:main"`), so the standard start
  command becomes `uv run math-job-operator` (add `--reload` for development).
- **Rationale**:
  - `uv run math-job-operator` satisfies Constitution Principle II (always launched via `uv run`).
    The project is already installed in editable mode (`hatchling` build backend; a
    `_editable_impl_math_job_operator.pth` file exists in the venv), so a console script becomes
    available after `uv sync` with no extra tooling.
  - Passing the app as an *import string* is required for `reload=True`. The reloader child
    process receives host and port from the same `Config` object, so they persist across reloads
    (FR-008).
  - Keeping the launcher in its own module, separate from `api/main.py`, gives it one
    responsibility (Principle III). `api/main.py` stays the app factory, and tests that import
    `app` never pull in launcher logic.
- **Alternatives considered**:
  - *`uv run --env-file .env uvicorn ... --port "$PORT"`*: still depends on shell expansion, puts
    a second `.env` parser alongside pydantic-settings (violates FR-002), and breaks when `.env` is
    missing. Rejected.
  - *`UVICORN_PORT` / `UVICORN_HOST` environment variables*: uvicorn reads these natively, but that
    means renaming the user-facing setting, and they wouldn't be validated or defaulted by
    `Settings`. Rejected.
  - *An `if __name__ == "__main__":` block in `api/main.py`*: works with
    `uv run python -m math_job_operator.api.main`, but mixes the app factory with process
    bootstrapping and gives a longer, less discoverable command. Rejected in favor of a named
    console script.

## R3 — Precedence order (FR-004 / FR-010)

- **Decision**: Use pydantic-settings' own source order and add one layer on top:
  **init kwargs (CLI flags) > process environment > `.env` > field default**.
- **Verification** (probe results):
  - `.env` `PORT=8081`, nothing else set → 8081
  - `.env` `PORT=8081` plus environment `PORT=9091` → 9091
  - `.env` `PORT=8081` plus init kwarg `PORT=9090` → 9090
  - empty `.env` → 8000 / `127.0.0.1`
- **Rationale**: This needs no custom merging code. CLI overrides go through the same validation
  as every other source.
- **Alternatives considered**: Merging sources by hand in `server.py`. Rejected because it
  duplicates what pydantic-settings already guarantees.

## R4 — Validation of `PORT` and `HOST` (FR-005, edge cases)

- **Decision**:
  - `PORT: Annotated[int, Field(ge=1, le=65535)] = 8000`
  - `HOST: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = "127.0.0.1"`

  Whitespace stripping is scoped to `HOST` only, rather than setting a model-wide
  `str_strip_whitespace`, so other settings don't change behavior.
- **Verification** (probe results):

  | `.env` line | Result |
  |---|---|
  | `PORT= 8081 ` | 8081 (the dotenv parser trims unquoted values) |
  | `PORT=` | `ValidationError` at `('PORT',)`: "unable to parse string as an integer" |
  | `PORT=abc` | `ValidationError` at `('PORT',)` |
  | `PORT=70000` | `ValidationError` at `('PORT',)`: "less than or equal to 65535" |
  | `HOST=` | `ValidationError` at `('HOST',)`: "at least 1 character" |
  | `HOST= 0.0.0.0 ` | `0.0.0.0` |

- **Error presentation**: `server.main` catches `pydantic.ValidationError` from building
  `Settings`, writes one line per error to stderr in the form
  `Invalid configuration: PORT=<value>: <message>`, and exits with status 2. It doesn't start the
  server and doesn't fall back to defaults. The error names the setting and the value (SC-003).
  Raising `SystemExit` keeps the output free of a traceback.
- **Alternatives considered**: Validating the host as an IP address only. Rejected because
  hostnames such as `localhost` are legitimate bind targets. Whether an address can actually be
  bound is decided at bind time (R5).

## R5 — Bind failures (FR-006, `HOST` edge case)

- **Decision**: No extra code. When binding fails (address already in use, or an address the
  machine doesn't have), uvicorn logs
  `[Errno N] error while attempting to bind on address ('<host>', <port>): <reason>` and exits the
  process with a non-zero status. It never retries on another port.
- **Rationale**: The message already names both host and port, and the exit is non-zero, which
  meets FR-006. Wrapping it would only duplicate uvicorn's behavior.

## R6 — Startup report (FR-007)

- **Decision**:
  - Rely on uvicorn's `Uvicorn running on http://<host>:<port>` log line, which is emitted both in
    normal mode and by the reload supervisor.
  - Add one explicit line from the launcher before handing over:
    `Starting Math Job Operator API on <host>:<port> (reload=<bool>)`. It names the resolved
    values even if uvicorn's log format or level changes.
- **Rationale**: This is cheap and deterministic, and it lets unit tests assert the reported
  values without starting a server.

## R7 — Testing approach

- **Decision**:
  - **Unit tests** in `tests/unit/test_server.py`. They monkeypatch `uvicorn.run` and build
    settings from a temporary `.env` file and controlled environment variables. They cover:
    - each precedence level;
    - the defaults;
    - every validation edge case (exit status 2 and the message names the setting);
    - `--reload` being passed through.
  - **Integration smoke test** in `tests/integration/test_server_startup.py`. It launches
    `math-job-operator` as a subprocess with `PORT` set to a free port and asserts that
    `GET /api/v1/jobs` answers on that port. It reuses the MongoDB/Redis prerequisites the existing
    integration suite already needs.
- **Rationale**:
  - The launcher is entrypoint code, outside the domain/application layers that the 80% coverage
    floor (Principle X) applies to. Unit tests still cover it fully because the resolution logic is
    pure.
  - The smoke test is the single end-to-end proof for SC-001.
  - No new repository or external HTTP client is added, so no new contract tests are required.
