#!/usr/bin/env python3
"""Export the dashboard backend OpenAPI spec to docs/reference/openapi.yaml.

This is the canonical machine-readable API contract. The human-readable
reference lives in docs/reference/api.md; regenerate this file whenever
backend routes change:

    python scripts/generate_openapi.py

The output file carries an AUTO-GENERATED header; do not edit it by hand.
Note: the root ./openapi.yaml is an unrelated contract-testing example
fixture (see tests/examples/test_contract_examples.py) and is not touched.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "dashboard" / "backend"
OUTPUT_FILE = REPO_ROOT / "docs" / "reference" / "openapi.yaml"

HEADER = """# AUTO-GENERATED from dashboard/backend FastAPI app — do not edit by hand.
# Regenerate with: python scripts/generate_openapi.py
# Human-readable reference: docs/reference/api.md
"""

EXPORT_SNIPPET = """
import json
from main import app
print(json.dumps(app.openapi()))
"""


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-c", EXPORT_SNIPPET],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return 1

    import yaml  # imported here so the error above surfaces first on failure

    spec = json.loads(result.stdout)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w") as fh:
        fh.write(HEADER)
        yaml.dump(spec, fh, sort_keys=False, allow_unicode=True)

    paths = len(spec.get("paths", {}))
    print(f"Wrote {OUTPUT_FILE.relative_to(REPO_ROOT)} ({paths} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
