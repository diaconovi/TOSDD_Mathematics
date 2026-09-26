# Feature Specification: Math Job Operator API

**Feature Branch**: `001-job-operator-api`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "Feature: Math Job Operator API — a service that runs Python
'jobs' (data-processing scripts) against market instrument data from Capital.com, on demand,
via an HTTP API. Actors are a Job Author (writes/uploads job scripts) and an API Consumer
(lists jobs, triggers job runs, manages shared variables). Functional requirements: list
available jobs (GET /api/v1/jobs) with name/description/type/return type; run jobs (POST
/api/v1/jobs) accepting an ordered list of job requests with arguments and an optional
same-request dependency, running concurrently with dependents waiting on their upstream job
and receiving its return value as an `upstream` variable, returning per-job
name/timestamp/duration/status/output; upload or replace a mutable job (PUT /api/v1/jobs) via
file upload, name derived from the file name, rejecting uploads to immutable jobs, requiring a
`def run(arg: str) -> list` entry point; list job dependencies (GET /api/v1/jobs/dependencies)
i.e. approved third-party packages; list default variables (GET /api/v1/jobs/variables); set
or update shared variables (PUT /api/v1/variables) with name/value pairs, upsert semantics, and
uppercase name normalization, automatically available to every job run. Business rules: jobs
are immutable (fixed) or mutable (user-uploaded/replaceable); jobs may only use approved
project dependencies, never the service's own framework/server/validation-library dependencies;
adding a new job dependency requires a project-level change and restart, not a runtime action.
Non-functional requirements: configurable logging level, configurable listen port, configurable
timezone for timestamps, full traceability of job executions (start/end time, duration,
status). Deliverables: a README documenting every endpoint, and one example job that queries
the collector's market endpoint for epic 'AWXSG' and reads at least one default variable. Out
of scope / open: authentication/authorization, per-job timeout/cancellation, sandboxing of
uploaded scripts, and — flagged as needing an explicit decision — the failure-propagation
policy when an upstream job fails; also unspecified: concurrency limits."

## Clarifications

### Session 2026-09-20

- Q: How should a job request's `arguments` (a list of dicts, e.g. `[{"arg1": "value"}]`) map onto a job's required entry point `def run(arg: str) -> list`, which only accepts a single string parameter? → A: The full `arguments` list is JSON-encoded into a single string and passed as `arg`; the job script decodes it itself.
- Q: What should happen when a job run request in `POST /api/v1/jobs` names a job that doesn't exist in the catalog? → A: That job's own result summary reports status "error" with an output explaining the job name was not found; the rest of the batch still runs normally.
- Q: What type of value should a shared variable be allowed to hold when set via `PUT /api/v1/variables`? → A: Arbitrary JSON — a variable's value may be any JSON type (string, number, bool, object, array).
- Q: Does "traceable" job execution history (FR-017) need to be retrievable later through the API, or is it satisfied by structured logs/records the operator can inspect outside the API? → A: Structured logs/records are sufficient — no dedicated API endpoint for historical job runs is required; the synchronous run response is the only place results are returned.
- Q: When a job's name is derived from an uploaded file's name in `PUT /api/v1/jobs`, how should the file name be converted to a job name? → A: Strip the file extension and lowercase the remainder; job-name matching (for collisions/replacement) is case-insensitive.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Jobs and Retrieve Results (Priority: P1)

An API Consumer submits one or more jobs to run against market instrument data, optionally
chaining a job to depend on the result of another job in the same request, and receives a
result summary for every job once it finishes.

**Why this priority**: This is the core value of the service — turning on-demand
data-processing requests into results. Without it, nothing else in the feature matters.

**Independent Test**: Can be fully tested by submitting a request with a single
no-dependency job and confirming a complete result summary (name, finish timestamp,
duration, status, output) is returned; a second test submits two jobs where one depends on
the other and confirms the dependent job's output reflects the upstream job's return value.

**Acceptance Scenarios**:

1. **Given** at least one available job, **When** an API Consumer submits it with valid
   arguments and no dependency, **Then** the response includes that job's name, finish
   timestamp, total processing time, status "completed", and its return value as output.
