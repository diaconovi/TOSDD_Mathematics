# Feature Specification: Listening Port & Host from Environment Configuration

**Feature Branch**: `002-port-from-env`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "when starting the application the listening port should be set from .env file as default behavior."

## Clarifications

### Session 2026-10-29

- Q: Should the listening host or network interface also be configurable from `.env` in this feature, or should only the port change? → A: Add a `HOST` setting in `.env`, defaulting to `127.0.0.1` (local only, as today).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start the service on the configured port (Priority: P1)

An operator or developer sets `PORT` in the project's `.env` file and starts the service with the standard documented start command. The service listens on that port. The operator does not need to export shell variables or repeat the port on the command line.

**Why this priority**: This is the whole feature. Today the configured port is ignored and the service always starts on 8000. That conflicts with other local services (Session Manager and Collector dev instances already use 8000/8001).

**Independent Test**: Set `PORT=8081` in `.env`, start the service with the standard start command from a fresh shell with no `PORT` variable exported, and confirm the service answers requests on 8081 and not on 8000.

**Acceptance Scenarios**:

1. **Given** `.env` contains `PORT=8081` and no `PORT` variable is set in the shell, **When** the operator runs the standard start command, **Then** the service listens on port 8081.
2. **Given** `.env` contains `PORT=8081`, **When** the service starts, **Then** the startup output states that the service is listening on port 8081.
3. **Given** `.env` contains `PORT=8081`, **When** the operator starts the service in development auto-reload mode, **Then** the service listens on 8081, including after each automatic reload.
4. **Given** `.env` contains `HOST=0.0.0.0` and `PORT=8081`, **When** the service starts, **Then** it accepts requests on port 8081 from other machines or containers. **Given** `HOST` is not set, **Then** it accepts requests only from the local machine.

---

### User Story 2 - Fall back to the default port when none is configured (Priority: P2)

An operator starts the service without setting a port, either because there is no `.env` file or because `.env` has no `PORT` entry. The service starts on the documented default port, 8000.

**Why this priority**: This keeps the existing out-of-the-box behavior for anyone who never configured a port.

**Independent Test**: Remove `PORT` from `.env`, start the service, and confirm it listens on 8000.

**Acceptance Scenarios**:

1. **Given** `.env` has no `PORT` entry and no `PORT` variable is set in the environment, **When** the service starts, **Then** it listens on port 8000.
2. **Given** no `.env` file exists, but all other required settings are supplied through the environment, **When** the service starts, **Then** it listens on port 8000.

---

### User Story 3 - Override the configured port for a single run (Priority: P3)

An operator needs to run the service on a different port temporarily, for example to run a second instance or avoid a temporary conflict. They should be able to do this without editing `.env`.

**Why this priority**: This is useful for local and CI workflows but isn't required for the core fix.

**Independent Test**: With `PORT=8081` in `.env`, start the service with a process environment variable `PORT=9090`, and confirm it listens on 9090.

**Acceptance Scenarios**:

1. **Given** `.env` contains `PORT=8081` and the process environment sets `PORT=9090`, **When** the service starts, **Then** it listens on 9090.
2. **Given** `.env` contains `PORT=8081`, **When** the operator passes an explicit port on the start command, **Then** the service listens on the explicitly passed port.

---

### Edge Cases

