#!/usr/bin/env python3
"""Fail-fast validation of RATE_LIMIT_FAIL_MODE (card 5221c63f item 2).

The rate-limiter middleware (line F-1) reads RATE_LIMIT_FAIL_MODE and
silently behaves as "open" for any value other than "closed" — a typo like
"cloed" would quietly disable fail-closed in production. This gate runs in
CI and pre-deploy so an invalid value blocks the deploy with a clear error
instead of silently falling back to open.

Usage:
    python scripts/validate_rate_limit_fail_mode.py [compose.yml ...]

With no arguments it scans every tracked docker-compose*.yml at the repo
root. Exit code 0 = all present values valid (or variable absent), 1 = at
least one invalid value.
"""

import sys
from pathlib import Path

import yaml

VALID_MODES = {"open", "closed"}
VAR_NAME = "RATE_LIMIT_FAIL_MODE"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def extract_fail_mode(compose_path: Path) -> str | None:
    """Return the RATE_LIMIT_FAIL_MODE declared in a compose file, if any.

    Handles both environment syntaxes: list ("- KEY=value") and mapping
    ("KEY: value"), across all services.
    """
    doc = yaml.safe_load(compose_path.read_text()) or {}
    for service in (doc.get("services") or {}).values():
        environment = service.get("environment") or {}
        if isinstance(environment, dict):
            if VAR_NAME in environment:
                return str(environment[VAR_NAME])
        else:  # list of "KEY=value" strings
            for entry in environment:
                if entry.startswith(f"{VAR_NAME}="):
                    return entry.split("=", 1)[1]
    return None


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]]
    if not paths:
        paths = sorted(repo_root().glob("docker-compose*.yml"))
        if not paths:
            print(f"no docker-compose*.yml found under {repo_root()}")
            return 0

    failures: list[str] = []
    for path in paths:
        try:
            value = extract_fail_mode(path)
        except Exception as exc:  # unparsable compose must also block
            print(f"ERROR: cannot parse {path}: {exc}")
            failures.append(str(path))
            continue
        if value is None:
            continue
        if value.strip().lower() not in VALID_MODES:
            failures.append(
                f"ERROR: {path}: {VAR_NAME}={value!r} is invalid. "
                f"Allowed values: {', '.join(sorted(VALID_MODES))}. "
                "Any other value silently falls back to open in the "
                "middleware — fix the typo or remove the variable."
            )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"OK: {VAR_NAME} values valid across {len(paths)} compose file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
