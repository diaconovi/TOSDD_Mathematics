---

description: "Task list for Math Job Operator API implementation"
---

# Tasks: Math Job Operator API

**Input**: Design documents from `/specs/001-job-operator-api/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and **mandatory**, not optional — Constitution Principle X requires
contract/integration tests for every infrastructure repository and external client, and
>80% unit coverage for domain entities and application use cases.

**Organization**: Tasks are grouped by user story (from spec.md, in priority order P1 → P2 →
P2 → P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths follow `src/math_job_operator/...` per plan.md's Project Structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization per plan.md

- [X] T001 Create the project skeleton per plan.md's Project Structure: `src/math_job_operator/{domain,application,infrastructure,api}/`, `jobs/immutable/`, `tests/{contract,integration,unit}/`, each with an `__init__.py`
- [X] T002 Initialize the `uv`-managed project in `pyproject.toml`: pin Python 3.14 (`uv python pin 3.14`), add `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `pymongo`, `redis`, `requests`, `to_session_manager = { git = "ssh://git@github.com/diaconovi/Trade_Ops_Library.git", subdirectory = "packages/to_session_manager" }`, `to_collector_client = { git = "ssh://git@github.com/diaconovi/Trade_Ops_Library.git", subdirectory = "packages/to_collector" }`, and dev dependencies `pytest`, `pytest-asyncio`, `httpx`, `mypy`, then `uv sync`
- [X] T003 [P] Configure strict static typing in `pyproject.toml` (`[tool.mypy]` with `strict = true`) per Constitution Principle I
- [X] T004 [P] Create `.env.example` documenting `LOGGING`, `PORT` (default `8000`), `TIME_ZONE`, `MONGO_URL`, `MONGO_PORT`, `MONGO_ACCOUNT_DB`, `MONGO_VARIABLES_COLLECTION`, `MONGO_JOBS_COLLECTION`, and `REDIS_URL`
- [X] T005 [P] Configure structured logging in `src/math_job_operator/config.py`'s companion `src/math_job_operator/logging_setup.py`, honoring the configured `LOGGING` level (INFO/DEBUG/WARNING)

**Checkpoint**: Project scaffolding and toolchain ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure every user story depends on — repositories, error handling,
job-loading/validation primitives, and dependency signaling.

**⚠️ CRITICAL**: No user story task may start until this phase is complete.

