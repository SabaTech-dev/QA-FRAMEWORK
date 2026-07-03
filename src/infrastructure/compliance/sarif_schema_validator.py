"""
SARIF 2.1.0 Schema Validator

Validates SARIF reports against the official OASIS specification
to ensure compliance with SARIF 2.1.0 schema.

Security: Prevents malformed/injected SARIF from entering CI/CD pipelines.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

# Cache the schema to avoid repeated downloads
_SARIF_SCHEMA_CACHE: Optional[Dict[str, Any]] = None


def get_sarif_schema() -> Dict[str, Any]:
    """
    Load SARIF 2.1.0 JSON schema.

    Downloads from OASIS spec if not cached.
    Fallbacks to local file if download fails.

    Returns:
        Dict containing the SARIF 2.1.0 JSON schema

    Raises:
        RuntimeError: If schema cannot be loaded
    """
    global _SARIF_SCHEMA_CACHE

    if _SARIF_SCHEMA_CACHE is not None:
        return _SARIF_SCHEMA_CACHE

    # Try to download from OASIS
    schema_url = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json"

    try:
        with urlopen(schema_url, timeout=10) as response:
            schema_data = json.loads(response.read().decode('utf-8'))
        _SARIF_SCHEMA_CACHE = schema_data
        return schema_data
    except (URLError, HTTPError) as e:
        # Fallback to local file
        local_path = Path(__file__).parent / "sarif_schema_2.1.0.json"
        if local_path.exists():
            with open(local_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            _SARIF_SCHEMA_CACHE = schema_data
            return schema_data
        else:
            raise RuntimeError(
                f"Cannot load SARIF schema from {schema_url} or local fallback. "
                f"Error: {e}"
            )


def validate_sarif_report(report_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a SARIF report against the SARIF 2.1.0 JSON schema.

    Args:
        report_dict: Dictionary representation of SARIF report

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Security checks:
    - Required fields: version, runs
    - Version must be "2.1.0"
    - Schema URI must be valid
    - Runs array must be valid
    """
    # Quick security checks before schema validation
    if not isinstance(report_dict, dict):
        return False, "SARIF report must be a JSON object"

    # Check required fields
    if "version" not in report_dict:
        return False, "Missing required field: version"

    if report_dict["version"] != "2.1.0":
        return False, f"Invalid version: {report_dict['version']}, expected '2.1.0'"

    if "runs" not in report_dict:
        return False, "Missing required field: runs"

    if not isinstance(report_dict["runs"], list):
        return False, "Field 'runs' must be an array"

    # Check schema URI format (basic)
    if "$schema" in report_dict:
        schema_uri = report_dict["$schema"]
        if not isinstance(schema_uri, str):
            return False, "Field '$schema' must be a string"
        if not schema_uri.startswith(("http://", "https://")):
            return False, "Field '$schema' must be a valid HTTP(S) URI"

    # Full schema validation with jsonschema
    try:
        import jsonschema

        schema = get_sarif_schema()
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(report_dict))

        if errors:
            # Format the first few errors
            error_messages = []
            for error in errors[:5]:  # Limit to first 5 errors
                path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                error_messages.append(f"{path}: {error.message}")

            return False, "Schema validation failed: " + "; ".join(error_messages)

        # Schema valid — now check our stricter requirements
        strict_error = _validate_strict_requirements(report_dict)
        if strict_error:
            return False, strict_error

        return True, None

    except ImportError:
        # jsonschema not installed - do basic structural validation
        return _basic_sarif_validation(report_dict)


def _validate_strict_requirements(report_dict: Dict[str, Any]) -> Optional[str]:
    """
    Check QA-FRAMEWORK-specific requirements beyond SARIF 2.1.0 schema.

    The base SARIF schema allows results without ruleId/level,
    but our compliance pipeline requires them for rule taxonomy mapping.

    Returns:
        Error message if validation fails, None if OK
    """
    for run_idx, run in enumerate(report_dict.get("runs", [])):
        for res_idx, result in enumerate(run.get("results", [])):
            if "ruleId" not in result:
                return (
                    f"Run {run_idx} result {res_idx}: "
                    f"ruleId is required by QA-FRAMEWORK"
                )
            if "level" not in result:
                return (
                    f"Run {run_idx} result {res_idx}: "
                    f"level is required by QA-FRAMEWORK"
                )
    return None


def _basic_sarif_validation(report_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Basic SARIF validation when jsonschema is not available.

    Checks critical structural requirements without full schema validation.
    """
    # Check version first
    if "version" not in report_dict:
        return False, "Missing required field: version"

    if report_dict["version"] != "2.1.0":
        return False, f"Invalid version: {report_dict['version']}, expected '2.1.0'"

    # Check runs
    if "runs" not in report_dict:
        return False, "Missing required field: runs"

    if not isinstance(report_dict["runs"], list):
        return False, "Field 'runs' must be an array"

    if not report_dict["runs"]:
        # Empty runs is valid (no results)
        return True, None

    for run_idx, run in enumerate(report_dict["runs"]):
        if not isinstance(run, dict):
            return False, f"Run {run_idx} must be a JSON object"

        # Check tool
        if "tool" not in run:
            return False, f"Run {run_idx} missing required field: tool"

        tool = run["tool"]
        if not isinstance(tool, dict):
            return False, f"Run {run_idx} tool must be a JSON object"

        if "driver" not in tool:
            return False, f"Run {run_idx} tool.driver missing"

        driver = tool["driver"]
        if not isinstance(driver, dict):
            return False, f"Run {run_idx} tool.driver must be a JSON object"

        if "name" not in driver:
            return False, f"Run {run_idx} tool.driver.name missing"

        # Check results structure if present
        if "results" in run:
            if not isinstance(run["results"], list):
                return False, f"Run {run_idx} results must be an array"

            for res_idx, result in enumerate(run["results"]):
                if not isinstance(result, dict):
                    return False, f"Run {run_idx} result {res_idx} must be a JSON object"

                # Check required fields
                if "ruleId" not in result:
                    return False, f"Run {run_idx} result {res_idx} missing ruleId"

                if "level" not in result:
                    return False, f"Run {run_idx} result {res_idx} missing level"

                if result["level"] not in ("error", "warning", "note", "none"):
                    return False, (
                        f"Run {run_idx} result {res_idx} has invalid level: {result['level']}"
                    )

                if "message" not in result:
                    return False, f"Run {run_idx} result {res_idx} missing message"

                if not isinstance(result["message"], dict):
                    return False, f"Run {run_idx} result {res_idx} message must be a JSON object"

                if "text" not in result["message"] and "id" not in result["message"]:
                    return False, f"Run {run_idx} result {res_idx} message missing text or id"

    return True, None


class SARIFValidationError(Exception):
    """Raised when SARIF report validation fails."""

    def __init__(self, message: str, report_dict: Optional[Dict[str, Any]] = None):
        self.message = message
        self.report_dict = report_dict
        super().__init__(message)


def validate_or_raise(report_dict: Dict[str, Any]) -> None:
    """
    Validate SARIF report and raise exception if invalid.

    Args:
        report_dict: Dictionary representation of SARIF report

    Raises:
        SARIFValidationError: If report is invalid
    """
    is_valid, error_message = validate_sarif_report(report_dict)
    if not is_valid:
        raise SARIFValidationError(error_message, report_dict)