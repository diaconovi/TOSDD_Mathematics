# Implementation Plan: Listening Port & Host from Environment Configuration

**Branch**: `002-port-from-env` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-port-from-env/spec.md`

## Summary

Today the service always listens on port 8000, because the documented start command lets the
shell expand `${PORT:-8000}` and the shell never reads `.env`. `Settings.PORT` is loaded but no
code ever reads it ([research R1](research.md#r1--root-cause-of-the-current-behavior)).

The fix adds a small launcher, `math_job_operator.server.main`, exposed as the console script
`math-job-operator`. It:

- builds `Settings` first, so the order is CLI flags > environment > `.env` > defaults;
- validates `PORT` (1–65535) and a new `HOST` setting (default `127.0.0.1`);
- reports the resolved address;
- hands the address to `uvicorn.run`, with optional `--reload`.

The standard start command becomes `uv run math-job-operator`.

## Technical Context

**Language/Version**: Python 3.14 (managed by `uv`)

**Primary Dependencies**: uvicorn 0.53 (server), pydantic 2.13 / pydantic-settings 2.15 (config),
FastAPI (unchanged), argparse from the standard library (launcher flags). No new dependencies.

**Storage**: N/A. The feature adds no persisted data.

**Testing**: pytest. Unit tests monkeypatch `uvicorn.run`. A subprocess smoke test reuses the
existing MongoDB/Redis integration prerequisites.

**Target Platform**: Linux server, local dev, and containers.

**Project Type**: Web service (single project, `src/` layout).

**Performance Goals**: N/A. Settings are resolved once at startup, with negligible cost.

**Constraints**:
- `uv run` launch is mandatory (Principle II).
- Strict mypy must pass.
- The `app` import path `math_job_operator.api.main:app` must stay unchanged for existing
  integrations.

**Scale/Scope**: One new module of about 60 lines, two `Settings` field changes, one
`pyproject.toml` entry, documentation updates, and two test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|---|---|---|
| I | Strict Static Typing | PASS | The launcher is fully annotated (`main(argv: Sequence[str] \| None = None) -> None`). Field constraints use `Annotated`. No `Any`. |
| II | uv-Managed Toolchain | PASS | The start command becomes `uv run math-job-operator`, a console script installed by `uv sync`. No new dependencies; no pip. |
| III | Focused, Modular Design | PASS | `server.py` has one responsibility (process bootstrapping), separate from the app factory in `api/main.py`. Its public function has a docstring example. |
| IV | API-First & RESTful | N/A | No endpoints change. |
| V | Statelessness | PASS | Host and port are read-only process configuration, not cross-request state. |
| VI | Service Boundary Isolation | N/A | No cross-service interaction. |
| VII | Dependency Inversion | PASS | The launcher is the outermost composition root. It depends on `config` and on uvicorn; no inner layer imports it. |
| VIII | Standardized Error Responses | N/A | Startup configuration errors happen before any HTTP API exists. They go to stderr with exit status 2, as defined in [contracts/start-command.md](contracts/start-command.md). |
| IX | Client Packages | N/A | No inter-service calls. |
| X | Testing Discipline | PASS | No new repository or HTTP client, so no new contract tests are required. Launcher logic gets full unit tests, plus one end-to-end smoke test. The domain/application coverage floor is unaffected. |

**Post-design re-check (after Phase 1)**: all gates still PASS. The design adds no violations, so
Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-port-from-env/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── start-command.md # Phase 1 output: the start-command interface
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/math_job_operator/
├── config.py            # MODIFY: constrain PORT to 1–65535; add HOST (default 127.0.0.1)
├── server.py            # NEW: argparse flags → Settings → startup log → uvicorn.run(...)
└── api/main.py          # MODIFY (docstring only): it is the app factory; the entrypoint now lives in server.py

pyproject.toml           # MODIFY: [project.scripts] math-job-operator = "math_job_operator.server:main"
.env.example             # MODIFY: document HOST, PORT, defaults, precedence
README.md                # MODIFY: start command → `uv run math-job-operator [--reload]`; config table adds HOST
specs/001-job-operator-api/quickstart.md   # MODIFY: Setup step uses the new start command

tests/
├── unit/test_server.py                    # NEW: precedence, defaults, validation errors, --reload passthrough
└── integration/test_server_startup.py     # NEW: subprocess start on a free PORT; GET /api/v1/jobs answers there
```

**Structure Decision**: Keep the existing single-project `src/` layout. The launcher goes at the
package root, next to `config.py` and `logging_setup.py`, because it is cross-cutting bootstrap
code and doesn't belong to the `api`, `application`, `domain` or `infrastructure` layers.

## Complexity Tracking

No constitution violations. Nothing to justify.