- [X] T006 [P] Define the `JSONValue` recursive type alias and domain entities `Job`, `JobRunRequest`, `JobRunResult`, `SharedVariable`, `ApprovedPackage` in `src/math_job_operator/domain/entities.py`, matching the fields and validation rules in data-model.md (e.g. `Job.name` normalized lowercase/extension-stripped and unique case-insensitively; `SharedVariable.value: JSONValue`; `JobRunResult.status: Literal["completed", "error"]`)
- [X] T007 [P] Define abstract `JobRepository` (get-by-name, list-all, upsert-mutable) and `VariableRepository` (get-all, upsert-many) interfaces in `src/math_job_operator/domain/repositories.py` per Constitution Principle VII (Dependency Inversion)
- [X] T008 Implement `Settings` (pydantic-settings) in `src/math_job_operator/config.py` loading `LOGGING`, `PORT`, `TIME_ZONE`, `MONGO_URL`, `MONGO_PORT`, `MONGO_ACCOUNT_DB`, `MONGO_VARIABLES_COLLECTION`, `MONGO_JOBS_COLLECTION`, `REDIS_URL` from `.env`, with `PORT` defaulting to `8000` per FR-019
- [X] T009 Implement the pymongo connection/client factory in `src/math_job_operator/infrastructure/mongo/client.py` using `Settings.MONGO_URL`/`MONGO_PORT`/`MONGO_ACCOUNT_DB`
- [X] T010 [P] Implement `MongoJobRepository` in `src/math_job_operator/infrastructure/mongo/job_repository.py`, storing/reading mutable job source keyed by the normalized (lowercase, no-extension) name in `MONGO_JOBS_COLLECTION`, implementing `JobRepository`
- [X] T011 [P] Implement `MongoVariableRepository` in `src/math_job_operator/infrastructure/mongo/variable_repository.py`, storing `{name: <UPPER_STR>, value: <JSONValue>}` documents in `MONGO_VARIABLES_COLLECTION`, implementing `VariableRepository`
- [X] T012 [P] Contract test for `MongoJobRepository` against a real MongoDB instance in `tests/contract/test_mongo_job_repository.py` (Constitution Principle X — no mocks for infrastructure repositories)
- [X] T013 [P] Contract test for `MongoVariableRepository` against a real MongoDB instance in `tests/contract/test_mongo_variable_repository.py` (Constitution Principle X — no mocks)
- [X] T014 Implement one-time seed-variable insertion in `src/math_job_operator/infrastructure/mongo/variable_seed.py`: insert `BASE_ENDPOINT_URL`, `DEMO_ENDPOINT_URL`, `SESSION_MANAGER_URL`, `SESSION_MANAGER_INSECURE`, `REDIS_URL` into `MONGO_VARIABLES_COLLECTION` only if each name doesn't already exist
- [X] T015 [P] Implement the RFC 7807 `ProblemDetail` model and shared FastAPI exception handlers in `src/math_job_operator/api/schemas/errors.py` per Constitution Principle VIII
- [X] T016 Implement the FastAPI app factory and uvicorn entrypoint in `src/math_job_operator/api/main.py`, wiring `Settings`, the Mongo client, the seed step (T014), logging (T005), and the exception handlers (T015)
- [X] T017 [P] Implement the AST-based import guard in `src/math_job_operator/infrastructure/job_runtime/import_guard.py`: parse a job script's `ast.Import`/`ast.ImportFrom` nodes and reject any import of `fastapi`, `uvicorn`, or `pydantic` (or their submodules), per FR-015
- [X] T018 [P] Implement the entry-point signature validator in `src/math_job_operator/infrastructure/job_runtime/entry_point.py`: using `inspect.signature`/`typing.get_type_hints`, confirm the loaded module exposes exactly `def run(arg: str) -> list`, per FR-009
- [X] T019 [P] Unit tests for the import guard (accepts approved imports, rejects `fastapi`/`uvicorn`/`pydantic` in various import forms) in `tests/unit/test_import_guard.py`
- [X] T020 [P] Unit tests for the entry-point validator (accepts exact `run(arg: str) -> list`, rejects missing/mismatched signatures) in `tests/unit/test_entry_point_validation.py`
- [X] T021 Implement the dynamic job loader in `src/math_job_operator/infrastructure/job_runtime/loader.py`: load an immutable job via `importlib.util.spec_from_file_location`/`module_from_spec`, or compile mutable job source (from `MongoJobRepository`) into a fresh `types.ModuleType` namespace; apply the import guard (T017) and entry-point validator (T018) to every loaded module before it is added to the catalog
- [X] T022 Implement the immutable-job filesystem loader in `src/math_job_operator/infrastructure/filesystem/immutable_job_loader.py`: scan the immutable jobs directory at startup, build the normalized (lowercase, extension-stripped) catalog index via the loader (T021), per FR-007a
- [X] T023 [P] Implement the Redis-backed signal bus in `src/math_job_operator/infrastructure/signaling/redis_signal_bus.py`: publish/subscribe per-batch, per-job-name completion signals (job name → status), per research.md §2
- [X] T024 [P] Contract test for `RedisSignalBus` against a real Redis instance in `tests/contract/test_redis_signal_bus.py` (Constitution Principle X)

**Checkpoint**: Foundation ready — user story phases below can now begin.

---

## Phase 3: User Story 1 - Run Jobs and Retrieve Results (Priority: P1) 🎯 MVP

**Goal**: An API Consumer submits a batch of job runs, with optional same-batch dependencies,
and gets back a per-job result summary once every job finishes.

