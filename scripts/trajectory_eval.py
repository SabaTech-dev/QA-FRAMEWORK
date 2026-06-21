#!/usr/bin/env python3
"""CI gate script: run trajectory evaluation and fail if below threshold.

Usage:
    python scripts/trajectory_eval.py
    python scripts/trajectory_eval.py --threshold 0.90

Exit codes:
    0 — all metrics above threshold
    1 — one or more metrics below threshold or tests failed

Card: 7e4a76ee-0061-44ce-97c2-d418b461583a
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 0.85


def main():
    parser = argparse.ArgumentParser(description="Trajectory evaluation CI gate")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum pass rate (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--test-path",
        default="tests/deepeval/test_trajectory_metrics.py",
        help="Path to trajectory test file",
    )
    args = parser.parse_args()

    # Ensure reports directory exists
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    report_file = reports_dir / "trajectory-report.json"

    # Run pytest with json output
    print(f"Running trajectory evaluation: {args.test_path}")
    print(f"Threshold: {args.threshold:.0%}")
    print("-" * 60)

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", args.test_path,
            "--json-report",
            f"--json-report-file={report_file}",
            "-v", "--tb=short",
        ],
        capture_output=True,
        text=True,
    )

    # Always print pytest output
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Check if tests passed
    if result.returncode != 0:
        print("=" * 60)
        print("❌ TRAJECTORY EVAL FAILED — tests did not pass")
        sys.exit(1)

    # Parse JSON report for metrics
    try:
        with open(report_file) as f:
            report = json.load(f)

        summary = report.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)

        if total == 0:
            print("⚠️  No tests found in report")
            sys.exit(1)

        pass_rate = passed / total
        print("=" * 60)
        print(f"Total tests:  {total}")
        print(f"Passed:       {passed}")
        print(f"Failed:       {failed}")
        print(f"Pass rate:    {pass_rate:.2%}")

        if pass_rate < args.threshold:
            print(f"❌ PASS RATE {pass_rate:.2%} BELOW THRESHOLD {args.threshold:.0%}")
            sys.exit(1)

        print(f"✅ PASS RATE {pass_rate:.2%} ≥ THRESHOLD {args.threshold:.0%}")
        sys.exit(0)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️  Could not parse report: {e}")
        # If tests passed but no report, still succeed
        print("✅ Tests passed (no JSON report available)")
        sys.exit(0)


if __name__ == "__main__":
    main()
