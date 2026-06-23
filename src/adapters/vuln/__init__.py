"""Vulnerability Scanning Module

This module provides a unified interface for vulnerability scanning using:
- Nuclei: Template-based vulnerability scanner for web and network
- WSTG-Scan: OWASP Web Security Testing Guide scanner

It includes Docker wrappers, result parsing, and report generation.
"""

from .vuln_parser import (
    VulnSeverity,
    VulnCategory,
    VulnerabilityFinding,
    VulnScanResult,
    UnifiedVulnParser,
)
from .vuln_report import VulnReportGenerator
from .nuclei_scanner import NucleiScanner
from .wstg_scanner import WSTGScanner
from .zap_scanner import ZAPScanner
from .vuln_client import VulnClient

__all__ = [
    "VulnSeverity",
    "VulnCategory",
    "VulnerabilityFinding",
    "VulnScanResult",
    "UnifiedVulnParser",
    "VulnReportGenerator",
    "NucleiScanner",
    "WSTGScanner",
    "ZAPScanner",
    "VulnClient",
]