**Independent Test**: Submit a single no-dependency job and confirm a complete result
(name/finish-timestamp/duration/status/output); submit two jobs where one depends on the
other and confirm the dependent job saw the upstream's return value as `upstream`.

### Tests for User Story 1

- [X] T025 [P] [US1] Contract test for `POST /api/v1/jobs` request/response shape in `tests/contract/test_jobs_post_contract.py` per contracts/jobs.md
- [X] T026 [P] [US1] Integration test: run a single independent job end-to-end (finish timestamp, duration, status "completed", output) in `tests/integration/test_jobs_api.py::test_run_single_job`
- [X] T027 [P] [US1] Integration test: a dependent job only starts after its upstream finishes and receives the upstream's return value as `upstream` (FR-003, FR-004) in `tests/integration/test_jobs_api.py::test_run_dependent_job`
- [X] T028 [P] [US1] Integration test: a run request naming a job absent from the catalog reports that entry as status "error" without affecting the rest of the batch (FR-006a) in `tests/integration/test_jobs_api.py::test_unknown_job_name`
- [X] T029 [P] [US1] Integration test: when an upstream job ends in "error", its dependent is never executed and is itself reported as "error" (FR-005) in `tests/integration/test_jobs_api.py::test_upstream_failure_propagation`
- [X] T029a [P] [US1] Integration test: a `depends_on` naming a job absent from the batch is reported as status "error" without executing it (FR-006b) in `tests/integration/test_jobs_api.py::test_dangling_dependency`
- [X] T029b [P] [US1] Integration test: a job returning a non-JSON-serializable value is reported as status "error" with a serialization-failure detail (FR-006c) in `tests/integration/test_jobs_api.py::test_non_serializable_output`
- [X] T030 [P] [US1] Integration test: a job whose `run()` returns nothing is reported as status "completed" with `output: null` (FR-006) in `tests/integration/test_jobs_api.py::test_job_with_no_return_value`

### Implementation for User Story 1