- **`PORT` is not a whole number** (for example `PORT=abc`): the service refuses to start and shows a clear error that names the `PORT` setting and the invalid value. It does not silently fall back to 8000.
- **`PORT` is outside 1–65535** (for example `PORT=0` or `PORT=70000`): the service refuses to start with a clear error stating the valid range.
- **The configured port is already in use**: the service fails to start with an error that names the port. It does not quietly pick a different port.
- **`PORT` is empty** (`PORT=`): this is treated as an invalid value and rejected with a clear error. It is not treated as "unset".
- **`PORT` has surrounding whitespace** (for example `PORT= 8081 `): the value is accepted after trimming, the same way other settings in `.env` are handled.
- **`HOST` is set to an address the machine doesn't have** (for example a mistyped IP): the service fails to start with an error that names the host. It does not fall back to `127.0.0.1`.
- **`HOST` is empty** (`HOST=`): this is treated as an invalid value and rejected with a clear error. It is not treated as "unset".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The standard documented start command MUST start the service on the port defined by the `PORT` setting in `.env`. The operator MUST NOT have to export shell variables or repeat the port on the command line.
- **FR-002**: The listening port MUST come from the same configuration source the service already uses for its other settings (MongoDB, Redis, logging, timezone). It MUST NOT be read separately.
- **FR-003**: When no port is configured anywhere, the service MUST listen on port 8000.
- **FR-004**: The port MUST be resolved in this order of precedence, highest first:
  1. A port passed explicitly on the start command.
  2. A `PORT` variable set in the process environment.
  3. `PORT` in `.env`.
  4. The default, 8000.
- **FR-005**: The service MUST validate the resolved port as a whole number from 1 to 65535. If the value is invalid, the service MUST refuse to start and report which setting is wrong and why.
- **FR-006**: If the resolved port cannot be bound (for example, it is already in use), the service MUST exit with an error that names the port. It MUST NOT fall back to another port.
- **FR-007**: At startup, the service MUST report the port it is listening on.
- **FR-008**: Development auto-reload mode MUST follow FR-001 through FR-007 in the same way, including after each reload.
- **FR-009**: The project documentation (README, `.env.example`, and the quickstart) MUST describe the single standard start command, the `PORT` and `HOST` settings, their defaults, and the precedence order.
- **FR-010**: The standard start command MUST bind to the network address defined by the `HOST` setting in `.env`. When no host is configured anywhere, it MUST bind to `127.0.0.1`, so the service is reachable only from the local machine, as today. `HOST` follows the same source rules as `PORT` (FR-002), the same precedence order (FR-004: start command, then process environment, then `.env`, then the default), and the same fail-fast behavior when it is empty or can't be bound (FR-005, FR-006). The startup report (FR-007) MUST include the host as well as the port.

### Key Entities

- **Listening Port setting (`PORT`)**: the TCP port the service accepts HTTP requests on. It is optional, is a whole number from 1 to 65535, and defaults to 8000. It is defined alongside the service's other `.env` settings.
- **Listening Host setting (`HOST`)**: the network address the service binds to. It is optional, is a non-empty IP address or hostname, and defaults to `127.0.0.1` (local only). `0.0.0.0` means all network interfaces. It is defined alongside `PORT`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of starts using the standard start command with a valid `PORT` in `.env`, the service listens on that port, with no extra steps from the operator.
- **SC-002**: An operator can change the service's port by editing one line in `.env`, and the change takes effect on the next start.
- **SC-003**: In 100% of starts with an invalid `PORT` value, the service refuses to start, and the error message identifies the `PORT` setting.
- **SC-004**: The service and the local Session Manager and Collector dev instances can all run at the same time on one machine, with no port conflicts, using only `.env` configuration.
- **SC-005**: Starting the service with no `PORT` configured behaves the same as today: it listens on 8000.

## Assumptions

- The "standard start command" is the single command documented in the README, launched through `uv run` as the constitution requires (Principle II). Other undocumented ways of launching the service are not required to honor `.env`.
- The `PORT` setting already exists in the service's configuration with a default of 8000. This feature makes that setting take effect. `HOST` is a new setting; its `127.0.0.1` default keeps today's local-only behavior, so exposing the service on the network is always an explicit choice.
- The precedence "explicit command-line value > process environment > `.env` > default" follows the usual convention for this kind of configuration. Allowing a one-off override without editing `.env` is acceptable.
- Containerized or production deployments that set `PORT` through the process environment will keep working, because the environment takes precedence over `.env`.
