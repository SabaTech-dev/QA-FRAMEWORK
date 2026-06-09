"""Security Testing Module - Security vulnerability testing adapters"""

from .sql_injection_tester import SQLInjectionTester, SQLInjectionPayload
from .xss_tester import XSSTester, XSSPayload
from .auth_tester import AuthTester, AuthTestCase
from .rate_limit_tester import RateLimitTester
from .security_client import SecurityClient

# Vulnerability scanning (Nuclei + WSTG integration)
from src.adapters.vuln import (
    NucleiScanner,
    WSTGScanner,
    UnifiedVulnParser,
    VulnReportGenerator,
    VulnScanResult,
    VulnerabilityFinding,
    VulnSeverity,
    VulnCategory,
)

__all__ = [
    "SQLInjectionTester",
    "SQLInjectionPayload",
    "XSSTester",
    "XSSPayload",
    "AuthTester",
    "AuthTestCase",
    "RateLimitTester",
    "SecurityClient",
    "NucleiScanner",
    "WSTGScanner",
    "UnifiedVulnParser",
    "VulnReportGenerator",
    "VulnScanResult",
    "VulnerabilityFinding",
    "VulnSeverity",
    "VulnCategory",
]
