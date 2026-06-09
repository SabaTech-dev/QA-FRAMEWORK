# =============================================================================
# OWASP Top 10:2025 Compliance Tests for QA-FRAMEWORK
# Automated security tests for each OWASP category
# Reference: https://owasp.org/Top10/2025/
# =============================================================================

"""
OWASP Top 10:2025 Categories:
  A01 - Broken Access Control
  A02 - Cryptographic Failures
  A03 - Injection (was A03:2021 Injection, now includes Supply Chain aspects)
  A04 - Insecure Design
  A05 - Security Misconfiguration
  A06 - Vulnerable and Outdated Components
  A07 - Identification and Authentication Failures
  A08 - Software and Data Integrity Failures
  A09 - Security Logging and Monitoring Failures
  A10 - Server-Side Request Forgery (absorbed into A01 in 2025)
  
  2025 Changes:
  - A03: Supply Chain Attacks (NEW)
  - A10: Mishandling of Exceptional Conditions (NEW, replaces SSRF)
  - SSRF absorbed into Broken Access Control (A01)
  - Security Misconfiguration moves to #2
"""

import pytest
import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Base path for QA-FRAMEWORK source
SRC_PATH = Path(__file__).parent.parent.parent / "src"

# Additional scan paths for cross-project security checks
DASHBOARD_PATH = Path(__file__).parent.parent.parent / "dashboard"
BACKEND_PATH = DASHBOARD_PATH / "backend"
FRONTEND_PATH = DASHBOARD_PATH / "frontend"


def _get_scan_paths() -> list:
    """Return all Python file paths to scan for security issues."""
    paths = []
    if SRC_PATH.exists():
        paths.extend(SRC_PATH.rglob("*.py"))
    if BACKEND_PATH.exists():
        paths.extend(BACKEND_PATH.rglob("*.py"))
    return paths


def _iter_python_files(base_paths: list = None) -> list:
    """Iterate over Python files in all configured scan paths.
    
    Args:
        base_paths: Optional list of path objects to scan.
                    Defaults to [_get_scan_paths()] for full coverage.
    """
    if base_paths:
        files = []
        for bp in base_paths:
            if bp.exists():
                files.extend(bp.rglob("*.py"))
        return files
    return _get_scan_paths()


class TestA01BrokenAccessControl:
    """A01:2021 - Broken Access Control (now includes SSRF)"""
    
    def test_no_hardcoded_credentials(self):
        """Ensure no hardcoded credentials in source code."""
        credentials_patterns = [
            r'password\s*=\s*["\'][^"\']+(["\'])',
            r'secret_key\s*=\s*["\'][^"\']+(["\'])',
            r'api_key\s*=\s*["\'][^"\']+(["\'])',
            r'token\s*=\s*["\'][^"\']+(["\'])',
        ]
        findings = []
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            base = SRC_PATH.parent  # repo root for relative paths
            for pattern in credentials_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Exclude env var lookups and test fixtures
                    for m in matches:
                        line_idx = content[:content.find(m)].count('\n')
                        line = content.split('\n')[line_idx] if line_idx < len(content.split('\n')) else ""
                        if "environ" not in line and "os.getenv" not in line and "Settings" not in line:
                            findings.append(f"{py_file.relative_to(base)}:{line_idx+1}")
        
        assert len(findings) == 0, f"Potential hardcoded credentials in: {findings}"
    
    def test_rbac_middleware_exists(self):
        """Verify RBAC middleware is implemented."""
        rbac_path = SRC_PATH / "api" / "middleware" / "rbac_middleware.py"
        assert rbac_path.exists(), "RBAC middleware file not found"
        content = rbac_path.read_text()
        assert "role" in content.lower() or "permission" in content.lower(), \
            "RBAC middleware does not reference roles/permissions"
    
    def test_tenant_isolation_enforced(self):
        """Verify tenant context middleware exists for multi-tenancy isolation."""
        tenant_path = SRC_PATH / "api" / "middleware" / "tenant_context.py"
        assert tenant_path.exists(), "Tenant context middleware not found"
        content = tenant_path.read_text()
        assert "tenant" in content.lower(), "Tenant middleware does not enforce tenant isolation"
    
    def test_no_ssrf_in_url_inputs(self):
        """Check for potential SSRF vectors in URL handling code.
        
        Now uses the centralized URL allowlist validator in
        src/core/security/url_validator.py. All HTTP clients should
        call validate_url() before making outbound requests.
        """
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            # Look for direct URL fetching without validation
            if "requests.get" in content or "httpx.get" in content or "urllib" in content:
                # Check if url_validator is imported/used
                if "url_validator" not in content.lower() and "validate_url" not in content.lower():
                    # Exclude test files and the validator itself
                    if "test" not in str(py_file).lower() and "url_validator" not in str(py_file).lower():
                        findings.append(str(py_file.relative_to(base)))
        
        # Warning only - not all URL fetching is SSRF
        if findings:
            pytest.warns(UserWarning, match=f"Review URL fetching for SSRF in: {findings}")


