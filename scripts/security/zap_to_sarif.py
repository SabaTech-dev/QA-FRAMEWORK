#!/usr/bin/env python3
"""Convert an OWASP ZAP JSON report into a SARIF 2.1.0 document.

The ``zaproxy/action-baseline`` GitHub Action does not emit SARIF natively;
it can produce a JSON report via ``cmd_options: '-J zap_report.json'``. This
script turns that JSON into SARIF so the findings appear in the GitHub
Security tab via ``github/codeql-action/upload-sarif``.

Usage::

    python3 zap_to_sarif.py <zap_report.json> <output.sarif>

Design notes:
    - One SARIF result is emitted per ZAP alert *instance* (not per alert),
      matching how GitHub Code Scoring groups findings by location.
    - ZAP riskcode maps to SARIF level: 3->error, 2->warning, 1->note, 0->none.
      This is the convention recommended by the SARIF TC and used by GitHub.
    - A missing input file is a soft failure (exit 0): the caller (the CI
      gate) is responsible for surfacing scan aborts, not the converter.

Exit codes:
    0 — SARIF written, or input missing (soft fail).
    1 — Invalid JSON, or output path not writable.
    2 — CLI misuse (wrong number of arguments).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# Mapping of ZAP riskcode to SARIF level.
# https://www.zaproxy.org/docs/alerts/
#   3 = High           -> error   (fails the gate)
#   2 = Medium         -> warning
#   1 = Low            -> note
#   0 = Informational  -> none    (hidden in Security tab by default)
RISK_TO_LEVEL: dict[str, str] = {
    "3": "error",
    "2": "warning",
    "1": "note",
    "0": "none",
}
DEFAULT_LEVEL = "warning"

# CVSS-like severity (0.0-10.0) for the GitHub Security tab, derived from
# the ZAP riskcode. Drives the severity badge shown next to each finding.
# https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning
RISK_TO_SEVERITY: dict[str, str] = {
    "3": "9.0",  # High
    "2": "6.0",  # Medium
    "1": "3.0",  # Low
    "0": "0.0",  # Informational
}
DEFAULT_SEVERITY = "0.0"

SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json"
)
ZAP_INFO_URI = "https://www.zaproxy.org/"
ZAP_ALERT_DOCS = "https://www.zaproxy.org/docs/alerts/"


def _level_for(riskcode: Any) -> str:
    """Return the SARIF level for a ZAP riskcode, defaulting to warning."""
    return RISK_TO_LEVEL.get(str(riskcode), DEFAULT_LEVEL)


def _severity_for(riskcode: Any) -> str:
    """Return a CVSS-like severity string for the GitHub Security tab."""
    return RISK_TO_SEVERITY.get(str(riskcode), DEFAULT_SEVERITY)


def _build_rules(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the SARIF rules array from the unique ZAP pluginids."""
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for alert in alerts:
        pluginid = str(alert.get("pluginid", "unknown"))
        if pluginid in seen or pluginid == "unknown":
            continue
        seen.add(pluginid)
        name = alert.get("name") or alert.get("alert") or f"ZAP rule {pluginid}"
        rules.append(
            {
                "id": f"zap-{pluginid}",
                "name": name,
                "shortDescription": {"text": name},
                "fullDescription": {"text": alert.get("desc", name)[:5000] or name},
                # Stable, single-URI help link. ZAP's "reference" field holds
                # free-form multi-line text with several URLs, which is not a
                # valid single helpUri; the docs index is authoritative.
                "helpUri": f"{ZAP_ALERT_DOCS}#{pluginid}",
                # NOTE: defaultConfiguration.level is intentionally omitted.
                # Each result carries its own level (derived from riskcode),
                # which keeps the CI gate's level-based counting accurate.
                "properties": {
                    "zap_pluginid": pluginid,
                    "zap_riskdesc": alert.get("riskdesc", ""),
                    "zap_wascid": alert.get("wascid", ""),
                    "security-severity": _severity_for(alert.get("riskcode")),
                    "tags": ["security", "DAST", "owasp-zap"],
                },
            }
        )
    return rules


def _build_results(site: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten every alert instance into a SARIF result."""
    results: list[dict[str, Any]] = []
    for alert in site.get("alerts", []):
        pluginid = str(alert.get("pluginid", "unknown"))
        level = _level_for(alert.get("riskcode"))
        message = alert.get("name") or alert.get("alert") or "ZAP finding"
        for index, instance in enumerate(alert.get("instances", [])):
            uri = instance.get("uri", "")
            results.append(
                {
                    "ruleId": f"zap-{pluginid}",
                    "level": level,
                    "message": {"text": message},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": uri},
                            }
                        }
                    ],
                    "partialFingerprints": {
                        "zap/pluginid": pluginid,
                        "zap/instance": str(index),
                        "zap/method": instance.get("method", ""),
                        "zap/param": instance.get("param", ""),
                    },
                    "properties": {
                        "confidence": alert.get("confidence", ""),
                        "riskdesc": alert.get("riskdesc", ""),
                        "solution": alert.get("solution", ""),
                    },
                }
            )
    return results


def convert(zap_report: dict[str, Any]) -> dict[str, Any]:
    """Convert a parsed ZAP JSON report dict into a SARIF 2.1.0 dict.

    Defensive against missing keys: an empty/aborted scan produces a valid
    SARIF document with no results, rather than raising.
    """
    sites = zap_report.get("site", []) or []
    all_alerts: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []
    for site in sites:
        all_alerts.extend(site.get("alerts", []) or [])
        all_results.extend(_build_results(site))

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OWASP ZAP",
                        "version": str(zap_report.get("@version", "unknown")),
                        "informationUri": ZAP_INFO_URI,
                        "rules": _build_rules(all_alerts),
                    }
                },
                "results": all_results,
            }
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert an OWASP ZAP JSON report to SARIF 2.1.0.",
    )
    parser.add_argument("input", help="Path to the ZAP JSON report")
    parser.add_argument("output", help="Path to write the SARIF document")
    args = parser.parse_args(argv)

    input_path = args.input
    output_path = args.output

    # Soft fail: a missing report in CI means the scan aborted upstream.
    # The gate step is responsible for failing the build on that case.
    try:
        with open(input_path, encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        print(
            f"warn: no ZAP report found at {input_path}; writing empty SARIF",
            file=sys.stderr,
        )
        empty = {
            "$schema": SARIF_SCHEMA,
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "OWASP ZAP",
                            "informationUri": ZAP_INFO_URI,
                            "rules": [],
                        }
                    },
                    "results": [],
                }
            ],
        }
        try:
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump(empty, handle, indent=2)
        except OSError as exc:
            print(f"error: cannot write output: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        zap_report = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {input_path}: {exc}", file=sys.stderr)
        return 1

    sarif = convert(zap_report)

    try:
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(sarif, handle, indent=2)
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return 1

    results = sarif["runs"][0].get("results", [])
    print(
        f"ok: converted {len(results)} findings to {output_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
