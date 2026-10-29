---

description: "Task list for feature 002: listening port & host from environment configuration"
---

# Tasks: Listening Port & Host from Environment Configuration

**Input**: Design documents from `/specs/002-port-from-env/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/start-command.md, quickstart.md

**Tests**: Included. The plan (research R7) explicitly calls for unit tests of the launcher plus one end-to-end smoke test, and Constitution Principle X requires a testing discipline. Write each story's tests first and confirm they fail before implementing.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)

## Shared conventions for all test tasks

- Unit tests for the launcher live in `tests/unit/test_server.py`. Every test MUST isolate itself from the developer's real `.env` and shell:
  - `monkeypatch.chdir(tmp_path)`.
  - Write a `tmp_path / ".env"` containing the required settings: `MONGO_URL=127.0.0.1`, `MONGO_PORT=27017`, `MONGO_ACCOUNT_DB=mathematics_test`. Add `PORT=`/`HOST=` lines only as the test needs them.
  - `monkeypatch.delenv("PORT", raising=False)` and `monkeypatch.delenv("HOST", raising=False)`.
- Tests MUST NOT start a real server. They replace `uvicorn.run` with a recorder: `monkeypatch.setattr("math_job_operator.server.uvicorn.run", fake)`, where `fake` captures its positional and keyword arguments.
- Put shared helpers in `tests/unit/test_server.py` (for example `write_env(tmp_path, **lines)` and the recorder fixture) the first time they're needed, and reuse them in later tasks.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Register the new start command so `uv run math-job-operator` exists.

- [X] T001 Add a `[project.scripts]` table to `pyproject.toml` containing `math-job-operator = "math_job_operator.server:main"` (place it right after the `[project]` dependencies block). Then run `uv sync` so the console script is installed into `.venv`. Don't add any dependencies: uvicorn, pydantic and pydantic-settings are already declared.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The configuration fields and the launcher skeleton that every user story builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 In `src/math_job_operator/config.py`, change the `Settings` fields, keeping all other fields unchanged:
  - **PORT** becomes `PORT: Annotated[int, Field(ge=1, le=65535)] = 8000`. data-model.md: "`int`, from 1 to 65535 inclusive", default `8000`.
  - **HOST** is added right after `PORT`: `HOST: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = "127.0.0.1"`. data-model.md: "`str`, surrounding whitespace stripped, at least 1 character after stripping", default `"127.0.0.1"`.
  - Import `Annotated` from `typing`, and `Field` and `StringConstraints` from `pydantic`.
  - Don't set a model-wide `str_strip_whitespace` (research R4).
  - Extend the class docstring example with `>>> s.HOST` → `'127.0.0.1'`.
- [X] T003 Create `src/math_job_operator/server.py` with a module docstring, `"""Process entrypoint: resolve host/port from Settings and start uvicorn."""`, and these fully typed functions (strict mypy, no `Any`):
  1. **`parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace`**
     - `prog="math-job-operator"`.
     - `--host` (`type=str`, `default=None`), `--port` (`type=int`, `default=None`), `--reload` (`action="store_true"`).
  2. **`load_settings(args: argparse.Namespace) -> Settings`**
     - Builds a dict of overrides holding only the flags that are not `None` (`HOST` from `args.host`, `PORT` from `args.port`).
     - Returns `Settings(**overrides)`, so precedence is init kwargs > environment > `.env` > default (research R3).
  3. **`main(argv: Sequence[str] | None = None) -> None`**
     - Calls `parse_args`, then `load_settings`.
     - Prints exactly `Starting Math Job Operator API on {host}:{port} (reload={true|false})` to stdout with `print(..., flush=True)`, so the line appears straight away even when stdout is piped. Use lowercase `true`/`false` (contracts/start-command.md).
     - Calls `uvicorn.run("math_job_operator.api.main:app", host=settings.HOST, port=settings.PORT, reload=args.reload)`. The app MUST be passed as this import string, not as an object, so that `reload` works (research R2).

  Give `main` a docstring with a usage example (Constitution III), for example `uv run math-job-operator --reload`. This skeleton doesn't handle validation errors; that's T011.
- [X] T004 In `src/math_job_operator/api/main.py`, change the module docstring from `"""FastAPI app factory and uvicorn entrypoint."""` to `"""FastAPI app factory. The process entrypoint lives in math_job_operator.server."""`. Don't change any code.

**Checkpoint**: `uv run math-job-operator --help` prints the three flags, and `uv run mypy src` passes.

---

## Phase 3: User Story 1 - Start the service on the configured port (Priority: P1) 🎯 MVP

**Goal**: The standard start command listens on `PORT` (and binds to `HOST`) from `.env`, with no shell exports, and keeps doing so across auto-reloads.

**Independent Test**: Set `PORT=8081` in `.env`, run `uv run math-job-operator` from a shell where `PORT` isn't exported, and check that `GET http://127.0.0.1:8081/api/v1/jobs` answers and nothing listens on 8000 (quickstart Scenario 1).

