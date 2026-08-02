"""Tests for scripts/security/zap_to_sarif.py.

Validates the conversion of OWASP ZAP JSON reports into SARIF 2.1.0 documents
consumable by the GitHub Security tab.

These tests follow the TDD cycle: written before the implementation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_SECURITY = Path(__file__).resolve().parents[2] / "scripts" / "security"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def zap_module():
    """Import the zap_to_sarif module from the scripts directory."""
    if str(SCRIPTS_SECURITY) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_SECURITY))
    import zap_to_sarif  # noqa: WPS433 — intentional runtime import for tests

    return zap_to_sarif


@pytest.fixture()
def sample_report():
    """Load the sample ZAP report fixture."""
    with FIXTURES.joinpath("zap_sample_report.json").open() as handle:
        return json.load(handle)


class TestRiskMapping:
    """ZAP riskcode must map deterministically to SARIF levels."""

    def test_high_maps_to_error(self, zap_module):
        assert zap_module.RISK_TO_LEVEL["3"] == "error"

    def test_medium_maps_to_warning(self, zap_module):
        assert zap_module.RISK_TO_LEVEL["2"] == "warning"

    def test_low_maps_to_note(self, zap_module):
        assert zap_module.RISK_TO_LEVEL["1"] == "note"

    def test_informational_maps_to_none(self, zap_module):
        assert zap_module.RISK_TO_LEVEL["0"] == "none"

    def test_unknown_risk_defaults_to_warning(self, zap_module):
        # Defensive: any unexpected riskcode should be treated as Medium,
        # not silently dropped or crashed.
        assert zap_module.RISK_TO_LEVEL.get("99", "warning") == "warning"


class TestConvertSchema:
    """The SARIF output must conform to v2.1.0 structural requirements."""

    def test_sarif_version_is_2_1_0(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        assert sarif["version"] == "2.1.0"

    def test_has_runs_array(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        assert "runs" in sarif
        assert isinstance(sarif["runs"], list)
        assert len(sarif["runs"]) >= 1

    def test_tool_driver_is_zap(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        driver = sarif["runs"][0]["tool"]["driver"]
        assert driver["name"] == "OWASP ZAP"
        assert "informationUri" in driver

    def test_schema_uri_present(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        assert sarif["$schema"].endswith("sarif-schema-2.1.0.json")


class TestConvertResults:
    """Each ZAP alert instance must become one SARIF result."""

    def test_one_result_per_instance(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        results = sarif["runs"][0].get("results", [])
        # The fixture has 4 alerts with 2+1+1+1 = 5 instances total.
        assert len(results) == 5

    def test_high_alert_results_use_error_level(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        high_results = [r for r in sarif["runs"][0].get("results", []) if r["level"] == "error"]
        # CSP alert (pluginid 10038) has 2 instances, both High risk.
        assert len(high_results) == 2

    def test_medium_alert_results_use_warning_level(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        medium_results = [r for r in sarif["runs"][0].get("results", []) if r["level"] == "warning"]
        # HttpOnly cookie (pluginid 10010) has 1 instance, Medium risk.
        assert len(medium_results) == 1

    def test_results_have_rule_ids(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        for result in sarif["runs"][0].get("results", []):
            assert result["ruleId"].startswith("zap-")
            assert result["ruleId"].replace("zap-", "").isdigit()

    def test_results_have_uri_locations(self, zap_module, sample_report):
        sarif = zap_module.convert(sample_report)
        for result in sarif["runs"][0].get("results", []):
            location = result["locations"][0]["physicalLocation"]["artifactLocation"]
            assert location["uri"].startswith("https://qa.sabatech.dev")


class TestConvertEdgeCases:
    """Edge cases must not crash the converter."""

    def test_empty_site_alerts(self, zap_module):
        empty_report = {
            "@version": "2.14.0",
            "@generated": "2026-08-02T10:00:00.000Z",
            "site": [{"@name": "https://example.com", "alerts": []}],
        }
        sarif = zap_module.convert(empty_report)
        assert sarif["runs"][0].get("results", []) == []

    def test_missing_site_key(self, zap_module):
        minimal_report = {"@version": "2.14.0"}
        sarif = zap_module.convert(minimal_report)
        # Must not raise; produces an empty but valid SARIF document.
        assert sarif["version"] == "2.1.0"
        assert sarif["runs"][0].get("results", []) == []


class TestCliInterface:
    """The CLI must be robust against bad inputs in CI environments."""

    SCRIPT = SCRIPTS_SECURITY / "zap_to_sarif.py"
    FIXTURE = FIXTURES / "zap_sample_report.json"

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_converts_fixture_to_sarif(self, tmp_path):
        out = tmp_path / "report.sarif"
        proc = self._run_cli(str(self.FIXTURE), str(out))
        assert proc.returncode == 0, proc.stderr
        sarif = json.loads(out.read_text())
        assert sarif["version"] == "2.1.0"

    def test_cli_missing_input_exits_zero(self, tmp_path):
        # A missing ZAP report in CI (e.g. scan aborted) must not fail the
        # pipeline at the conversion step. The gate step is responsible for
        # surfacing scan failures.
        out = tmp_path / "report.sarif"
        proc = self._run_cli(str(tmp_path / "nonexistent.json"), str(out))
        assert proc.returncode == 0
        assert "no zap report found" in proc.stderr.lower()

    def test_cli_invalid_json_exits_one(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        out = tmp_path / "report.sarif"
        proc = self._run_cli(str(bad), str(out))
        assert proc.returncode == 1
        assert "invalid json" in proc.stderr.lower()