2. **Given** two available jobs A and B, **When** an API Consumer submits both in one
   request with B declaring a dependency on A, **Then** B does not start until A finishes,
   and B's execution has access to A's return value through a variable named `upstream`.
3. **Given** a job that raises an error during execution, **When** its run completes,
   **Then** its result summary reports status "error" and the output contains the error
   detail.
4. **Given** a job whose `run()` produces no return value, **When** it completes
   successfully, **Then** its result summary reports status "completed" and output `null`.
5. **Given** a dependent job B declares upstream job A, **When** A's run ends with status
   "error", **Then** B is never executed and B's result summary reports status "error" with
   an output explaining that its upstream job failed.

---

### User Story 2 - Discover Available Jobs and Approved Packages (Priority: P2)

An API Consumer browses the catalog of jobs that can be run and the third-party packages
available to job scripts, before deciding what to submit.

**Why this priority**: Consumers need to know what jobs exist, their expected arguments and
return types, and what packages jobs can rely on, before they can use User Story 1
effectively.

**Independent Test**: Can be fully tested by calling the job catalog and dependency-list
endpoints independently of running any job, and confirming the returned data matches what is
actually installed/available.

**Acceptance Scenarios**:

1. **Given** a mix of immutable and mutable jobs exist, **When** an API Consumer requests
   the job catalog, **Then** every job is listed with its name, description, type
   ("mutable" or "immutable"), and return type.
2. **Given** a set of approved third-party packages, **When** an API Consumer requests the
   dependency list, **Then** the response contains exactly those packages currently
   available for job scripts to import.

---

### User Story 3 - Upload or Replace a Mutable Job (Priority: P2)

A Job Author uploads a new job script, or replaces an existing mutable job's script, so it
becomes available for API Consumers to run.

**Why this priority**: The service's job catalog must be extensible without a service
redeployment; this is what makes it a general-purpose job operator rather than a fixed set of
endpoints.

**Independent Test**: Can be fully tested by uploading a valid script and then confirming it
appears in the job catalog (User Story 2) and can be run (User Story 1); a second test
attempts to overwrite an immutable job and confirms it is rejected.

**Acceptance Scenarios**:

1. **Given** a valid job script file exposing `def run(arg: str) -> list`, **When** a Job
   Author uploads it, **Then** the job becomes available under a name derived from the file
   name and is marked "mutable".
2. **Given** an existing mutable job, **When** a Job Author uploads a new script under the
   same derived name, **Then** the previous script is replaced by the new one.
3. **Given** an existing immutable job, **When** a Job Author attempts to upload a script
   under that job's name, **Then** the upload is rejected with an error and the immutable
   job is left unchanged.
4. **Given** a script that does not expose a `def run(arg: str) -> list` entry point,
   **When** a Job Author uploads it, **Then** the upload is rejected with an error.

---

### User Story 4 - View and Update Shared Variables (Priority: P3)

An API Consumer inspects the shared variables currently available to all jobs, and adds or
updates variables so subsequent job runs can use them.

**Why this priority**: Shared variables let jobs be configured (e.g. credentials, defaults)
without editing job code, but this is a supporting capability rather than the core run flow.

**Independent Test**: Can be fully tested by setting a variable, confirming it appears in the
variable listing in uppercase form, and confirming a job run can read it.

**Acceptance Scenarios**:

1. **Given** the current set of shared variables, **When** an API Consumer requests the
   variable list, **Then** every stored variable name and value is returned.
2. **Given** a variable name submitted in any letter case, **When** an API Consumer sets it,
   **Then** it is stored and subsequently listed in uppercase form.
3. **Given** a variable that already exists, **When** an API Consumer submits a new value
   for the same name (in any case), **Then** the stored value is overwritten rather than
   duplicated.
4. **Given** a variable has been set, **When** any job runs afterward, **Then** that
   variable is automatically accessible inside the job's execution.

---

### Edge Cases

- A run request names a job that does not exist in the catalog at all: that job's result is
  reported as an "error" (job name not found) without affecting the rest of the batch (see
  FR-006a).