### Tests for User Story 1 ⚠️

> Write these tests FIRST and confirm they fail before T008 to T010.

- [X] T005 [P] [US1] In `tests/unit/test_server.py` (new file; follow the shared conventions above), add `test_port_and_host_from_env_file`. It writes `.env` with `PORT=8081` and `HOST=0.0.0.0` plus the required settings, calls `server.main([])`, and asserts the recorded `uvicorn.run` call was `("math_job_operator.api.main:app",)` with `host="0.0.0.0"`, `port=8081`, `reload=False`.
- [X] T006 [P] [US1] In `tests/unit/test_server.py`, add two tests:
  - `test_reload_flag_passes_through`: `.env` has `PORT=8081`; calling `server.main(["--reload"])` records `reload=True` and `port=8081`.
  - `test_startup_line_reports_resolved_address`: uses `capsys`. `.env` has `PORT=8081`; calling `server.main([])` prints stdout containing exactly `Starting Math Job Operator API on 127.0.0.1:8081 (reload=false)`.
- [X] T007 [P] [US1] Create `tests/integration/test_server_startup.py`. It needs the same MongoDB and Redis as the existing integration tests. Put the shared setup in two helpers:
  - **`free_port() -> int`**: bind a socket to `("127.0.0.1", 0)`, read the port, close the socket.
  - **`child_env(port: int) -> dict[str, str]`**: return a copy of `os.environ` with:
    - `PORT=str(port)`;
    - `HOST=127.0.0.1`, set explicitly rather than popped, so a `HOST=` line in the repository `.env` can't change the result;
    - `MONGO_ACCOUNT_DB=mathematics_test` and `REDIS_URL=redis://localhost:6379/1`, the same values as `tests/conftest.py`, so dev data isn't touched;
    - `PYTHONUNBUFFERED=1`.

  Start the service with `subprocess.Popen(["uv", "run", "--no-sync", "math-job-operator"], env=..., cwd=<repository root>, stdout=PIPE, stderr=STDOUT, text=True)`. This follows Constitution Principle II, which requires starting the app via `uv run`.

  Add two tests:
  1. **`test_service_listens_on_port_from_env`**
     - Start the service with `child_env(free_port())`.
     - Poll `httpx.get(f"http://127.0.0.1:{port}/api/v1/jobs")` every 0.25 s for up to 15 s and assert status 200.
     - In a `finally` block, call `terminate()` and then `communicate(timeout=10)` to collect the output, so the pipe can't deadlock.
     - Assert the collected output contains `on 127.0.0.1:{port}`.
  2. **`test_bind_failure_exits_without_fallback`** (FR-006)
     - Hold a port: bind and `listen()` a socket on `("127.0.0.1", port)`, and keep it open for the whole test.
     - Start the service with `child_env(port)` and call `communicate(timeout=30)`.
     - Assert `returncode != 0`, and that the output contains `str(port)` and `address already in use` (case-insensitive).

### Implementation for User Story 1

- [X] T008 [US1] Make T005 and T006 pass with the skeleton from T003 in `src/math_job_operator/server.py`. Fix only what the tests reveal; for example, the `reload=` boolean must render as lowercase `true`/`false`, and `main` must forward `args.reload`. Run `uv run pytest tests/unit/test_server.py`.
- [X] T009 [US1] Run `uv run pytest tests/integration/test_server_startup.py` with MongoDB and Redis running, and fix `src/math_job_operator/server.py` until it passes. Then check FR-008 by hand with quickstart Scenario 2: start with `--reload`, `touch src/math_job_operator/api/main.py`, and confirm the service still answers on the same port.
- [X] T010 [US1] Update `README.md`:
  - In the run block, replace `uv run uvicorn math_job_operator.api.main:app --reload --port "${PORT:-8000}"` with `uv run math-job-operator --reload` and a one-line comment that host and port come from `.env`.
  - Add a `HOST` row to the Configuration table, directly below `PORT`: `| \`HOST\` | Network address to bind (\`0.0.0.0\` = all interfaces) | \`127.0.0.1\` |`.

**Checkpoint**: User Story 1 works. `PORT`/`HOST` in `.env` decide where the service listens. This is the MVP.

---

## Phase 4: User Story 2 - Fall back to the default port when none is configured (Priority: P2)

**Goal**: With no `PORT`/`HOST` configured anywhere, the service listens on `127.0.0.1:8000`. Invalid configured values are refused instead of quietly falling back.

