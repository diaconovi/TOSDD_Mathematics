# Phase 1 Data Model: Math Job Operator API

## JSONValue (shared type alias)

Recursive alias used wherever a value must accept any JSON-representable shape without using
bare `Any` (see research.md §7):

```
JSONValue = str | int | float | bool | None | dict[str, "JSONValue"] | list["JSONValue"]
```

## Job

Represents a catalog entry — either an immutable (filesystem) or mutable (MongoDB) job.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Normalized: file extension stripped, lowercased (FR-007). Unique across immutable + mutable jobs, matched case-insensitively (FR-007a). Acts as the catalog key. |
| `description` | `str` | Free text; sourced from the job module's docstring or a declared `DESCRIPTION` constant. |
| `job_type` | `Literal["mutable", "immutable"]` | Determines whether `PUT /api/v1/jobs` may replace it (FR-008). |
| `return_type` | `str` | Declared type name of the value `run()` produces (Assumptions: static/declared, not a runtime value). |
| `entry_point` | callable reference (not serialized) | Loaded `run(arg: str) -> list` callable; validated at load time (FR-009). |

**Validation rules**:
- `name` MUST be unique among all jobs (case-insensitive) — enforced at upload/load time.
- `entry_point` MUST exist and match `def run(arg: str) -> list` (FR-009); jobs failing this
  check are never added to the catalog.
- An immutable job's `job_type` is fixed at "immutable" for its lifetime; only jobs loaded
  from MongoDB are ever "mutable".

**Lifecycle**: Immutable jobs are loaded once at startup and are read-only thereafter for the
life of the process. Mutable jobs are created or replaced by `PUT /api/v1/jobs` (FR-007,
FR-007a) and are re-fetched from MongoDB per run (no long-lived in-process cache of mutable
source, to keep instances stateless per Constitution Principle V).

## JobRunRequest

One entry inside the ordered list submitted to `POST /api/v1/jobs`.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Job name to run; matched case-insensitively against the catalog. |
| `args` | `list[dict[str, JSONValue]]` | Passed through as-is; JSON-encoded into a single string and handed to `run()` as `arg` (FR-002a) — the service does not interpret its contents. |
| `depends_on` | `str \| None` | Optional job name, must refer to another entry in the **same** request. |

**Validation rules**:
- `name` referring to a job absent from the catalog is not a request-level (HTTP) validation
  error — it produces a per-job "error" result instead (FR-006a); see JobRunResult.
- `depends_on`, if present, SHOULD reference another `name` present in the same request (see
  spec Edge Cases — behavior for a dangling `depends_on` is deferred to implementation-time
  edge-case handling, not blocking for this plan).

## JobRunResult

One entry in the response list from `POST /api/v1/jobs`, one per submitted `JobRunRequest`.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Echoes the request's job name. |
| `finished_at` | `datetime` (timezone-aware, per configured `TIME_ZONE`) | Set when the job's execution (or immediate rejection) completes. |
| `duration` | `float` (seconds) | Wall-clock time spent executing; `0` for jobs rejected before execution (unknown job, failed upstream). |
| `status` | `Literal["completed", "error"]` | Per FR-006, FR-005, FR-006a. |
| `output` | `JSONValue \| None` | Return value on success; error detail (string) on failure; `null` when the job has no return value. |

**State transitions** (per run request lifecycle):

```
submitted → (no dependency) → running → completed | error
submitted → (has dependency) → waiting-for-upstream
    waiting-for-upstream → (upstream completed) → running → completed | error
    waiting-for-upstream → (upstream error) → error   [never enters running; FR-005]
submitted → (name not in catalog) → error             [never enters running; FR-006a]
```

## SharedVariable

A named, globally available value, stored in `MONGO_VARIABLES_COLLECTION`.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Always normalized to uppercase on write and on lookup (FR-013). Unique key. |
| `value` | `JSONValue` | Any JSON type; stored and returned without coercion (FR-013a). |

**Validation rules**:
- Setting a variable whose (uppercased) name already exists overwrites its `value` in place
  (FR-012); it never creates a duplicate document.
- Every stored variable is exposed inside every job execution's context, keyed by its
  uppercase name (FR-014).

## ApprovedPackage

Read-only, sourced from the project's own dependency declaration (not user-editable at
runtime — FR-016), exposed via `GET /api/v1/jobs/dependencies`.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Package name available for job scripts to import (e.g. `requests`). Excludes the service's own framework dependencies (`fastapi`, `uvicorn`, `pydantic`), which are always disallowed regardless of this list (FR-015). |

## Entity relationships

```
Job (1) ──< JobRunRequest (submitted against, by name, per batch)
JobRunRequest (1) ──1 JobRunResult (produced per submitted request)
JobRunRequest (0..1) ──> JobRunRequest (depends_on another entry in the same batch)
SharedVariable (*) ──< every JobRunRequest's execution context (all variables always in scope)
ApprovedPackage (*) ── constrains which imports any Job's script may use
```
