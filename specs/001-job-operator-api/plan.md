# Implementation Plan: Math Job Operator API

**Branch**: `001-job-operator-api` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-job-operator-api/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A FastAPI microservice that catalogs and runs Python "jobs" (data-processing scripts) against
Capital.com market/instrument data on demand. Consumers list jobs and approved packages,
submit batches of job runs (with optional same-batch dependencies resolved via an `upstream`
variable), upload/replace mutable jobs, and manage shared variables that every job run can
read. Jobs are either filesystem-backed immutable scripts loaded at startup or MongoDB-backed
mutable scripts; shared variables and mutable job source live in MongoDB; an asyncio-based
scheduler (signaled through Redis for cross-worker safety) resolves the per-request dependency
graph and executes independent jobs concurrently.

## Technical Context

**Language/Version**: Python 3.14 (per constitution Principle II)

**Primary Dependencies**: FastAPI + uvicorn (API/server), Pydantic (validation), pymongo
(MongoDB driver), redis-py (dependency-signaling pub/sub), requests, `to_session_manager`
(git dependency, authentication client), `to_collector_client` (git dependency, market/
instrument/price client)

**Storage**: MongoDB (`MONGO_JOBS_COLLECTION` for mutable job source,
`MONGO_VARIABLES_COLLECTION` for shared variables) + local filesystem directory for immutable
job scripts (read-only, loaded at startup)

**Testing**: pytest + pytest-asyncio (unit + integration), httpx `AsyncClient` against the
FastAPI app (integration), a real/ephemeral MongoDB instance for repository contract tests, a
real Redis instance for signal-bus contract tests. `to_session_manager`/`to_collector_client`
are consumed directly by job scripts (not service-owned wrappers), so no service-level
contract tests are needed for them in this feature.

**Target Platform**: Linux server, containerized microservice (uvicorn behind a process
manager)

**Project Type**: Single web-service (backend API only, no frontend)

**Performance Goals**: Not specified by the feature; no explicit latency/throughput SLA — the
run endpoint blocks until every submitted job in the batch finishes, so end-to-end time is
dominated by job logic itself, not framework overhead

**Constraints**: Job scripts MUST NOT import the service's own framework dependencies
(`fastapi`, `uvicorn`, `pydantic`) even though those packages are present in the process
(FR-015); adding a job dependency requires a project-level change + restart, never a runtime
action (FR-016); each service instance MUST remain stateless (Constitution Principle V) — all
mutable data (job source, variables) lives in MongoDB, never local process memory

