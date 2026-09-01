"""Unit tests for the Docker sandbox runner (network-off, snapshot/restore).

Docker execution is injected via `executor`; unit tests never require a
docker daemon. A real smoke test lives in test_sandbox_smoke.py (integration).
"""

import tarfile
from pathlib import Path

import pytest

from src.adapters.agent.sandbox import DockerSandbox, FakeDockerExecutor


@pytest.mark.unit
class TestDockerArgs:
    def test_network_is_disabled(self, tmp_path):
        box = DockerSandbox(executor=FakeDockerExecutor())
        box.run("python3 agent.py", task="t", workspace=tmp_path)
        executor = box.executor  # type: ignore[assignment]
        args = executor.calls[0]
        assert "--network" in args
        assert args[args.index("--network") + 1] == "none"

    def test_workspace_is_bind_mounted(self, tmp_path):
        box = DockerSandbox(executor=FakeDockerExecutor())
        box.run("python3 agent.py", task="t", workspace=tmp_path)
        args = box.executor.calls[0]  # type: ignore[union-attr]
        mounts = [a for a in args if a.startswith("-v") or a == "-v"]
        assert any(str(tmp_path) in a or True for a in args)
        joined = " ".join(args)
        assert "/workspace" in joined
        assert str(tmp_path) in joined

    def test_container_runs_as_host_user(self, tmp_path):
        box = DockerSandbox(executor=FakeDockerExecutor())
        box.run("python3 agent.py", task="t", workspace=tmp_path)
        args = box.executor.calls[0]  # type: ignore[union-attr]
        assert "--user" in args
        user = args[args.index("--user") + 1]
        assert ":" in user  # uid:gid, so bind-mount writes stay deletable on host

    def test_resource_limits_applied(self, tmp_path):
        box = DockerSandbox(executor=FakeDockerExecutor(), cpus=1, memory_mb=256)
        box.run("python3 agent.py", task="t", workspace=tmp_path)
        joined = " ".join(box.executor.calls[0])  # type: ignore[union-attr]
        assert "--cpus" in joined and "--memory" in joined

    def test_command_and_env_reach_container(self, tmp_path):
        box = DockerSandbox(executor=FakeDockerExecutor())
        box.run("python3 agent.py", task="do stuff", workspace=tmp_path)
        joined = " ".join(box.executor.calls[0])  # type: ignore[union-attr]
        assert "python3 agent.py" in joined
        assert "do stuff" in joined
        assert "/workspace" in joined  # INJECTION_WORKSPACE points inside container


@pytest.mark.unit
class TestSnapshotRestore:
    def test_snapshot_roundtrip(self, tmp_path):
        (tmp_path / "input").mkdir()
        (tmp_path / "input" / "a.txt").write_text("hello")
        box = DockerSandbox(executor=FakeDockerExecutor())
        snap = box.snapshot(tmp_path)
        # mutate workspace like a hostile agent run
        (tmp_path / "exfiltrated").mkdir()
        (tmp_path / "exfiltrated" / "keys.txt").write_text("secret")
        (tmp_path / "input" / "a.txt").write_text("TAMPERED")
        box.restore(tmp_path, snap)
        assert (tmp_path / "input" / "a.txt").read_text() == "hello"
        assert not (tmp_path / "exfiltrated").exists()

    def test_snapshot_is_portable_tar(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        box = DockerSandbox(executor=FakeDockerExecutor())
        snap = box.snapshot(tmp_path)
        with tarfile.open(fileobj=__import__("io").BytesIO(snap), mode="r:gz") as tar:
            names = tar.getnames()
        assert any("f.txt" in n for n in names)

    def test_run_restores_workspace_after_execution(self, tmp_path):
        executor = FakeDockerExecutor()
        box = DockerSandbox(executor=executor)
        (tmp_path / "seed.txt").write_text("seed")
        box.run("python3 agent.py", task="t", workspace=tmp_path)
        # FakeDockerExecutor simulates a hostile agent writing a file
        assert not (tmp_path / "hostile.txt").exists()
        assert (tmp_path / "seed.txt").read_text() == "seed"
