"""Vendor parity guard: dashboard/backend copy must match the repo-level module.

The dashboard ships a vendored copy of ``src/infrastructure/qa_visual`` under
``dashboard/backend/src/infrastructure/qa_visual`` (same pattern as the cache
module) because the Docker build context only includes ``dashboard/backend``.
These two copies WILL drift silently unless a test fails loudly. If a file
changes on either side, re-copy the module:

    cp src/infrastructure/qa_visual/*.py dashboard/backend/src/infrastructure/qa_visual/

Skipped automatically when the vendored copy is absent (e.g. slim deploys that
only run the repo-level suite).
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "src" / "infrastructure" / "qa_visual"
VENDOR_DIR = REPO_ROOT / "dashboard" / "backend" / "src" / "infrastructure" / "qa_visual"

pytestmark = pytest.mark.skipif(
    not VENDOR_DIR.is_dir(), reason="vendored qa_visual copy not present"
)


def _py_files(directory: Path) -> dict[str, str]:
    return {p.name: p.read_text() for p in sorted(directory.glob("*.py"))}


def test_vendored_copy_exists():
    assert VENDOR_DIR.is_dir(), "dashboard vendored qa_visual module is missing"
    assert (VENDOR_DIR / "__init__.py").is_file()


def test_vendored_copy_matches_source_file_by_file():
    source = _py_files(SOURCE_DIR)
    vendored = _py_files(VENDOR_DIR)
    assert set(source) == set(vendored), (
        f"file sets differ: only in source={set(source) - set(vendored)}, "
        f"only in vendored={set(vendored) - set(source)}"
    )
    drifted = [name for name, content in source.items() if vendored[name] != content]
    assert not drifted, (
        f"vendored qa_visual copy drifted from src/ in: {drifted}. "
        "Re-copy with: cp src/infrastructure/qa_visual/*.py "
        "dashboard/backend/src/infrastructure/qa_visual/"
    )