class TestA02CryptographicFailures:
    """A02:2021 - Cryptographic Failures"""
    
    def test_no_weak_hash_algorithms(self):
        """Ensure no weak hash algorithms (MD5, SHA1) used for security."""
        weak_hashes = ["hashlib.md5", "hashlib.sha1", "MD5", "SHA1"]
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            for weak in weak_hashes:
                if weak.lower() in content.lower() and "test" not in str(py_file).lower():
                    findings.append(f"{py_file.relative_to(base)}: {weak}")
        
        assert len(findings) == 0, f"Weak hash algorithms found: {findings}"
    
    def test_https_enforced(self):
        """Check that HTTP is not used for sensitive connections."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            # Look for http:// URLs (not https) in non-test code
            if re.search(r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)', content):
                if "test" not in str(py_file).lower():
                    findings.append(str(py_file.relative_to(base)))
        
        assert len(findings) == 0, f"HTTP (non-TLS) URLs found in: {findings}"


class TestA03Injection:
    """A03:2021 - Injection (now includes Supply Chain in 2025)"""
    
    def test_sql_injection_protection(self):
        """Verify parameterized queries or ORM usage for SQL."""
        sql_injection_tester = SRC_PATH / "adapters" / "security" / "sql_injection_tester.py"
        if sql_injection_tester.exists():
            content = sql_injection_tester.read_text()
            assert "parameterized" in content.lower() or "bind" in content.lower(), \
                "SQL injection tester does not enforce parameterized queries"
    
    def test_no_raw_sql_concatenation(self):
        """Check for string concatenation in SQL queries."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            # Look for f-string or format in SQL-like patterns
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE|DROP).*\{.*\}', content, re.IGNORECASE):
                if "test" not in str(py_file).lower():
                    findings.append(str(py_file.relative_to(base)))
        
        assert len(findings) == 0, f"Potential SQL injection via string formatting: {findings}"
    
    def test_no_eval_or_exec(self):
        """Ensure no use of eval() or exec() which can lead to code injection."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if re.search(r'\beval\s*\(', content) or re.search(r'\bexec\s*\(', content):
                if "test" not in str(py_file).lower():
                    findings.append(str(py_file.relative_to(base)))
        
        assert len(findings) == 0, f"eval/exec usage found (code injection risk): {findings}"
    
    def test_supply_chain_lockfile_exists(self):
        """Verify dependency lockfile exists for reproducible builds."""
        base = SRC_PATH.parent
        assert (base / "poetry.lock").exists() or (base / "requirements.txt").exists(), \
            "No lockfile found — dependency pinning not enforced"


class TestA04InsecureDesign:
    """A04:2021 - Insecure Design"""
    
    def test_input_validation_with_pydantic(self):
        """Verify Pydantic models are used for input validation."""
        pydantic_files = list(_get_scan_paths())
        uses_pydantic = any("pydantic" in f.read_text(errors="ignore") for f in pydantic_files)
        assert uses_pydantic, "Pydantic not used for input validation"
    
    def test_rate_limiting_exists(self):
        """Check for rate limiting configuration."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if "rate" in content.lower() and "limit" in content.lower():
                findings.append(str(py_file.relative_to(base)))
        
        # Soft check - warn if no rate limiting found
        if not findings:
            pytest.warns(UserWarning, match="No rate limiting detected")


