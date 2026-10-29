"""End-to-end checks that `uv run math-job-operator` binds to the configured host/port.

Requires the same MongoDB and Redis instances as the rest of the integration suite.
"""

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
START_COMMAND = ["uv", "run", "--no-sync", "math-job-operator"]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


def child_env(port: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        PORT=str(port),
        HOST="127.0.0.1",
        MONGO_ACCOUNT_DB="mathematics_test",
        REDIS_URL="redis://localhost:6379/1",
        PYTHONUNBUFFERED="1",
    )
    return env


def start_service(port: int) -> subprocess.Popen[str]:
    return subprocess.Popen(
        START_COMMAND,
        env=child_env(port),
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def test_service_listens_on_port_from_env() -> None:
    port = free_port()
    process = start_service(port)
    status_code = None
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and process.poll() is None:
            try:
                status_code = httpx.get(f"http://127.0.0.1:{port}/api/v1/jobs").status_code
                break
            except httpx.TransportError:
                time.sleep(0.25)
    finally:
        process.terminate()
        output, _ = process.communicate(timeout=10)

    assert status_code == 200, output
    assert f"on 127.0.0.1:{port}" in output


def test_bind_failure_exits_without_fallback() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen()
        port: int = holder.getsockname()[1]

        process = start_service(port)
        output, _ = process.communicate(timeout=30)

    assert process.returncode != 0, output
    assert str(port) in output
    assert "address already in use" in output.lower()
