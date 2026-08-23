"""Vulnerability Scanning Module

This module provides a unified interface for vulnerability scanning using:
- Nuclei: Template-based vulnerability scanner for web and network
- WSTG-Scan: OWASP Web Security Testing Guide scanner

It includes Docker wrappers, result parsing, and report generation.
"""

from .nuclei_scanner import NucleiScanner
from .vuln_client import VulnClient
from .vuln_parser import (
    UnifiedVulnParser,
    VulnCategory,
    VulnerabilityFinding,
    VulnScanResult,
    VulnSeverity,
)
from .vuln_report import VulnReportGenerator
from .wstg_scanner import WSTGScanner

__all__ = [
    "VulnSeverity",
    "VulnCategory",
    "VulnerabilityFinding",
    "VulnScanResult",
    "UnifiedVulnParser",
    "VulnReportGenerator",
    "NucleiScanner",
    "WSTGScanner",
    "VulnClient",
]