- A dependent job's `depends_on` names a job not present in the same request: that job's
  result is reported as an "error" (dependency not found), mirroring FR-006a (see FR-006b).
- (Resolved — see Assumptions) Multiple dependents may share the same upstream job; each
  gets its own copy of the upstream's return value as `upstream`.
- What happens when a PUT /api/v1/jobs upload's derived job name collides with an existing
  mutable job versus an existing immutable job?
- What happens when an uploaded script defines `run` with a different signature (e.g. extra
  required parameters, wrong return annotation)?
- (Resolved) The same variable name submitted twice with different letter case in one
  `PUT /api/v1/variables` request: the last occurrence in request order wins (see FR-012).
- What happens when a job attempts to read a shared variable that has never been set?
- A job's return value cannot be represented as JSON: reported as an "error" result with a
  serialization-failure detail, rather than an unhandled error (see FR-006c).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a way to list every available job (both immutable and
  mutable), returning for each one its name, description, job type ("mutable" or
  "immutable"), and return type.
- **FR-001a**: A job's `return_type` MUST describe the declared shape of the list `run()`
  produces (e.g. `"list"` by default, or a more specific description such as
  `"list[float]"` when the job declares one via a module-level `RETURN_TYPE` constant) — not
  merely restate the fixed `list` return annotation required by FR-009.
- **FR-002**: System MUST provide a way to submit an ordered list of job run requests in a
  single call, each specifying a job name, a list of argument dicts, and an optional
  reference to another job name in the same request as its upstream dependency.
- **FR-002a**: System MUST JSON-encode a job request's full `arguments` list into a single
  string and pass it as the `arg` parameter of the job's `run()` entry point; the job script
  is responsible for decoding it.
- **FR-003**: System MUST execute all jobs submitted in a single run request concurrently,
  except that a job declaring a dependency MUST NOT start until its declared upstream job has
  finished.
- **FR-004**: System MUST expose a finished upstream job's return value to its dependent job
  as a variable named `upstream`.
- **FR-005**: When a job's declared upstream job ends with status "error", the system MUST
  NOT execute that dependent job and MUST report its result summary with status "error" and
  an output describing that its upstream job failed.
- **FR-006**: System MUST return, for every job in a run request, a result summary
  containing the job name, finish timestamp, total processing time, status ("completed" or
  "error"), and output (the return value on success, the error detail on failure, or `null`
  when the job has no return value).
- **FR-006a**: When a run request names a job that does not exist in the catalog, the system
  MUST report that job's result summary with status "error" and an output explaining the job
  name was not found, while continuing to process the rest of the batch normally.
- **FR-006b**: When a job's `depends_on` names a job absent from the same batch, the system
  MUST report that job's result summary with status "error" and an output explaining the
  dependency was not found, without executing it, and without affecting the rest of the
  batch.
- **FR-006c**: When a job's return value cannot be represented as JSON, the system MUST
  report that job's result summary with status "error" and an output describing the
  serialization failure, rather than raising an unhandled error.
- **FR-007**: System MUST provide a way to upload a job script as a file, deriving the job's
  name from the uploaded file's name by stripping its file extension and lowercasing the
  remainder.
- **FR-007a**: System MUST match job names case-insensitively when checking for collisions
  against existing mutable or immutable jobs (e.g. `AWXSG.py` and `awxsg.PY` resolve to the
  same job name).
- **FR-008**: System MUST reject an upload that targets an existing immutable job's name,
  returning an error and leaving that immutable job unchanged.
- **FR-009**: System MUST validate that an uploaded job script exposes a default entry point
  matching `def run(arg: str) -> list`, rejecting the upload with an error when this entry
  point is missing or does not match the expected signature.
- **FR-010**: System MUST provide a way to list the third-party packages currently approved
  and available for job scripts to import.
- **FR-011**: System MUST provide a way to list the current set of shared variables available
  to all jobs.
- **FR-012**: System MUST provide a way to create or update shared variables from a list of
  name/value pairs, creating variables that do not yet exist and overwriting the value of
  variables that already exist; when the same normalized name appears more than once in a
  single request, the last occurrence in request order determines the stored value.
