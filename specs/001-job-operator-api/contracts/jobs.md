# Contract: `/api/v1/jobs*` endpoints

All error responses (any 4xx/5xx) use RFC 7807 Problem Details
(`application/problem+json`): `{type, title, status, detail, instance}` (Constitution
Principle VIII). Per-job business failures inside a 200 response (unknown job name, upstream
failure, job raised an exception) are **not** Problem Details — they are `JobRunResult` entries
with `status: "error"` (FR-005, FR-006, FR-006a).

## `GET /api/v1/jobs`

List every available job (FR-001).

**Response** `200 OK` — `list[JobSummary]`

```jsonc
[
  {
    "name": "awxsg_example",
    "description": "Fetches AWXSG market data and reads a default variable.",
    "job_type": "immutable",   // "mutable" | "immutable"
    "return_type": "list"
  }
]
```

## `POST /api/v1/jobs`

Run an ordered batch of jobs, resolving same-batch dependencies (FR-002–FR-006a).

**Request** — `list[JobRunRequest]`

```jsonc
[
  { "name": "fetch_prices", "args": [{"epic": "AWXSG"}], "depends_on": null },
  { "name": "compute_stats", "args": [{"window": 20}], "depends_on": "fetch_prices" }
]
```

- `args`: passed through untouched, JSON-encoded as a single string into the job's `arg`
  parameter (FR-002a) — the service does not validate its shape beyond being JSON-serializable.
- `depends_on`: optional; when set, must name another entry in this same list (dangling
  references are an implementation-time edge case, not a request-level validation error).

**Response** `200 OK` — `list[JobRunResult]`, same order and length as the request.

```jsonc
[
  {
    "name": "fetch_prices",
    "finished_at": "2026-09-20T10:15:32-06:00",
    "duration": 0.842,
    "status": "completed",
    "output": [{"epic": "AWXSG", "bid": 123.4, "ask": 123.6}]
  },
  {
    "name": "compute_stats",
    "finished_at": "2026-09-20T10:15:33-06:00",
    "duration": 0.031,
    "status": "completed",
    "output": [20.1]
  }
]
```

- Unknown job name → that entry's result: `status: "error"`, `output: "job 'x' not found"`
  (FR-006a); rest of the batch proceeds normally.
- Upstream ended in "error" → dependent entry's result: `status: "error"`,
  `output: "upstream job 'x' failed"`, dependent job never executes (FR-005).
- Job raised during execution → `status: "error"`, `output: "<error detail>"` (FR-006).
- Job returned nothing → `status: "completed"`, `output: null` (FR-006).

## `PUT /api/v1/jobs`

Upload or replace a mutable job (FR-007–FR-009, FR-007a).

**Request** — `multipart/form-data`, one file field containing the `.py` job script. The job
name is derived by stripping the file extension and lowercasing the remainder (FR-007);
matching against existing jobs is case-insensitive (FR-007a).

**Responses**:
- `200 OK` — job created or replaced. `{"name": "<derived-name>", "job_type": "mutable"}`
- `409 Conflict` (Problem Details) — the derived name matches an existing **immutable** job
  (FR-008); the immutable job is left unchanged.
- `422 Unprocessable Entity` (Problem Details) — the uploaded script has no `run` entry point,
  or `run`'s signature doesn't match `def run(arg: str) -> list` (FR-009).

## `GET /api/v1/jobs/dependencies`

List approved third-party packages available for job scripts to import (FR-010).

**Response** `200 OK` — `list[str]`, e.g. `["requests", "pymongo"]`. Never includes the
service's own framework dependencies (`fastapi`, `uvicorn`, `pydantic`) — those are always
disallowed in job scripts regardless of this list (FR-015).

## `GET /api/v1/jobs/variables`

List the current set of shared variables (FR-011).

**Response** `200 OK` — `list[VariableOut]`

```jsonc
[
  { "name": "BASE_ENDPOINT_URL", "value": "https://api-capital.backend-capital.com" },
  { "name": "SESSION_MANAGER_INSECURE", "value": false }
]
```
