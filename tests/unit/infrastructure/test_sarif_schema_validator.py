"""
Tests for SARIF Schema Validator

Covers:
- Schema validation against SARIF 2.1.0 spec
- Basic validation fallback when jsonschema not available
- Required field validation
- Structural validation
- Error message formatting
"""

import pytest
import json

from src.infrastructure.compliance.sarif_schema_validator import (
    validate_sarif_report,
    validate_or_raise,
    SARIFValidationError,
    get_sarif_schema,
    _basic_sarif_validation,
)


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def minimal_valid_sarif():
    """Minimal valid SARIF 2.1.0 report."""
    return {
        "version": "2.1.0",
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "qa-framework",
                        "version": "1.0.0",
                    }
                },
                "results": [],
            }
        ],
    }


@pytest.fixture
def sarif_with_result():
    """SARIF report with a single result."""
    return {
        "version": "2.1.0",
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "qa-framework",
                        "version": "1.0.0",
                    }
                },
                "results": [
                    {
                        "ruleId": "QA-ACC-001",
                        "level": "error",
                        "kind": "fail",
                        "message": {
                            "text": "Test failed"
                        },
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sarif_with_multiple_results():
    """SARIF report with multiple results."""
    return {
        "version": "2.1.0",
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "qa-framework",
                        "version": "1.0.0",
                    }
                },
                "results": [
                    {
                        "ruleId": "QA-ACC-001",
                        "level": "error",
                        "kind": "fail",
                        "message": {
                            "text": "Test failed"
                        },
                    },
                    {
                        "ruleId": "QA-ACC-002",
                        "level": "warning",
                        "kind": "fail",
                        "message": {
                            "text": "Test warning"
                        },
                    },
                ],
            }
        ],
    }


# ========================================================================
# Schema Loading
# ========================================================================

class TestSchemaLoading:
    def test_get_sarif_schema_returns_dict(self):
        """Schema should be loaded as a dict."""
        schema = get_sarif_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"

    def test_get_sarif_schema_cached(self):
        """Schema should be cached on second call."""
        schema1 = get_sarif_schema()
        schema2 = get_sarif_schema()
        assert schema1 is schema2


# ========================================================================
# Valid Reports
# ========================================================================

class TestValidReports:
    def test_minimal_valid_sarif_passes(self, minimal_valid_sarif):
        """Minimal valid SARIF should pass validation."""
        is_valid, error = validate_sarif_report(minimal_valid_sarif)
        assert is_valid is True
        assert error is None

    def test_sarif_with_result_passes(self, sarif_with_result):
        """SARIF with a valid result should pass."""
        is_valid, error = validate_sarif_report(sarif_with_result)
        assert is_valid is True
        assert error is None

    def test_sarif_with_multiple_results_passes(self, sarif_with_multiple_results):
        """SARIF with multiple results should pass."""
        is_valid, error = validate_sarif_report(sarif_with_multiple_results)
        assert is_valid is True
        assert error is None


# ========================================================================
# Invalid Reports - Required Fields
# ========================================================================