- **FR-013**: System MUST normalize every shared variable name to uppercase, regardless of
  the letter case submitted, both when storing and when matching against existing variables.
- **FR-013a**: System MUST accept any JSON type (string, number, boolean, object, or array)
  as a shared variable's value and return it in that same type when listed or read by a job.
- **FR-014**: System MUST make all stored shared variables automatically available inside
  every job execution.
- **FR-015**: System MUST prevent job scripts from importing the core service's own runtime
  dependencies (its web framework, application server, and validation library), restricting
  job scripts to the approved package set only.
- **FR-016**: Adding a new package to the approved job-dependency set MUST require a
  project-level change and an application restart; the system MUST NOT support adding job
  dependencies dynamically at request time.
- **FR-017**: System MUST record, for every job execution, its start time, end time,
  duration, and final status, and keep this record traceable after the run completes, via
  structured logs/records inspectable outside the API; no dedicated history-query endpoint is
  required.
- **FR-018**: System MUST allow the logging level (INFO, DEBUG, or WARNING) to be configured
  without a code change.
- **FR-019**: System MUST allow the HTTP listen port to be configured, defaulting to a
  documented value when not explicitly set.
- **FR-020**: System MUST allow the timezone used for all reported timestamps to be
  configured.

### Key Entities

- **Job**: An executable unit of data-processing logic exposed by the catalog; key
  attributes are name, description, type ("mutable" or "immutable"), return type (defaults
  to "list"; may be a job-declared, more specific description via a `RETURN_TYPE` constant,
  per FR-001a), and its entry point.
- **Job Run Request**: A single job's execution request within a batch submission; key
  attributes are job name, argument list, and an optional upstream job reference.
- **Job Run Result**: The outcome of one executed job; key attributes are job name, finish
  timestamp, processing time, status, and output.
- **Shared Variable**: A named value available to all job executions; key attributes are
  name (always stored uppercase) and value (any JSON type: string, number, boolean, object,
  or array).
- **Approved Package**: A third-party package a job script is permitted to import; key
  attribute is package name.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An API Consumer can retrieve the full job catalog in a single request and
  determine each job's type and return type without inspecting any source code.
- **SC-002**: An API Consumer submitting a batch that includes at least one dependent job
  receives a complete result summary for every submitted job once all of them finish.
- **SC-003**: A dependent job's result reflects the agreed failure-propagation policy every
  time its declared upstream job fails.
- **SC-004**: A Job Author can publish a new or updated mutable job and have it appear in the
  job catalog and become runnable without any service code change or redeployment.
- **SC-005**: Every attempt to overwrite an immutable job through the upload capability is
  rejected, with zero immutable jobs ever modified that way.
- **SC-006**: A shared variable set through the API is visible in the variable listing and
  inside every subsequent job run, regardless of the letter case used when it was set.
- **SC-007**: Every completed or failed job run has a traceable record of start time, end
  time, duration, and status available after the run finishes.

## Assumptions

- "Return type" reported for a job describes the declared type of the value its `run()`
  entry point produces, not a runtime value.
- The approved package set for job scripts is curated by project maintainers ahead of time;
  API Consumers cannot request new packages through the API (per FR-016).
- A job script is responsible for decoding the JSON-encoded `arguments` string it receives as
  `arg` (per FR-002a); the service performs no validation of a job's expected argument shape
  beyond the entry-point signature check (FR-009).
- File uploads for the job-upload capability carry exactly one job script per request.
- The example job required as a deliverable (querying the collector's market endpoint for
  epic "AWXSG" and reading a default variable) is a mutable job.
- Multiple jobs within the same run request may declare a dependency on the same upstream
  job; each dependent job receives its own copy of that upstream job's return value as
  `upstream`.

## Out of Scope

- Authentication or authorization for any endpoint.
- Per-job execution timeout or mid-run cancellation.
- Sandboxing or security isolation of uploaded job scripts beyond the import restriction in
  FR-015.
- Limits on the number of jobs that may run concurrently.