- [X] T031 [P] [US1] Define `JobRunRequest`/`JobRunResult` Pydantic schemas in `src/math_job_operator/api/schemas/job_schemas.py`: `JobRunRequest(name: str, args: list[dict[str, JSONValue]], depends_on: str | None)`, `JobRunResult(name: str, finished_at: datetime, duration: float, status: Literal["completed", "error"], output: JSONValue | None)`, per contracts/jobs.md
- [X] T032 [US1] Implement the dependency-graph builder in `src/math_job_operator/application/job_execution.py`: resolve every requested job name against the combined catalog (immutable index + `MongoJobRepository`, T010/T022); names with no match immediately become a `status: "error"` result ("job not found") excluded from the graph (FR-006a); entries whose `depends_on` names a job absent from the batch immediately become a `status: "error"` result ("dependency not found") excluded from the graph (FR-006b); remaining entries are split into independent jobs (scheduled immediately as asyncio tasks) and dependent jobs (deferred until their upstream's `RedisSignalBus` completion signal, T023)
- [X] T033 [US1] Implement per-job invocation in `src/math_job_operator/application/job_execution.py`: JSON-encode the job's `args` list into a single string and pass it as `arg` to the loaded `run()` (FR-002a); on upstream success, inject the upstream's return value into the dependent job's execution context as `upstream` (FR-004); when the declared upstream ended in "error", mark the dependent as `status: "error"` without invoking `run()` (FR-005); when a `depends_on` names a job absent from the batch, mark that entry `status: "error"` without executing it (FR-006b); if a job's return value cannot be JSON-serialized, catch the failure and mark the result `status: "error"` with a serialization-failure detail (FR-006c); also inject every stored `SharedVariable` (via `VariableRepository`, T011) into the job's execution context by its uppercase name (FR-014); capture start/end time, duration, and status/output into a `JobRunResult`, rendering `finished_at` in `Settings.TIME_ZONE` (FR-006, FR-020)
- [X] T034 [US1] Implement `POST /api/v1/jobs` in `src/math_job_operator/api/v1/jobs.py`, accepting `list[JobRunRequest]` and returning `list[JobRunResult]` in the same order, wired to the job_execution use case (T032/T033)

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Discover Available Jobs and Approved Packages (Priority: P2)

**Goal**: An API Consumer can list every job in the catalog and the packages approved for job
scripts to use, before submitting a run request.

**Independent Test**: Call the job-catalog and dependency-list endpoints independently of
running any job, and confirm the data matches what's actually loaded/configured.

### Tests for User Story 2

- [X] T035 [P] [US2] Contract test for `GET /api/v1/jobs` and `GET /api/v1/jobs/dependencies` in `tests/contract/test_jobs_get_contract.py` per contracts/jobs.md
- [X] T036 [P] [US2] Integration test: the catalog lists both immutable and mutable jobs with name/description/type/return_type (FR-001) in `tests/integration/test_jobs_api.py::test_list_jobs`
- [X] T037 [P] [US2] Integration test: the dependency list returns the approved package set and never includes `fastapi`/`uvicorn`/`pydantic` (FR-010, FR-015) in `tests/integration/test_jobs_api.py::test_list_dependencies`

### Implementation for User Story 2

- [X] T038 [P] [US2] Define the `JobSummary` Pydantic schema (`name: str`, `description: str`, `job_type: Literal["mutable", "immutable"]`, `return_type: str`) in `src/math_job_operator/api/schemas/job_schemas.py`
- [X] T039 [US2] Implement the list-jobs and list-approved-packages use cases in `src/math_job_operator/application/job_catalog.py`: combine the immutable filesystem index (T022) with `MongoJobRepository` (T010) entries into one catalog; expose a static `APPROVED_JOB_PACKAGES` list (`requests`, `pymongo`, `to_session_manager`, `to_collector_client`), always excluding `fastapi`/`uvicorn`/`pydantic` (FR-015)
- [X] T040 [US2] Implement `GET /api/v1/jobs` and `GET /api/v1/jobs/dependencies` in `src/math_job_operator/api/v1/jobs.py`, wired to the job_catalog use case (T039)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Upload or Replace a Mutable Job (Priority: P2)

**Goal**: A Job Author uploads a new job script, or replaces an existing mutable job's
script, making it available to run and appear in the catalog.

**Independent Test**: Upload a valid script, confirm it appears in the catalog and can be
run; attempt to overwrite an immutable job and confirm it's rejected; attempt to upload a
script without a valid entry point and confirm it's rejected.

### Tests for User Story 3

- [X] T041 [P] [US3] Contract test for `PUT /api/v1/jobs` (200 success, 409 immutable conflict, 422 invalid entry point) in `tests/contract/test_jobs_put_contract.py` per contracts/jobs.md
- [X] T042 [P] [US3] Integration test: uploading a new script makes it appear in the catalog as "mutable" and runnable in `tests/integration/test_jobs_api.py::test_upload_new_job`
- [X] T043 [P] [US3] Integration test: uploading over an existing immutable job's derived name is rejected with 409 and the immutable job is left unchanged (FR-008) in `tests/integration/test_jobs_api.py::test_upload_rejects_immutable_overwrite`
- [X] T044 [P] [US3] Integration test: uploading a script without a valid `run(arg: str) -> list` entry point is rejected with 422 (FR-009) in `tests/integration/test_jobs_api.py::test_upload_rejects_invalid_entry_point`

### Implementation for User Story 3

- [X] T045 [US3] Implement the upload-job use case in `src/math_job_operator/application/job_upload.py`: derive the job name by stripping the file extension and lowercasing the remainder (FR-007); check the normalized name case-insensitively against the immutable index (reject with a conflict if matched, FR-008) and against `MongoJobRepository` (replace if matched, FR-007a); validate the script via the import guard (T017) and entry-point validator (T018) before persisting (FR-009)
- [X] T046 [US3] Implement `PUT /api/v1/jobs` as a `multipart/form-data` file-upload endpoint in `src/math_job_operator/api/v1/jobs.py`, wired to the job_upload use case (T045), returning 200/409/422 per contracts/jobs.md
- [X] T047 [P] [US3] Unit tests for the job_upload use case (name normalization, immutable-collision rejection, mutable replacement, entry-point validation failure) in `tests/unit/test_job_upload_use_case.py`

**Checkpoint**: User Stories 1, 2, and 3 all work independently.

---

## Phase 6: User Story 4 - View and Update Shared Variables (Priority: P3)

**Goal**: An API Consumer can inspect and update the shared variables available to every job
run.

**Independent Test**: Set a variable, confirm it's listed in uppercase form, and confirm a
job run can read it.

### Tests for User Story 4

- [X] T048 [P] [US4] Contract test for `PUT /api/v1/variables` and `GET /api/v1/jobs/variables` in `tests/contract/test_variables_contract.py` per contracts/variables.md and contracts/jobs.md
- [X] T049 [P] [US4] Integration test: setting a variable in any letter case lists it in uppercase form (FR-013) in `tests/integration/test_variables_api.py::test_set_and_list_variable`
- [X] T050 [P] [US4] Integration test: setting an existing variable overwrites its value rather than duplicating it (FR-012) in `tests/integration/test_variables_api.py::test_overwrite_variable`
- [X] T051 [P] [US4] Integration test: variable values accept arbitrary JSON types (string/number/bool/object/array) without coercion (FR-013a) in `tests/integration/test_variables_api.py::test_variable_arbitrary_json_types`
- [X] T051a [P] [US4] Integration test: submitting the same variable name twice with different letter case in one request stores the last occurrence's value (FR-012) in `tests/integration/test_variables_api.py::test_duplicate_name_last_write_wins`

### Implementation for User Story 4

- [X] T052 [P] [US4] Define `VariableIn`/`VariableOut` Pydantic schemas (`name: str`, `value: JSONValue`) in `src/math_job_operator/api/schemas/variable_schemas.py`
- [X] T053 [US4] Implement the list/upsert-variables use case in `src/math_job_operator/application/variable_management.py`: normalize every name to uppercase (FR-013), upsert semantics — create if absent, overwrite value if present (FR-012), pass `value` through untouched as `JSONValue` (FR-013a), via `VariableRepository` (T011)
- [X] T054 [US4] Implement `PUT /api/v1/variables` in `src/math_job_operator/api/v1/variables.py` and `GET /api/v1/jobs/variables` in `src/math_job_operator/api/v1/jobs.py`, both wired to the variable_management use case (T053)
- [X] T055 [P] [US4] Unit tests for the variable normalization/upsert logic in `tests/unit/test_variable_normalization.py`

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Feature deliverables and quality gates that span multiple user stories.

- [X] T056 [P] Create the example immutable job in `jobs/immutable/awxsg_example.py`: decode its `arg` string via `json.loads`, call `to_collector_client` for epic `"AWXSG"`, and read at least one default shared variable from its execution context (feature deliverable)
- [X] T057 [P] Write `README.md` documenting setup, `.env` configuration, and usage of every endpoint (contracts/jobs.md, contracts/variables.md), including a note on the `arg` JSON-encoding contract (FR-002a) for job authors (feature deliverable)
- [X] T058 Add structured per-job execution logging (start time, end time, duration, status) in `src/math_job_operator/application/job_execution.py`, satisfying FR-017 traceability via logs only (no queryable history endpoint, per clarified scope)
- [X] T059 Run every quickstart.md validation scenario end-to-end against a live dev environment (Session Manager at `http://localhost:8000`, Collector at `http://localhost:8001`) and confirm expected results
- [X] T060 [P] Verify unit test coverage for `src/math_job_operator/domain/` and `src/math_job_operator/application/` exceeds 80% via `uv run pytest --cov=src/math_job_operator/domain --cov=src/math_job_operator/application --cov-report=term-missing` (Constitution Principle X)
- [X] T061 [P] Run strict type checking with zero errors via `uv run mypy --strict src/` (Constitution Principle I / Technology Stack Constraints)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends only on Foundational.
- **User Story 2 (Phase 4)**: Depends only on Foundational (independent of US1).
- **User Story 3 (Phase 5)**: Depends only on Foundational (independent of US1/US2).
- **User Story 4 (Phase 6)**: Depends only on Foundational (independent of US1/US2/US3). Note:
  US1's job-execution context reads shared variables directly from `VariableRepository`
  (Foundational, T011) — it does **not** depend on US4's endpoints, so US1 and US4 remain
  independently deliverable in either order.
- **Polish (Phase 7)**: Depends on the user stories it touches (T056 needs US1's run path and
  US2's catalog; T057 documents all endpoints; T059 exercises all four stories).

### Within Each User Story

- Tests are written first and MUST fail before implementation begins.
- Schemas before use cases; use cases before endpoints.
- Story complete and checkpointed before moving to the next priority.

### Parallel Opportunities

- All Setup tasks marked [P] (T003–T005) can run together once T001–T002 land.
- Foundational tasks marked [P] (T006, T007, T010–T013, T015, T017–T020, T023–T024) can run
  in parallel within Phase 2, respecting the intra-phase notes above (e.g. T010/T011 need T007
  and T009 first; T021 needs T017/T018 first; T022 needs T021 first).
- Once Foundational completes, User Stories 1–4 can be built in parallel by different
  developers, since none of their implementation tasks depend on another story's endpoints.
- All test tasks within a story marked [P] can run in parallel with each other.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /api/v1/jobs in tests/contract/test_jobs_post_contract.py"
Task: "Integration test: run a single independent job in tests/integration/test_jobs_api.py::test_run_single_job"
Task: "Integration test: dependent job in tests/integration/test_jobs_api.py::test_run_dependent_job"
Task: "Integration test: unknown job name in tests/integration/test_jobs_api.py::test_unknown_job_name"
Task: "Integration test: upstream failure propagation in tests/integration/test_jobs_api.py::test_upstream_failure_propagation"
Task: "Integration test: job with no return value in tests/integration/test_jobs_api.py::test_job_with_no_return_value"

# Then implement (schemas first, in parallel with nothing else since job_execution depends on it):
Task: "Define JobRunRequest/JobRunResult schemas in src/math_job_operator/api/schemas/job_schemas.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks everything else).
3. Complete Phase 3: User Story 1 (run jobs, resolve dependencies, return results).
4. **STOP and VALIDATE**: run T025–T030 and quickstart Scenario 2/3 manually.
5. Deploy/demo the MVP: consumers can already run jobs even before catalog browsing, uploads,
   or variable management exist (a job to run would need to be seeded directly into the
   immutable directory or Mongo for this early demo).

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate independently → MVP demo.
3. Add User Story 2 → validate independently → catalog browsing available.
4. Add User Story 3 → validate independently → jobs can be authored without a redeploy.
5. Add User Story 4 → validate independently → shared configuration available to jobs.
6. Phase 7 Polish → ship the example job, README, logging, and quality-gate verification.

### Parallel Team Strategy

With multiple developers, once Foundational is complete: Developer A takes US1, Developer B
takes US2, Developer C takes US3, Developer D takes US4 — all four integrate independently
since none of their implementation tasks depend on another story's endpoints.

---

## Notes

- [P] tasks touch different files with no unmet dependencies.
- [Story] labels map every user-story-phase task back to spec.md for traceability.
- Tests are mandatory here (Constitution Principle X), not optional — write them first and
  confirm they fail before implementing.
- Commit after each task or logical group; stop at any checkpoint to validate a story alone.
- The upstream-failure policy (FR-005) is fixed by the spec's clarification — no configurable
  branch point is needed (see plan.md's Completion Report note).
