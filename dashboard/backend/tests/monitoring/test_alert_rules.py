"""
Tests for Prometheus alert rules shipped in the repo

Covers PR #106 follow-up (card 5221c63f, AC-1):
- rate_limit_backend_failures_total > 0 must raise an alert (security
  condition for default fail-open in BETA)
- The alert expression must reference the exact counter exported by
  middleware.rate_limit (guards against silent metric renames)
"""

from pathlib import Path

import pytest

pytest.importorskip("yaml")

from middleware.rate_limit import RATE_LIMIT_BACKEND_FAILURES

RULES_FILE = (
    Path(__file__).resolve().parents[3]
    / "monitoring"
    / "prometheus"
    / "alerts"
    / "qa-framework-alerts.yml"
)


def _load_rules():
    import yaml

    with open(RULES_FILE) as f:
        return yaml.safe_load(f)


def _find_alert(rules, name):
    for group in rules.get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("alert") == name:
                return rule
    return None


class TestRateLimitBackendFailuresAlert:
    """Alert on rate limit backing-store failures (fail-open visibility)"""

    def test_rules_file_parses(self):
        rules = _load_rules()
        assert rules.get("groups"), "no alert groups found"

    def test_alert_exists(self):
        assert _find_alert(_load_rules(), "RateLimitBackendFailures") is not None

    def test_expr_fires_above_zero(self):
        rule = _find_alert(_load_rules(), "RateLimitBackendFailures")
        assert "rate_limit_backend_failures_total > 0" in rule["expr"]

    def test_expr_matches_exported_counter_name(self):
        """The expr must use the counter actually exported by the middleware.

        prometheus_client appends the _total suffix to Counter names, so an
        alert on any other spelling would never fire.
        """
        rule = _find_alert(_load_rules(), "RateLimitBackendFailures")
        exported = RATE_LIMIT_BACKEND_FAILURES._name + "_total"
        assert exported in rule["expr"]

    def test_labels_and_annotations(self):
        rule = _find_alert(_load_rules(), "RateLimitBackendFailures")
        assert rule["labels"]["severity"] in ("warning", "critical")
        assert rule["annotations"].get("summary")
        assert rule["annotations"].get("description")
