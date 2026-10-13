"""Validation of Prometheus alert rules (dashboard/monitoring).

Card 5221c63f item 1: the backend exposes a
``rate_limit_backend_failures_total`` counter (line F-1). A regression in the
rate-limiter backing store must page someone, so the alert rule has to exist
and keep pointing at the right metric.
"""

from pathlib import Path

import pytest
import yaml

ALERTS_FILE = (
    Path(__file__).resolve().parents[4]
    / "dashboard"
    / "monitoring"
    / "prometheus"
    / "alerts"
    / "qa-framework-alerts.yml"
)


@pytest.fixture(scope="module")
def rules_doc() -> dict:
    return yaml.safe_load(ALERTS_FILE.read_text())


@pytest.fixture(scope="module")
def all_alerts(rules_doc) -> list[dict]:
    alerts = [rule for group in rules_doc["groups"] for rule in group["rules"] if "alert" in rule]
    assert alerts, "no alert rules found in qa-framework-alerts.yml"
    return alerts


def _find_alert(all_alerts, name) -> dict:
    matches = [a for a in all_alerts if a["alert"] == name]
    assert matches, f"alert '{name}' not found in qa-framework-alerts.yml"
    return matches[0]


def test_rate_limit_backend_failures_alert_exists(all_alerts):
    alert = _find_alert(all_alerts, "RateLimitBackendFailures")
    assert alert["expr"].strip(), "expr must not be empty"


def test_rate_limit_backend_failures_expr_tracks_the_counter(all_alerts):
    expr = _find_alert(all_alerts, "RateLimitBackendFailures")["expr"]
    assert "rate_limit_backend_failures_total > 0" in expr


def test_rate_limit_backend_failures_has_severity_and_for(all_alerts):
    alert = _find_alert(all_alerts, "RateLimitBackendFailures")
    assert alert["labels"]["severity"] in {"critical", "warning"}
    assert alert["for"], "alert must hold for a grace period before firing"


def test_alert_names_are_unique(all_alerts):
    names = [a["alert"] for a in all_alerts]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"duplicated alert names: {sorted(duplicates)}"
