"""Unit tests for scripts/security/slopsquat_ci_check.py (cards d859cee2/45644f9f).

Covers the pure parsing/aggregation helpers only — no network. The guard
itself (`guard_agent_install.py`) carries its own self-verifying demo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "security"))

from slopsquat_ci_check import added_lines, added_npm_specs, req_spec_from_line


class TestAddedLines:
    def test_extracts_only_added_lines(self):
        diff = "+++ b/requirements.txt\n--- a/requirements.txt\n+requests==2.34.2\n-old==1.0.0\n+httpx==0.26.0\n"
        assert added_lines(diff) == ["requests==2.34.2", "httpx==0.26.0"]

    def test_empty_diff(self):
        assert added_lines("") == []


class TestReqSpecFromLine:
    def test_pinned_with_inline_comment(self):
        assert req_spec_from_line("requests==2.34.2  # aligned with pyproject") == (
            "requests",
            "2.34.2",
        )

    def test_extras(self):
        assert req_spec_from_line("allure-pytest[extras]==2.13.5") == ("allure-pytest", "2.13.5")

    def test_unpinned_range_checks_existence_only(self):
        assert req_spec_from_line("locust>=2.31") == ("locust", None)

    def test_skips_comments_blank_and_options(self):
        assert req_spec_from_line("# QA-FRAMEWORK - Dependencies") is None
        assert req_spec_from_line("") is None
        assert req_spec_from_line("-r base.txt") is None
        assert req_spec_from_line("--index-url https://example.com") is None


class TestAddedNpmSpecs:
    def test_added_dependencies_with_version(self):
        base = '{"dependencies": {"react": "18.0.0"}}'
        head = '{"dependencies": {"react": "18.0.0", "express": "4.21.2"}}'
        assert added_npm_specs(base, head) == [("express", "4.21.2")]

    def test_caret_spec_yields_existence_only(self):
        assert added_npm_specs("{}", '{"dependencies": {"vite": "^8.3.0"}}') == [("vite", None)]

    def test_scoped_package(self):
        assert added_npm_specs(None, '{"devDependencies": {"@scope/pkg": "1.2.3"}}') == [
            ("@scope/pkg", "1.2.3")
        ]

    def test_new_file_treats_base_as_empty(self):
        assert added_npm_specs(None, '{"dependencies": {"left-pad": "1.3.0"}}') == [
            ("left-pad", "1.3.0")
        ]

    def test_removed_only_yields_nothing(self):
        assert added_npm_specs('{"dependencies": {"left-pad": "1.3.0"}}', "{}") == []

    def test_invalid_base_json_is_tolerated(self):
        assert added_npm_specs("not json", '{"dependencies": {"left-pad": "1.3.0"}}') == [
            ("left-pad", "1.3.0")
        ]
