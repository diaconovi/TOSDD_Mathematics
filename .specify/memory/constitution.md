<!--
Sync Impact Report
===================
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Modified principles: n/a (first substantive fill of the placeholder scaffold)
Added sections:
  - Core Principles I–X (Strict Static Typing; uv-Managed Toolchain; Focused, Modular
    Library Design; API-First & RESTful Conventions; Statelessness & Distributed State;
    Service Boundary Isolation; Dependency Inversion; Standardized Error Responses;
    Inter-Service Communication via Client Packages; Testing Discipline)
  - Technology Stack Constraints
  - Development Workflow & Quality Gates
  - Governance
Removed sections: none (all bracket placeholders replaced)
Deferred / follow-up TODOs: none — all values were supplied by the user or clarified
  interactively (Collector client package confirmed as `to_collector_client`).
-->

# Capital.com Data & Instruments Mathematics API Microservice Constitution

## Core Principles

### I. Strict Static Typing & Modern Python Syntax (NON-NEGOTIABLE)
All code MUST use Python static strict typing: every public function, method, and class
attribute carries explicit type annotations, the project's type checker MUST run in strict
mode, and `Any` MUST NOT be used to silence a typing error. Only Python 3+ syntax is
permitted — no Python 2-compatible constructs (`from __future__ import`, `unicode` literals,
old-style classes, `%`-only string formatting where f-strings apply).
Rationale: this service computes and serves financial instrument and pricing data; a typing
error caught at review time is cheaper than a malformed payload reaching a downstream
consumer.

### II. uv-Managed Toolchain (NON-NEGOTIABLE)
Python version and dependency management MUST always be performed through `uv` (`uv add`,
`uv remove`, `uv lock`, `uv python pin`). The target interpreter is Python 3.14. All
development and execution MUST happen inside a virtual environment, and the application MUST
always be started via `uv run` — never via a bare `python`/`pip` invocation or a manually
activated environment outside `uv`'s control.
Rationale: a single, enforced toolchain removes environment drift between contributors, CI,
and deployment, and keeps the interpreter/dependency graph reproducible from a lockfile.

### III. Focused, Modular Library Design
The project MUST remain a focused, modular Python tool library: each module owns one clear
responsibility, and no module exists for purely organizational reasons. Public modules,
classes, and functions SHOULD include a concise usage example in their docstring wherever the
call pattern is not immediately obvious from the signature.
Rationale: a narrow, well-documented module surface keeps the library composable and lets new
contributors learn correct usage from the code itself rather than external documents.

### IV. API-First & RESTful Conventions
All business logic MUST be exposed through standardized RESTful endpoints. Resource naming
MUST be clear and resource-oriented, using plural nouns (e.g. `/api/v1/instruments`,
`/api/v1/prices`). No business capability may be reachable only through an internal function
call that bypasses the API surface.
Rationale: a consistent, resource-oriented API is the contract every consumer and future
service integration depends on; inconsistent naming or hidden logic breaks that contract.

### V. Statelessness & Distributed State
Each microservice instance MUST be stateless. Session and other cross-request state MUST live
in a distributed cache or store (e.g. MongoDB) — never in local process memory. Any instance
MUST be replaceable or restarted without losing in-flight session data.
Rationale: statelessness is what allows horizontal scaling and safe rolling deployments; state
held in local memory silently breaks both.

### VI. Service Boundary Isolation
Domain boundaries MUST NOT be crossed directly, and a service MUST NOT access another
service's database. All cross-service interaction MUST occur through explicit REST contracts
or asynchronous events.
Rationale: enforced boundaries keep services independently deployable and prevent hidden
coupling through shared data stores.

### VII. Dependency Inversion
All dependencies MUST flow inward, toward domain and application logic. Infrastructure
concerns (databases, external HTTP clients, message brokers) MUST be accessed only through
abstract interfaces defined by the domain/application layers; concrete implementations are
injected, never imported directly by inner layers.
Rationale: inverting dependencies keeps domain logic testable in isolation and lets
infrastructure be swapped without touching business rules.

### VIII. Standardized Error Responses
All API errors MUST return a consistent JSON payload conforming to RFC 7807 (Problem Details
for HTTP APIs), paired with a meaningful HTTP status code. Ad-hoc error shapes are not
permitted.
Rationale: a single error contract lets every consumer — human or service — handle failures
uniformly instead of special-casing each endpoint.

### IX. Inter-Service Communication via Client Packages
Communication with other services MUST go through that service's designated client package —
direct, ad-hoc HTTP calls to another service are not permitted. The designated packages are:
- **Session Manager** (authentication): `to_session_manager`
- **Collector** (market data, instruments, and prices gathering): `to_collector_client`

Rationale: routing all inter-service calls through a named client package centralizes retry,
auth, and contract-versioning logic instead of duplicating it at each call site.

### X. Testing Discipline: Contract Tests & Coverage Targets
Integration (contract) tests are mandatory for every infrastructure database repository and
every external HTTP client. Unit test coverage for domain entities and application use cases
MUST remain above 80% at all times.
Rationale: contract tests catch drift against real infrastructure and external services that
mocks cannot detect; the coverage floor keeps the core business logic — the highest-risk,
longest-lived code — verifiably correct as the service evolves.

## Technology Stack Constraints

- **Language / runtime**: Python 3.14 only.
- **Dependency & version manager**: `uv` exclusively — no `pip`, `poetry`, `pipenv`, or
  `conda` for dependency resolution or interpreter management.
- **Execution**: always inside a `uv`-managed virtual environment; the application is always
  launched via `uv run`.
- **Type checking**: a strict-mode static type checker (e.g. `mypy --strict` or Pyright strict)
  MUST pass with zero errors before merge.
- **State/session storage**: a distributed cache or document store (e.g. MongoDB) — never
  in-process memory or local files.

## Development Workflow & Quality Gates

- Every pull request MUST pass strict type checking, the full test suite, and the >80%
  coverage gate for domain entities and application use cases before it can be merged.
- Any new infrastructure repository or external HTTP client MUST ship with its contract
  (integration) tests in the same pull request that introduces it.
- Code review MUST verify: RESTful, plural, resource-oriented endpoint naming; RFC 7807 error
  responses; no direct cross-service database access; and that inter-service calls go through
  `to_session_manager` or `to_collector_client` as appropriate.
- Any deviation from a Core Principle MUST be documented in the pull request description with
  an explicit justification and, where applicable, a follow-up task to remove the deviation.

## Governance

This constitution supersedes all other project practices and conventions. Amendments require:
(1) a documented rationale for the change, (2) update of the version number per the semantic
versioning policy below, and (3) review of all dependent templates and workflows for
consistency with the amendment.

**Versioning policy** (semantic versioning applied to this document):
- **MAJOR**: backward-incompatible governance changes, or removal/redefinition of a Core
  Principle.
- **MINOR**: a new principle or section is added, or existing guidance is materially expanded.
- **PATCH**: clarifications, wording fixes, or other non-semantic refinements.

All pull requests and code reviews MUST verify compliance with this constitution. Complexity
or deviation that cannot be justified against these principles MUST be simplified or rejected
before merge.

**Version**: 1.0.0 | **Ratified**: 2026-09-20 | **Last Amended**: 2026-09-20
