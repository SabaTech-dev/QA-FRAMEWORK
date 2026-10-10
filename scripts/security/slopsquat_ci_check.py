#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
slopsquat_ci_check.py — CI check-only wrapper for guard_agent_install.py
(cards d859cee2 / 45644f9f, integration I-3)

Extracts NEW dependency entries added in a diff (requirements*.txt,
package.json) and verifies each against the official registry by invoking
the slopsquatting guard in `check` mode with --json. Fails on any BLOCK
(404 = hallucinated package, or fail-closed registry error).

Scope note: this is check-only (existence), per card d859cee2 §I-3
"fail the PR si 404". Version pinning (POL-3) applies to interactive
agent installs via `cmd` mode, not to CI validation of manifests.
package-lock.json / yarn.lock diffs are not parsed (v1 limitation).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_agent_install import parse_pip_spec, parse_npm_spec  # noqa: E402

GUARD = Path(__file__).resolve().parent / "guard_agent_install.py"
NPM_DEP_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")
REQ_FILENAME_RE = re.compile(r"^requirements[\w.-]*\.txt$")
PIP_OPTION_RE = re.compile(r"^(?:-[A-Za-z]|--)")


def git(*args):
    """git output as text; empty string on failure (e.g. file absent in base)."""
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def added_lines(diff_text):
    """Unified diff text -> list of added line contents (no '+++' header)."""
    return [l[1:] for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]


def req_spec_from_line(line):
    """A requirements.txt line -> (name, version|None) or None if not a package spec."""
    spec = line.split("#", 1)[0].strip()
    if not spec or PIP_OPTION_RE.match(spec):
        return None
    name, ver, _pinned = parse_pip_spec(spec)
    return (name, ver) if name else None


def added_npm_specs(base_json, head_json):
    """Old/new package.json contents -> [(name, version|None)] added in head."""

    def deps(text):
        try:
            doc = json.loads(text) if text else {}
        except json.JSONDecodeError:
            return {}
        merged = {}
        for section in NPM_DEP_SECTIONS:
            merged.update(doc.get(section) or {})
        return merged

    base, head = deps(base_json), deps(head_json)
    specs = []
    for name in sorted(set(head) - set(base)):
        _n, ver, _pinned = parse_npm_spec("%s@%s" % (name, head[name]))
        specs.append((name, ver))
    return specs


def collect_entries(base, head):
    """[(eco, name, version|None)] for dependency entries added between base..head."""
    entries = []
    for path in git("diff", "--name-only", "--diff-filter=ACMRT", base, head).splitlines():
        path = path.strip()
        if not path:
            continue
        basename = path.rsplit("/", 1)[-1]
        if REQ_FILENAME_RE.match(basename):
            for line in added_lines(git("diff", "-U0", base, head, "--", path)):
                spec = req_spec_from_line(line)
                if spec:
                    entries.append(("pypi", *spec))
        elif basename == "package.json":
            for name, ver in added_npm_specs(
                git("show", "%s:%s" % (base, path)), git("show", "%s:%s" % (head, path))
            ):
                entries.append(("npm", name, ver))
    return entries


def run_guard(eco, name, version):
    """Invoke the guard in check mode (--json). Returns (exit_code, detail)."""
    cmd = [sys.executable, str(GUARD), "check", eco, name]
    if version:
        cmd.append(version)
    cmd.append("--json")
    out = subprocess.run(cmd, capture_output=True, text=True)
    try:
        detail = json.loads(out.stdout).get("detail", "")
    except (json.JSONDecodeError, AttributeError):
        detail = (out.stdout or out.stderr).strip()[:200]
    return out.returncode, detail


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="base sha (PR base)")
    ap.add_argument("--head", default="HEAD", help="head sha (default HEAD)")
    args = ap.parse_args(argv)

    entries = collect_entries(args.base, args.head)
    if not entries:
        print("slopsquatting-guard: no new dependency entries to check")
        return 0

    failures, worst = [], 0
    for eco, name, version in entries:
        code, detail = run_guard(eco, name, version)
        worst = max(worst, code)
        status = "OK" if code == 0 else "BLOCK(%d)" % code
        print(
            "[%s] %-4s %s%s — %s"
            % (
                status,
                eco,
                name,
                "@" + version if version and eco == "npm" else ("==" + version if version else ""),
                detail,
            )
        )
        if code != 0:
            failures.append((eco, name, code))

    if failures:
        print(
            "slopsquatting-guard: %d/%d new dependency entries BLOCKED (404 hallucination or fail-closed)"
            % (len(failures), len(entries))
        )
        return 1
    print(
        "slopsquatting-guard: all %d new dependency entries verified in official registries"
        % len(entries)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