**Independent Test**: Remove `PORT` and `HOST` from `.env`, run `uv run math-job-operator`, and confirm the startup line says `127.0.0.1:8000`. Then run `PORT=abc uv run math-job-operator` and confirm exit status 2 with a message naming `PORT` (quickstart Scenarios 4 and 6).

### Tests for User Story 2 ⚠️

- [X] T011 [P] [US2] In `tests/unit/test_server.py`, add `test_defaults_when_unconfigured`: `.env` holds only the required Mongo settings, and calling `server.main([])` records `host="127.0.0.1"`, `port=8000`.
- [X] T012 [P] [US2] In `tests/unit/test_server.py`, add a parametrized `test_invalid_values_refuse_to_start` over these `.env` lines:
  - `PORT=` (expected name `PORT`)
  - `PORT=abc` (`PORT`)
  - `PORT=0` (`PORT`)
  - `PORT=70000` (`PORT`)
  - `HOST=` (`HOST`)

  Each case asserts four things: `server.main([])` raises `SystemExit` with `.code == 2`; captured stderr contains `Invalid configuration: {NAME}=`; `uvicorn.run` was never called; and nothing was printed to stdout.
- [X] T013 [P] [US2] In `tests/unit/test_server.py`, add `test_whitespace_is_trimmed`: `.env` with `PORT= 8081 ` and `HOST= 0.0.0.0 ` records `port=8081`, `host="0.0.0.0"`.

### Implementation for User Story 2

- [X] T014 [US2] In `src/math_job_operator/server.py`, wrap the `load_settings(args)` call in `main` with `try/except pydantic.ValidationError as exc`. For each entry of `exc.errors()`:
  - The setting name is `".".join(str(p) for p in err["loc"])`.
  - The value is `err["input"]`. When the input is a `dict` (a required field is missing entirely), render it as `<missing>`.
  - Write `Invalid configuration: {name}={value}: {err["msg"]}` to `sys.stderr`.

  Then `raise SystemExit(2)` with no traceback and without calling `uvicorn.run` (research R4, contracts/start-command.md). Run `uv run pytest tests/unit/test_server.py` until T011 to T013 pass.
- [X] T015 [US2] Confirm that `tests/integration/test_server_startup.py::test_bind_failure_exits_without_fallback` (written in T007) passes, which covers the port-in-use case of FR-006 automatically (research R5). Then check the address-not-on-this-machine case by hand: `HOST=10.255.255.254 uv run math-job-operator; echo "exit=$?"` should print uvicorn's `error while attempting to bind on address ('10.255.255.254', <port>)` and a non-zero exit. Record the outcome in the commit message or PR description. No code change is expected; if uvicorn falls back or exits with 0, open a follow-up instead of patching uvicorn behavior.

**Checkpoint**: User Stories 1 and 2 both work independently. The defaults are kept, and bad configuration fails fast.

---

## Phase 5: User Story 3 - Override the configured port for a single run (Priority: P3)

**Goal**: An operator can override `.env` for one run, using either a process environment variable or a `--port`/`--host` flag. The flag wins over the environment.

**Independent Test**: With `PORT=8081` in `.env`, run `PORT=9090 uv run math-job-operator`, which listens on 9090. Then run `PORT=9090 uv run math-job-operator --port 9191`, which listens on 9191 (quickstart Scenario 5).

### Tests for User Story 3 ⚠️

- [X] T016 [P] [US3] In `tests/unit/test_server.py`, add `test_process_env_overrides_env_file`: `.env` has `PORT=8081` and `HOST=127.0.0.1`, plus `monkeypatch.setenv("PORT", "9090")` and `monkeypatch.setenv("HOST", "0.0.0.0")`. Calling `server.main([])` records `port=9090`, `host="0.0.0.0"`.
- [X] T017 [P] [US3] In `tests/unit/test_server.py`, add `test_cli_flags_override_env_and_env_file`: `.env` has `PORT=8081`, and the environment has `PORT=9090` and `HOST=0.0.0.0`. Calling `server.main(["--port", "9191", "--host", "localhost"])` records `port=9191`, `host="localhost"`.
- [X] T018 [P] [US3] In `tests/unit/test_server.py`, add `test_cli_port_out_of_range_refused`: `server.main(["--port", "70000"])` raises `SystemExit` with code 2, stderr contains `Invalid configuration: PORT=70000`, and `uvicorn.run` isn't called. The flag value goes through the same `Settings` validation (data-model.md: "`int`, from 1 to 65535 inclusive").

### Implementation for User Story 3