class TestInvalidReportsRequiredFields:
    def test_missing_version_fails(self):
        """Report without version should fail."""
        report = {
            "runs": []
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "version" in error

    def test_invalid_version_fails(self):
        """Report with wrong version should fail."""
        report = {
            "version": "2.0.0",
            "runs": []
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "2.1.0" in error

    def test_missing_runs_fails(self):
        """Report without runs should fail."""
        report = {
            "version": "2.1.0"
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "runs" in error

    def test_runs_not_array_fails(self):
        """Report with runs as object should fail."""
        report = {
            "version": "2.1.0",
            "runs": {}
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "array" in error


# ========================================================================
# Invalid Reports - Schema URI
# ========================================================================

class TestInvalidReportsSchemaURI:
    def test_schema_not_string_fails(self):
        """Schema URI must be a string."""
        report = {
            "version": "2.1.0",
            "$schema": 123,
            "runs": []
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "string" in error

    def test_schema_not_uri_fails(self):
        """Schema URI must be HTTP(S)."""
        report = {
            "version": "2.1.0",
            "$schema": "file://local/schema.json",
            "runs": []
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "HTTP" in error


# ========================================================================
# Invalid Reports - Run Structure
# ========================================================================

class TestInvalidReportsRunStructure:
    def test_run_not_object_fails(self):
        """Run must be an object."""
        report = {
            "version": "2.1.0",
            "runs": ["not an object"]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "object" in error

    def test_run_missing_tool_fails(self):
        """Run must have tool field."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "results": []
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "tool" in error

    def test_tool_missing_driver_fails(self):
        """Tool must have driver field."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "name": "qa-framework"
                    },
                    "results": []
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "driver" in error

    def test_driver_missing_name_fails(self):
        """Driver must have name field."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "version": "1.0.0"
                        }
                    },
                    "results": []
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "name" in error


# ========================================================================
# Invalid Reports - Result Structure
# ========================================================================

class TestInvalidReportsResultStructure:
    def test_result_not_object_fails(self):
        """Result must be an object."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": ["not an object"]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "object" in error

    def test_result_missing_rule_id_fails(self):
        """Result must have ruleId."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "level": "error",
                            "message": {
                                "text": "test"
                            }
                        }
                    ]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "ruleId" in error

    def test_result_missing_level_fails(self):
        """Result must have level."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "QA-ACC-001",
                            "message": {
                                "text": "test"
                            }
                        }
                    ]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "level" in error

    def test_result_invalid_level_fails(self):
        """Result level must be valid SARIF level."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "QA-ACC-001",
                            "level": "invalid",
                            "message": {
                                "text": "test"
                            }
                        }
                    ]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "level" in error

    def test_result_missing_message_fails(self):
        """Result must have message."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "QA-ACC-001",
                            "level": "error"
                        }
                    ]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "message" in error

    def test_result_message_not_object_fails(self):
        """Result message must be an object."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "QA-ACC-001",
                            "level": "error",
                            "message": "not an object"
                        }
                    ]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "object" in error

    def test_result_message_missing_text_and_id_fails(self):
        """Result message must have text or id."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "QA-ACC-001",
                            "level": "error",
                            "message": {
                                "markdown": "**test**"
                            }
                        }
                    ]
                }
            ]
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "text" in error or "id" in error


# ========================================================================
# Error Messages
# ========================================================================

class TestErrorMessages:
    def test_error_message_includes_field_name(self):
        """Error message should mention the problematic field."""
        report = {
            "version": "2.1.0"
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "runs" in error

    def test_error_message_includes_validation_details(self):
        """Error message should include validation details."""
        report = {
            "version": "1.0.0",
            "runs": []
        }
        is_valid, error = validate_sarif_report(report)
        assert is_valid is False
        assert "1.0.0" in error


# ========================================================================
# validate_or_raise
# ========================================================================

class TestValidateOrRaise:
    def test_valid_report_does_not_raise(self, minimal_valid_sarif):
        """Valid report should not raise exception."""
        validate_or_raise(minimal_valid_sarif)  # Should not raise

    def test_invalid_report_raises_exception(self):
        """Invalid report should raise SARIFValidationError."""
        report = {
            "version": "2.1.0"
        }
        with pytest.raises(SARIFValidationError) as exc_info:
            validate_or_raise(report)

        assert "runs" in str(exc_info.value)

    def test_exception_contains_report_dict(self):
        """Exception should contain the report dict for debugging."""
        report = {
            "version": "2.1.0"
        }
        with pytest.raises(SARIFValidationError) as exc_info:
            validate_or_raise(report)

        assert exc_info.value.report_dict == report


# ========================================================================
# Basic Validation (Fallback)
# ========================================================================

class TestBasicValidation:
    def test_basic_validation_accepts_valid(self, minimal_valid_sarif):
        """Basic validation should accept valid report."""
        is_valid, error = _basic_sarif_validation(minimal_valid_sarif)
        assert is_valid is True
        assert error is None

    def test_basic_validation_rejects_invalid_version(self):
        """Basic validation should reject wrong version."""
        report = {
            "version": "1.0.0",
            "runs": []
        }
        is_valid, error = _basic_sarif_validation(report)
        assert is_valid is False

    def test_basic_validation_rejects_missing_runs(self):
        """Basic validation should reject missing runs."""
        report = {
            "version": "2.1.0"
        }
        is_valid, error = _basic_sarif_validation(report)
        assert is_valid is False

    def test_basic_validation_rejects_invalid_result_level(self):
        """Basic validation should reject invalid result level."""
        report = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "qa-framework"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "QA-ACC-001",
                            "level": "invalid",
                            "message": {
                                "text": "test"
                            }
                        }
                    ]
                }
            ]
        }
        is_valid, error = _basic_sarif_validation(report)
        assert is_valid is False