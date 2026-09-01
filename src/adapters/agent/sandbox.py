"""Docker sandbox runner for the agent under test (spec C4, Fase 0 Day 2).

Contract:
- Container runs with `--network none` (egress deny-by-default) and CPU/memory
  caps. The agent command runs inside /workspace (bind-mounted, rw, isolated
  per run).
- Snapshot/restore: the workspace is snapshotted (tar.gz in memory) before the
  run and restored afterwards, so hostile writes never outlive the run and
  runs are repeatable.
- No long-lived containers: `docker run --rm` with a timeout.

The docker binary is invoked through an injected `executor` (default:
subprocess) so unit tests never require a daemon.
"""

import io
import os
import subprocess
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IMAGE = "python:3.12-slim"


@dataclass
class DockerRunResult:
    exit_code: int
    stdout: str
    stderr: str


class DockerUnavailable(RuntimeError):
    pass


@dataclass
class FakeDockerExecutor:
    """Test double: records docker argv and simulates a hostile agent that
    writes hostile.txt into the (host) workspace, exercising restore."""

    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, args: list[str], timeout: int) -> DockerRunResult:
        self.calls.append(args)
        # simulate agent effect: write into workspace via -v mount target
        try:
            v_idx = args.index("-v")
            host_dir = args[v_idx + 1].split(":")[0]
            (Path(host_dir) / "hostile.txt").write_text("pwned")
        except (ValueError, IndexError, OSError):
            pass
        return DockerRunResult(0, "", "")


class DockerSandbox:
    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        cpus: float = 1.0,
        memory_mb: int = 512,
        timeout_seconds: int = 120,
        executor=None,
    ):
        self.image = image
        self.cpus = cpus
        self.memory_mb = memory_mb
        self.timeout_seconds = timeout_seconds
        self._executor = executor or self._subprocess_executor

    @property
    def executor(self):
        return self._executor

    def run(self, agent_command: str, task: str, workspace: Path) -> DockerRunResult:
        snapshot = self.snapshot(workspace)
        try:
            args = self._docker_args(agent_command, task, workspace)
            return self._executor(args, self.timeout_seconds)
        finally:
            self.restore(workspace, snapshot)

    def _docker_args(self, agent_command: str, task: str, workspace: Path) -> list[str]:
        quoted_command = agent_command.replace("'", "'\\''")
        quoted_task = task.replace("'", "'\\''")
        inner = (
            f"export INJECTION_TASK='{quoted_task}' INJECTION_WORKSPACE=/workspace; {agent_command}"
        )
        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            self._host_user(),
            "--cpus",
            str(self.cpus),
            "--memory",
            f"{self.memory_mb}m",
            "--pids-limit",
            "128",
            "--security-opt",
            "no-new-privileges",
            "-v",
            f"{workspace.resolve()}:/workspace",
            "-w",
            "/workspace",
            self.image,
            "bash",
            "-c",
            inner,
        ]

    def snapshot(self, workspace: Path) -> bytes:
        """Capture the workspace as an in-memory tar.gz."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(workspace.resolve(), arcname=".")
        return buf.getvalue()

    def restore(self, workspace: Path, snapshot: bytes) -> None:
        """Reset the workspace to the snapshot state (delete-then-extract)."""
        resolved = workspace.resolve()
        for child in resolved.iterdir():
            if child.is_dir() and not child.is_symlink():
                import shutil

                shutil.rmtree(child)
            else:
                child.unlink()
        with tarfile.open(fileobj=io.BytesIO(snapshot), mode="r:gz") as tar:
            tar.extractall(str(resolved))

    @staticmethod
    def _host_user() -> str:
        """uid:gid of the invoking user so bind-mount writes stay host-deletable
        (container root would create root-owned files the harness cannot clean)."""
        try:
            return f"{os.getuid()}:{os.getgid()}"
        except AttributeError:  # non-POSIX
            return "0:0"

    @staticmethod
    def _subprocess_executor(args: list[str], timeout: int) -> DockerRunResult:
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)  # never leak env into sandbox orchestration
        try:
            completed = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout, check=False, env=env
            )
        except FileNotFoundError as exc:
            raise DockerUnavailable("docker binary not found") from exc
        except subprocess.TimeoutExpired:
            return DockerRunResult(124, "", f"sandbox timeout after {timeout}s")
        return DockerRunResult(completed.returncode, completed.stdout, completed.stderr)