**Scale/Scope**: Not specified by the feature; internal trading-ops tool, single microservice
exposing 6 endpoints — scope explicitly excludes auth, timeouts/cancellation, sandboxing, and
concurrency limits (see spec's Out of Scope section)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Strict Static Typing & Modern Python Syntax | PASS | All Pydantic models and domain code use explicit type annotations under strict mypy/Pyright. A polymorphic shared-variable value / job output is modeled as an explicit recursive `JSONValue` type alias (`str \| int \| float \| bool \| None \| dict[str, JSONValue] \| list[JSONValue]`) rather than bare `typing.Any`, so the "no `Any` to silence an error" rule is respected while still representing arbitrary JSON (see data-model.md). |
| II | uv-Managed Toolchain | PASS | Project uses `uv` for all dependency/version management (`pyproject.toml` + `uv.lock`), Python 3.14 pinned via `uv python pin`, and the app is always started with `uv run uvicorn ...`. |
| III | Focused, Modular Library Design | PASS | Layered into domain/application/infrastructure/api modules, each with a single responsibility; public use-case functions carry a short docstring usage example. |
| IV | API-First & RESTful Conventions | PASS (with note) | All 6 endpoints are plural, resource-oriented (`/api/v1/jobs`, `/api/v1/variables`). `PUT /api/v1/jobs` (upload, name derived from the file rather than a URL path segment) is a collection-level PUT rather than a per-resource `PUT /api/v1/jobs/{name}`; this shape is fixed by the approved feature spec's functional requirements (FR-007), not a free implementation choice, so it is documented here rather than reopened. |
| V | Statelessness & Distributed State | PASS (with note) | Mutable job source and shared variables live in MongoDB; any instance can serve any request. Immutable job scripts live on a local filesystem directory loaded at startup — these are read-only, deployed-with-the-service artifacts (equivalent to code, not session/request state), identical across every instance, so they don't violate instance interchangeability. Redis is used as a distributed signal bus for upstream/dependent job coordination (never in-process-only state), consistent with "distributed cache" guidance. |
| VI | Service Boundary Isolation | PASS | No direct database access to Session Manager or Collector; all cross-service calls go through their client packages. |
| VII | Dependency Inversion | PASS | Domain/application layers depend on abstract `JobRepository`/`VariableRepository` interfaces; MongoDB and filesystem implementations are injected in the infrastructure layer. This applies to the service's own core — user-authored job scripts are the executed payload, not part of the service's domain layer, so FR-015's allowance for jobs to import approved third-party/client packages directly does not conflict with this principle. |
| VIII | Standardized Error Responses | PASS | All request-level failures (invalid upload, immutable-job conflict, malformed payload) return RFC 7807 Problem Details via a shared FastAPI exception handler. Per-job "error" status inside a `POST /api/v1/jobs` result (FR-005/FR-006/FR-006a) is a business-level outcome inside a 200 response, not an HTTP-level error, and is intentionally distinct. |
| IX | Inter-Service Communication via Client Packages | PASS | `to_session_manager` and `to_collector_client` are the only sanctioned ways to reach those services; the example job uses `to_collector_client` for the "AWXSG" epic query. |
| X | Testing Discipline | PASS | Contract/integration tests planned for both MongoDB repositories and both external HTTP clients; unit tests planned for domain entities and application use cases (execution engine, dependency resolution, variable normalization, entry-point/import validation) targeting >80% coverage. |

No unresolved violations — Complexity Tracking table is omitted.

## Project Structure

### Documentation (this feature)

```text
specs/001-job-operator-api/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── jobs.md
│   └── variables.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/math_job_operator/
├── domain/
│   ├── entities.py          # Job, JobRunRequest, JobRunResult, SharedVariable, JSONValue
│   └── repositories.py      # Abstract JobRepository / VariableRepository interfaces
├── application/
│   ├── job_catalog.py       # List-jobs, list-dependencies use cases
│   ├── job_execution.py     # Dependency-graph scheduler + run-jobs use case
│   ├── job_upload.py        # Upload/replace-job use case (validation, collision rules)
│   └── variable_management.py  # List/set shared-variables use case
├── infrastructure/
│   ├── mongo/
│   │   ├── client.py            # pymongo connection/session setup
│   │   ├── job_repository.py    # MongoJobRepository (mutable jobs)
│   │   ├── variable_repository.py  # MongoVariableRepository
│   │   └── variable_seed.py        # One-time default-variable seeding
│   ├── filesystem/
│   │   └── immutable_job_loader.py  # Loads + indexes immutable jobs at startup
│   ├── job_runtime/
│   │   ├── loader.py           # Dynamic module loading (importlib / compile+exec)
│   │   ├── import_guard.py     # AST-based framework-import rejection (FR-015)
│   │   └── entry_point.py      # `run(arg: str) -> list` signature validation (FR-009)
│   └── signaling/
│       └── redis_signal_bus.py # Upstream-completion pub/sub for the scheduler
├── api/
│   ├── main.py                  # FastAPI app factory / uvicorn entrypoint
│   ├── v1/
│   │   ├── jobs.py               # GET/POST/PUT /api/v1/jobs, GET .../dependencies, .../variables
│   │   └── variables.py          # PUT /api/v1/variables
│   └── schemas/
│       ├── job_schemas.py        # JobSummary, JobRunRequest/Result Pydantic models
│       ├── variable_schemas.py   # VariableIn/Out Pydantic models
│       └── errors.py             # RFC 7807 ProblemDetail model + exception handlers
├── config.py                    # pydantic-settings reading .env (LOGGING, PORT, TIME_ZONE, MONGO_*)
└── logging_setup.py              # Configures structured logging per LOGGING level

jobs/
└── immutable/
    └── awxsg_example.py         # Example deliverable job (collector query + default variable)

tests/
├── contract/
│   ├── test_mongo_job_repository.py
│   ├── test_mongo_variable_repository.py
│   └── test_redis_signal_bus.py
├── integration/
│   ├── test_jobs_api.py
│   └── test_variables_api.py
└── unit/
    ├── test_job_execution_use_case.py
    ├── test_variable_normalization.py
    ├── test_import_guard.py
    └── test_entry_point_validation.py

README.md
pyproject.toml
.env.example
```

**Structure Decision**: Single project (Option 1), organized as a layered
domain/application/infrastructure/api package (`src/math_job_operator/`) to satisfy
Constitution Principle VII (Dependency Inversion). A top-level `jobs/immutable/` directory
holds the filesystem-backed immutable job scripts (separate from the service's own source so
FR-015's import restriction can be enforced uniformly on anything loaded from either that
directory or MongoDB).

## Complexity Tracking

*No unresolved Constitution Check violations — this section intentionally left empty.*
