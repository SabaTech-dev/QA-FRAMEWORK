"""Vendor parity guard: dashboard/backend copy must match the repo-level module.

The dashboard ships a vendored copy of the accuracy_testing module (domain +
infrastructure) under ``dashboard/backend/src`` because its Docker build
context only includes ``dashboard/backend``. These two copies WILL drift
silently unless a test fails loudly. If a file changes on either side,
re-copy the module:

    cp src/domain/accuracy_testing/*.py dashboard/backend/src/domain/accuracy_testing/
    cp src/infrastructure/accuracy_testing/*.py \
       dashboard/backend/src/infrastructure/accuracy_testing/

Skipped automatically when the vendored copy is absent (e.g. slim deploys that
only run the repo-level suite).
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIRS = [
    REPO_ROOT / "src" / "domain" / "accuracy_testing",
    REPO_ROOT / "src" / "infrastructure" / "accuracy_testing",
]
VENDOR_DIRS = [
    REPO_ROOT / "dashboard" / "backend" / "src" / "domain" / "accuracy_testing",
    REPO_ROOT / "dashboard" / "backend" / "src" / "infrastructure" / "accuracy_testing",
]

pytestmark = pytest.mark.skipif(
    not all(d.is_dir() for d in VENDOR_DIRS), reason="vendored accuracy_testing copy not present"
)


def _py_files(directory: Path) -> dict:
    return {p.name: p.read_text() for p in sorted(directory.glob("*.py"))}


def test_vendored_copy_exists():
    for vendor_dir in VENDOR_DIRS:
        assert vendor_dir.is_dir(), f"dashboard vendored module is missing: {vendor_dir}"
        assert (vendor_dir / "__init__.py").is_file()


def test_vendored_copy_matches_source_file_by_file():
    for source_dir, vendor_dir in zip(SOURCE_DIRS, VENDOR_DIRS):
        source = _py_files(source_dir)
        vendored = _py_files(vendor_dir)
        assert set(source) == set(vendored), (
            f"file sets differ in {source_dir.name}: "
            f"only in source={set(source) - set(vendored)}, "
            f"only in vendored={set(vendored) - set(source)}"
        )
        drifted = [name for name, content in source.items() if vendored[name] != content]
        assert not drifted, (
            f"vendored accuracy_testing copy drifted in {source_dir.name}: {drifted}. "
            "Re-copy with: cp src/domain/accuracy_testing/*.py "
            "dashboard/backend/src/domain/accuracy_testing/ && cp "
            "src/infrastructure/accuracy_testing/*.py "
            "dashboard/backend/src/infrastructure/accuracy_testing/"
        )