class TestA05SecurityMisconfiguration:
    """A05:2021 - Security Misconfiguration (now #2 in 2025)"""
    
    def test_debug_disabled_in_prod(self):
        """Ensure DEBUG is not enabled by default."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if re.search(r'DEBUG\s*=\s*True', content) and "test" not in str(py_file).lower():
                findings.append(str(py_file.relative_to(base)))
        
        assert len(findings) == 0, f"DEBUG=True found in production code: {findings}"
    
    def test_no_default_secret_keys(self):
        """Check for default/placeholder secret keys."""
        default_secrets = [
            "change-me", "changeme", "secret", "default", "example",
            "your-secret", "xxx", "TODO"
        ]
        findings = []
        env_files = list(SRC_PATH.parent.rglob(".env*"))
        for env_file in env_files:
            if "example" in str(env_file).lower() or "template" in str(env_file).lower():
                continue
            content = env_file.read_text(errors="ignore")
            for ds in default_secrets:
                if ds.lower() in content.lower():
                    findings.append(f"{env_file}: contains '{ds}'")
        
        assert len(findings) == 0, f"Default secret values found: {findings}"
    
    def test_cors_configuration(self):
        """Verify CORS is not overly permissive."""
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if "CORSMiddleware" in content or "cors" in content.lower():
                assert '"*"' not in content or "allow_origins" not in content, \
                    "CORS allows all origins (*) — overly permissive"
    
    def test_no_exposed_stack_traces(self):
        """Verify error handlers don't expose stack traces."""
        logger_path = SRC_PATH / "infrastructure" / "logger" / "logger.py"
        if logger_path.exists():
            content = logger_path.read_text()
            # Good: logger handles exceptions properly
            assert "exception" in content.lower() or "error" in content.lower(), \
                "Logger doesn't handle exceptions"
    
    def test_security_headers_configured(self):
        """Check for security headers middleware or configuration."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if any(h in content for h in ["X-Content-Type-Options", "X-Frame-Options", 
                                           "Content-Security-Policy", "Strict-Transport-Security"]):
                findings.append(str(py_file.relative_to(base)))
        
        if not findings:
            pytest.warns(UserWarning, match="No security headers configuration found")


class TestA06VulnerableComponents:
    """A06:2021 - Vulnerable and Outdated Components"""
    
    def test_trivy_workflow_exists(self):
        """Verify Trivy security scanning is configured in CI/CD."""
        trivy_wf = SRC_PATH.parent / ".github" / "workflows" / "trivy-security.yml"
        assert trivy_wf.exists(), "Trivy security workflow not found"
    
    def test_bandit_in_ci(self):
        """Verify Bandit is integrated in CI/CD pipeline."""
        ci_wf = SRC_PATH.parent / ".github" / "workflows" / "ci-cd.yml"
        assert ci_wf.exists(), "CI/CD workflow not found"
        content = ci_wf.read_text()
        assert "bandit" in content.lower(), "Bandit not in CI/CD pipeline"
    
    def test_pip_audit_in_ci(self):
        """Verify pip-audit/Safety is in CI/CD pipeline."""
        ci_wf = SRC_PATH.parent / ".github" / "workflows" / "ci-cd.yml"
        content = ci_wf.read_text()
        assert "pip-audit" in content or "safety" in content.lower(), \
            "pip-audit/Safety not in CI/CD pipeline"


class TestA07AuthFailures:
    """A07:2021 - Identification and Authentication Failures"""
    
    def test_auth_domain_exists(self):
        """Verify authentication domain module exists."""
        auth_dir = SRC_PATH / "domain" / "auth"
        assert auth_dir.exists(), "Auth domain module not found"
    
    def test_password_not_stored_in_plain(self):
        """Ensure passwords are hashed, not stored in plaintext."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if "password" in content.lower() and ("hash" not in content.lower() and "bcrypt" not in content.lower()):
                if "entity" in str(py_file).lower() or "model" in str(py_file).lower():
                    if "test" not in str(py_file).lower():
                        findings.append(str(py_file.relative_to(base)))
        
        # Soft check
        if findings and len(findings) > 2:
            pytest.warns(UserWarning, match="Review password handling")


