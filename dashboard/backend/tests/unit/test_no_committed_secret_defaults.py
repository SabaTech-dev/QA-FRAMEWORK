"""Repo guard against committed secret defaults (card 2972521c, incident 112853a6).

The staging SECRET_KEY default committed in this public repo allowed forging
JWTs against qa.sabatech.dev (CWE-798, HIGH 8.6). These tests are the
executable form of the card acceptance criteria so the defaults cannot be
reintroduced silently:

- docker-compose.unified.yml must declare SECRET_KEY as required
  (``${SECRET_KEY:?...}``) with NO committed fallback.
- No tracked file may carry the known dev-secret literals
  ("dev-secret-key" / "dev-jwt-secret") outside the tests of this change.
"""

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    """Git toplevel, robust to this file's nesting depth."""
    out = subprocess.run(
        ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return Path(out)


REPO_ROOT = _repo_root()
UNIFIED_COMPOSE = REPO_ROOT / "docker-compose.unified.yml"

FORBIDDEN_LITERALS = ("dev-secret-key", "dev-jwt-secret")

# File extensions whose tracked contents are scanned for secret literals.
SCANNED_SUFFIXES = {
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
    ".sh",
    ".cfg",
    ".ini",
    ".toml",
    ".example",
    ".env",
}


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def test_unified_compose_secret_key_has_no_committed_default():
    """SECRET_KEY must be required in the unified compose, never defaulted."""
    content = UNIFIED_COMPOSE.read_text()
    assert "SECRET_KEY=" in content
    # No inline default fallback may be committed for SECRET_KEY.
    assert "SECRET_KEY=${SECRET_KEY:-" not in content
    assert "dev-secret-key" not in content
    # The variable must be declared required (compose fails fast when unset):
    # `${SECRET_KEY:?...}` — the ":?" without a following default is the
    # hard-requirement marker in compose interpolation syntax.
    assert "SECRET_KEY=${SECRET_KEY:?" in content
    assert "SECRET_KEY=${SECRET_KEY:-" not in content


def test_tracked_files_contain_no_dev_secret_literals():
    """AC (a)/(c): the known dev-secret literals must not exist in tracked
    files outside the tests introduced by this change."""
    offenders: list[str] = []
    for tracked in _tracked_files():
        path = REPO_ROOT / tracked
        if path.suffix.lower() not in SCANNED_SUFFIXES and ".env" not in path.name:
            continue
        # Tests of this change may reference the literals as guards.
        if tracked.startswith("dashboard/backend/tests/"):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for literal in FORBIDDEN_LITERALS:
            if literal in text:
                offenders.append(f"{tracked}: contains '{literal}'")
    assert not offenders, "Committed secret defaults found:\n" + "\n".join(offenders)
