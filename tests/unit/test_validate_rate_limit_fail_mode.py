"""Tests for scripts/validate_rate_limit_fail_mode.py (card 5221c63f item 2).

The deploy/CI fail-fast gate for RATE_LIMIT_FAIL_MODE: a typo like "cloed"
must produce a clear error and a non-zero exit, never a silent fallback to
open (which is what the middleware default effectively does today).
"""

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validate_rate_limit_fail_mode.py"


def run_validator(*compose_paths: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(p) for p in compose_paths]],
        capture_output=True,
        text=True,
    )


def write_compose(tmp_path: Path, environment_block: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    compose = tmp_path / "docker-compose.test.yml"
    compose.write_text(
        textwrap.dedent(
            f"""\
            services:
              backend:
                image: backend:test
                environment:
            {environment_block}
            """
        )
    )
    return compose


def test_valid_closed_list_style_passes(tmp_path):
    compose = write_compose(tmp_path, "      - RATE_LIMIT_FAIL_MODE=closed")
    result = run_validator(compose)
    assert result.returncode == 0, result.stderr


def test_valid_open_dict_style_passes(tmp_path):
    compose = write_compose(tmp_path, "      RATE_LIMIT_FAIL_MODE: open")
    result = run_validator(compose)
    assert result.returncode == 0, result.stderr


def test_case_and_whitespace_are_tolerated(tmp_path):
    # The middleware normalises via strip().lower() before comparing.
    compose = write_compose(tmp_path, "      - RATE_LIMIT_FAIL_MODE= CLOSED ")
    result = run_validator(compose)
    assert result.returncode == 0, result.stderr


def test_invalid_value_fails_with_clear_error(tmp_path):
    compose = write_compose(tmp_path, "      - RATE_LIMIT_FAIL_MODE=cloed")
    result = run_validator(compose)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "cloed" in combined, "error must name the offending value"
    assert str(compose) in combined, "error must name the offending file"
    assert "open" in combined and "closed" in combined, "error must list the allowed values"


def test_missing_variable_passes(tmp_path):
    compose = write_compose(tmp_path, "      - SOME_OTHER_VAR=1")
    result = run_validator(compose)
    assert result.returncode == 0, result.stderr


def test_one_bad_file_fails_the_whole_run(tmp_path):
    good = write_compose(tmp_path / "good", "      - RATE_LIMIT_FAIL_MODE=open")
    bad = write_compose(tmp_path / "bad", "      - RATE_LIMIT_FAIL_MODE=fail-closed")
    result = run_validator(good, bad)
    assert result.returncode != 0
