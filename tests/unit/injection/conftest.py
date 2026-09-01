"""Shared fixtures for the injection harness tests.

Redirects the HITL queue to a temp path for every test so CLI-level
integration tests never pollute the real reports/injection queue.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolated_hitl_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("INJECTION_HITL_QUEUE", str(tmp_path / "hitl.jsonl"))