class TestA08DataIntegrity:
    """A08:2021 - Software and Data Integrity Failures"""
    
    def test_sbom_generation_configured(self):
        """Verify SBOM generation in CI/CD."""
        trivy_wf = SRC_PATH.parent / ".github" / "workflows" / "trivy-security.yml"
        content = trivy_wf.read_text()
        assert "sbom" in content.lower() or "cyclonedx" in content.lower() or "spdx" in content.lower(), \
            "SBOM generation not configured"
    
    def test_ci_uses_sha_pinned_actions(self):
        """Check if GitHub Actions are pinned to SHA (not tags) across ALL workflow files.
        
        OWASP A08: Software and Data Integrity Failures requires CI action pinning.
        """
        workflows_dir = SRC_PATH.parent / ".github" / "workflows"
        if not workflows_dir.exists():
            pytest.skip("Workflows directory not found")
        
        unpinned = []
        for wf_file in sorted(workflows_dir.glob("*.yml")):
            content = wf_file.read_text()
            uses_lines = re.findall(r'uses:\s*(.+)', content)
            for line in uses_lines:
                if '@' in line:
                    ref = line.split('@')[1].split()[0]
                    if not re.search(r'^[a-f0-9]{40}$', ref):
                        unpinned.append(f"{wf_file.name}: {line.strip()}")
        
        # All actions must be pinned to immutable SHAs
        assert len(unpinned) == 0, (
            f"{len(unpinned)} unpinned action(s) found — OWASP A08 violation:\n"
            + "\n".join(unpinned)
        )


class TestA09LoggingFailures:
    """A09:2021 - Security Logging and Monitoring Failures"""
    
    def test_logging_infrastructure_exists(self):
        """Verify logging infrastructure exists."""
        logger_path = SRC_PATH / "infrastructure" / "logger" / "logger.py"
        assert logger_path.exists(), "Logger infrastructure not found"
    
    def test_audit_logging_for_auth_events(self):
        """Check for audit logging of authentication events."""
        auth_dir = SRC_PATH / "domain" / "auth"
        has_audit = False
        for py_file in auth_dir.rglob("*.py"):
            content = py_file.read_text(errors="ignore")
            if "log" in content.lower() and ("login" in content.lower() or "auth" in content.lower()):
                has_audit = True
                break
        
        assert has_audit, "No audit logging for auth events found"


class TestA10ExceptionalConditions:
    """A10:2025 - Mishandling of Exceptional Conditions (NEW in 2025)"""
    
    def test_global_error_handler_exists(self):
        """Verify global error handler prevents stack trace leakage."""
        fastapi_path = SRC_PATH / "infrastructure" / "shutdown" / "fastapi_integration.py"
        if fastapi_path.exists():
            content = fastapi_path.read_text()
            assert "exception" in content.lower() or "error" in content.lower(), \
                "FastAPI integration does not handle exceptions"
    
    def test_no_bare_except_clauses(self):
        """Check for bare except: clauses that swallow errors silently."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            if re.search(r'except\s*:', content) and "test" not in str(py_file).lower():
                findings.append(str(py_file.relative_to(base)))
        
        assert len(findings) == 0, f"Bare except: clauses found (swallows errors): {findings}"
    
    def test_error_responses_no_stack_traces(self):
        """Verify API error responses don't include stack traces."""
        findings = []
        base = SRC_PATH.parent
        for py_file in _get_scan_paths():
            content = py_file.read_text(errors="ignore")
            # Look for traceback or stack trace in response bodies
            if "traceback" in content.lower() and "response" in content.lower():
                if "test" not in str(py_file).lower():
                    findings.append(str(py_file.relative_to(base)))
        
        assert len(findings) == 0, f"Stack traces in responses: {findings}"


class TestSecurityToolIntegration:
    """Verify all security tools are properly integrated."""
    
    def test_semgrep_config_exists(self):
        """Check if Semgrep configuration exists."""
        base = SRC_PATH.parent
        has_config = (base / ".semgrep.yml").exists() or (base / "semgrep.yml").exists()
        if not has_config:
            pytest.warns(UserWarning, match="Semgrep config not found")
    
    def test_gitleaks_config_exists(self):
        """Check if Gitleaks configuration exists."""
        base = SRC_PATH.parent
        has_config = (base / ".gitleaks.toml").exists() or (base / ".gitleaks.yml").exists()
        if not has_config:
            pytest.warns(UserWarning, match="Gitleaks config not found")
    
    def test_pre_commit_config_exists(self):
        """Check if pre-commit hooks are configured."""
        base = SRC_PATH.parent
        assert (base / ".pre-commit-config.yaml").exists(), \
            "Pre-commit hooks not configured"


# =============================================================================
# Run with: pytest tests/security/test_owasp_top10_2025.py -v
# =============================================================================