- [X] T019 [US3] Run `uv run pytest tests/unit/test_server.py`. If T016 to T018 fail, fix `load_settings` in `src/math_job_operator/server.py` so flags are passed only when not `None`, as `Settings` init keyword arguments (`HOST=`, `PORT=`). Don't merge sources by hand (research R3).

**Checkpoint**: All three user stories work independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 [P] Update `.env.example`:
  - Replace the `PORT` comment block with: `# HTTP listen port (1-65535). Defaults to 8000 if unset.` and `# Precedence: --port flag > PORT environment variable > this file > default.`
  - Keep `PORT=8000`.
  - Add, directly below it, `# Network address to bind. 127.0.0.1 = local only (default); 0.0.0.0 = all interfaces.` and `HOST=127.0.0.1`.
- [X] T021 [P] In `README.md`, add one short paragraph under the Configuration table covering three points: `HOST`/`PORT` follow the precedence `--host`/`--port` flag > environment variable > `.env` > default; an invalid value stops startup with exit status 2; and the old raw-`uvicorn` command doesn't read `.env` for the port (contracts/start-command.md § Compatibility).
- [X] T022 [P] In `specs/001-job-operator-api/quickstart.md`, replace the Setup line `uv run uvicorn math_job_operator.api.main:app --reload --port "${PORT:-8000}"` with `uv run math-job-operator --reload`. In the Validation Scenario `curl` commands, replace `http://localhost:8000` with `http://localhost:${PORT:-8000}` and add a note that the port is `PORT` from `.env`.
- [X] T023 Fix the misleading comment in the local `.env`, which says "8080 here" while the value is `8081`. This file is untracked, so it is a local fix only; tell the user rather than committing it.
- [X] T024 Run the quality gates. All three MUST pass:
  1. `uv run mypy src tests/unit/test_server.py tests/integration/test_server_startup.py`. The pre-existing test modules already have 7 known mypy errors outside this feature's scope, so the strict-typing gate covers `src` plus the two new test files only.
  2. `uv run pytest`.
  3. The domain/application coverage floor above 80% (Constitution X), which must be unchanged.

  Fix any strict-typing issues in `src/math_job_operator/server.py`, `src/math_job_operator/config.py`, or the two new test files.
- [X] T025 Run quickstart Scenarios 1 to 7 from `specs/002-port-from-env/quickstart.md` by hand, and record the outcome of each in the commit message or PR description.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: no dependency on T001. T002, T003 and T004 touch different files and can run in parallel. T001 can point at `math_job_operator.server:main` before the module exists, because console scripts resolve their target only when run.
- **Console script**: T007 and T009 (and every quickstart scenario) need T001 done and `uv sync` run after it, so that `math-job-operator` is installed.
- **User Stories (Phases 3 to 5)**: all depend on Phase 2. After that, the stories don't depend on each other's code, but they share `tests/unit/test_server.py` and `src/math_job_operator/server.py`, so running them one after another (P1 → P2 → P3) avoids edit conflicts.
- **Polish (Phase 6)**: after the stories you intend to ship. T020 to T022 can run alongside any story.

### Within each story

The tests (marked [P], all in one new file or appending separate functions) come first and must fail. Then the implementation, then the checkpoint.

### User story dependencies

- **US1 (P1)**: depends only on Phase 2.
- **US2 (P2)**: depends only on Phase 2. T014 adds error handling to `main` independently of US1.
- **US3 (P3)**: depends only on Phase 2. Flag plumbing already exists from T003, so US3 is mainly verification.

## Parallel Examples

```text
# Setup + Phase 2, all at once:
T001 pyproject.toml  |  T002 config.py  |  T003 server.py  |  T004 api/main.py docstring

# US1 tests together:
T005 + T006 (unit, test_server.py)  |  T007 (integration, test_server_startup.py)

# US2 tests together:
T011 | T012 | T013   (separate test functions in test_server.py)

# Polish docs together:
T020 .env.example | T021 README.md | T022 specs/001 quickstart
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. T001 (Setup), then T002 to T004 (Foundational).
2. T005 to T010 (US1).
3. **Stop and validate** with quickstart Scenarios 1 and 2. This alone fixes the reported bug.

### Incremental delivery

1. MVP (US1): the service starts on `.env` `PORT`/`HOST`.
2. Add US2: defaults stay at `127.0.0.1:8000`, and invalid values fail fast with exit status 2.
3. Add US3: one-off overrides through the environment or a flag.
4. Polish: docs, the feature 001 quickstart, quality gates, and the manual quickstart run.

## Notes

- [P] tasks touch different files, or append independent test functions with no dependency on unfinished tasks.
- Commit after each phase checkpoint.
- Never pass the FastAPI `app` object to `uvicorn.run`. Always pass the import string, or `--reload` breaks.
