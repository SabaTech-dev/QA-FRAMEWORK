"""Persistent subprocess bridge to @desert-ant-labs/redact (S4).

The SDK is Node-only; QA-FW is Python. A small Node sidecar
(pii-redact-bridge/bridge.mjs) speaks NDJSON over stdio:

    request:  {"id": 1, "text": "..."}
    response: {"id": 1, "redactedText": "...", "items": [...]}

`bridge_command` is configurable so tests can inject a deterministic
fake bridge without downloading the 195MB model.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed, operator-configured bridge command
import threading
from typing import Any

_DEFAULT_COMMAND: list[str] = ["node", "pii-redact-bridge/bridge.mjs"]


class RedactBridge:
    """Manage the redact sidecar process and its request/response stream."""

    def __init__(self, bridge_command: list[str] | None = None) -> None:
        self._command = bridge_command or _DEFAULT_COMMAND
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._next_id = 1

    def __enter__(self) -> "RedactBridge":
        self._start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        try:
            self._proc = subprocess.Popen(  # nosec B603 - operator-configured command, no shell
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except (OSError, FileNotFoundError) as exc:
            raise RuntimeError(f"cannot start redact bridge: {exc}") from exc

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def redact_text(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Redact free text; return (redactedText, items). Thread-safe."""
        with self._lock:
            self._start()
            if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
                raise RuntimeError("redact bridge is not running")
            req_id = self._next_id
            self._next_id += 1
            self._proc.stdin.write(json.dumps({"id": req_id, "text": text}) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("redact bridge closed unexpectedly")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid bridge response: {line!r}") from exc
            if resp.get("id") != req_id:
                raise RuntimeError("redact bridge response out of order")
            return resp.get("redactedText", text), resp.get("items", [])
