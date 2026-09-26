# Phase 0 Research: Math Job Operator API

## 1. Already-resolved spec ambiguity: upstream-failure propagation

**Note**: The plan input describes the failure/missing-upstream propagation policy as "still
undecided (spec open question)" and asks for a configurable stub. This was actually already
resolved during `/speckit-clarify` (2026-09-20) and is captured in the spec as FR-005: when a
job's declared upstream ends in "error", the dependent job is **not executed** and is reported
with status "error" and an output explaining the upstream failure. This plan implements FR-005
directly rather than a swappable policy branch — no further research needed here.

## 2. Cross-worker dependency signaling mechanism

**Decision**: Use Redis pub/sub (one channel per job-run-batch, one sub-channel/key per job
name) to signal "job X in batch Y finished with status Z" from the coroutine/task that ran the
upstream job to the coroutine awaiting it for the dependent job.

**Rationale**: Constitution Principle V requires every instance to be stateless and forbids
state that only lives in local process memory. A pure in-process `asyncio.Event`/`Future`
would work correctly only if uvicorn is guaranteed to run a single worker process and every
job in a batch is scheduled on that same event loop; using Redis instead keeps the completion
signal in a distributed store so the design remains correct even if the service is scaled to
multiple uvicorn workers or replicas. It also matches the `REDIS_URL` variable already present
in the project's seed configuration.

**Alternatives considered**:
- Pure in-process `asyncio.Event` per batch: simplest, but silently breaks correctness the
  moment the service runs more than one worker process — rejected as inconsistent with
  Principle V.
- A full task-queue library (Celery, arq, dramatiq): adds a persistent worker/broker topology
  and out-of-request-lifecycle execution semantics that the spec doesn't ask for (the run
  endpoint is synchronous — it returns only once every submitted job has finished); rejected
  as unnecessary complexity for this feature's scope.

## 3. Dynamic job loading (immutable vs. mutable)

**Decision**: Immutable jobs are loaded via `importlib.util.spec_from_file_location` /
`module_from_spec` from the dedicated filesystem directory at startup, building the
normalized (lowercase, extension-stripped) catalog index once. Mutable jobs are stored as
source text in MongoDB and loaded on demand by compiling the source
(`compile(source, f"<mutable:{name}>", "exec")`) into a fresh `types.ModuleType` namespace —
no temp files needed.

**Rationale**: `importlib` is the standard, well-understood way to load a real file as a
module and gives good tracebacks. For Mongo-backed source, compiling directly into a fresh
module namespace avoids the extra I/O and cleanup of writing a temp file per run while still
giving the script its own isolated namespace (no leakage between job runs).

**Alternatives considered**:
- Writing mutable job source to a temp file and using the same `importlib` path for both
  cases: more uniform code path, but adds filesystem I/O and cleanup on every run for no
  functional benefit — rejected in favor of the simpler in-memory `compile`/`exec`.

## 4. Enforcing the "no core-dependency imports" rule (FR-015)

**Decision**: Statically parse each job script's AST (`ast.parse` + walk `ast.Import` /
`ast.ImportFrom` nodes) at load time (upload time for mutable jobs, startup time for immutable
jobs) and reject/refuse to load any script that imports `fastapi`, `uvicorn`, or `pydantic`
(or submodules thereof). This check runs once per script version, not per invocation.

**Rationale**: The spec explicitly puts sandboxing/full security isolation out of scope — only
the specific import restriction in FR-015 is required. A static AST check is enough to catch
the straightforward `import fastapi` / `from pydantic import ...` cases without the
performance cost or complexity of a runtime import hook (`sys.meta_path` finder), which would
matter only if true sandboxing were in scope.

**Alternatives considered**:
- Runtime `sys.meta_path` import-blocking hook: would also catch dynamically constructed
  imports (`importlib.import_module("fast" + "api")`), but that level of adversarial
  resistance is explicitly out of scope (sandboxing is not required); rejected as
  disproportionate to the stated requirement.

## 5. Entry-point signature validation (FR-009)

**Decision**: After loading a candidate job module, use `inspect.signature(module.run)` to
confirm there is exactly one parameter named `arg` annotated `str`, and
`typing.get_type_hints(module.run).get("return")` resolves to `list`. Reject with an error if
`run` is missing or the signature doesn't match.

**Rationale**: `inspect`/`typing` introspection is the standard library's own mechanism for
this and needs no extra dependency; it runs once per upload (or once at startup for immutable
jobs), not per invocation.

**Alternatives considered**: None material — this is the standard approach for validating a
callable's signature in Python.

## 6. Testing strategy for MongoDB and external HTTP clients

**Decision**: Repository contract tests run against a real (ephemeral, test-only) MongoDB
instance rather than a mock, per Constitution Principle X ("contract tests catch drift ...
that mocks cannot detect"). `to_session_manager`/`to_collector_client` contract tests run
against the dev/test instances already available at `http://localhost:8000` and
`http://localhost:8001` respectively (per the feature's stated Dev/Test Environment).

**Rationale**: Directly mandated by the constitution's testing principle; using the real
dev/test service instances for the two client packages avoids maintaining a second,
divergence-prone mock of their contracts.

**Alternatives considered**: In-memory `mongomock` for repository tests — rejected as a
violation of Principle X's explicit "not mocks" instruction for infrastructure repositories.

## 7. Variable / job-output typing without `Any`

**Decision**: Introduce a recursive `JSONValue` type alias
(`JSONValue = str | int | float | bool | None | dict[str, "JSONValue"] | list["JSONValue"]`)
used for `SharedVariable.value` and `JobRunResult.output`, instead of `typing.Any`.

**Rationale**: Satisfies FR-013a (any JSON type) and the spec's `output: Any | None` shape
while keeping Constitution Principle I's "no bare `Any`" rule intact — `JSONValue` still type
-checks under strict mypy/Pyright and documents the real constraint (must be JSON-representable)
rather than "anything at all".

**Alternatives considered**: `pydantic.JsonValue` (built-in equivalent) — a reasonable
drop-in alternative; either satisfies the same constraint, so the choice is left to
implementation-time convenience as long as a bare `Any` is not used at the boundary.
