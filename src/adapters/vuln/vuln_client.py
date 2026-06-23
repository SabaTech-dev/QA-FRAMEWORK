"""Vulnerability Scanning Client

Unified client for vulnerability scanning using Nuclei and WSTG-Scan.
Provides a facade similar to SecurityClient for easy integration.
"""

import logging
from typing import Any, Dict, List, Optional

from src.adapters.vuln import (
    VulnScanResult,
    VulnerabilityFinding,
    VulnSeverity,
    VulnCategory,
    UnifiedVulnParser,
    VulnReportGenerator,
)
from src.adapters.vuln.nuclei_scanner import NucleiScanner
from src.adapters.vuln.wstg_scanner import WSTGScanner
from src.adapters.vuln.zap_scanner import ZAPScanner

logger = logging.getLogger(__name__)


class VulnClient:
    """Unified vulnerability scanning client.

    Provides a single interface for all vulnerability scanning operations
    using Nuclei (template-based), WSTG (OWASP methodology), and ZAP (OWASP ZAP).

    Usage:
        client = VulnClient()

        # Web scan
        result = await client.scan_web("https://example.com")

        # Network scan
        result = await client.scan_network("10.0.0.1/24")

        # Generate report
        paths = client.generate_report(result)
    """

    def __init__(
        self,
        output_dir: str = "./reports/vuln",
        report_output_dir: str = "./reports/vuln",
    ):
        """Initialize the vulnerability scanning client.

        Args:
            output_dir: Directory for raw scan outputs
            report_output_dir: Directory for generated reports
        """
        self._nuclei = NucleiScanner(output_dir=output_dir)
        self._wstg = WSTGScanner(output_dir=output_dir)
        self._zap = ZAPScanner(output_dir=output_dir)
        self._reporter = VulnReportGenerator(output_dir=report_output_dir)
        self._closed = False

    async def scan_web(
        self,
        target: str,
        use_nuclei: bool = True,
        use_wstg: bool = True,
        use_zap: bool = False,
        nuclei_templates: Optional[List[str]] = None,
        wstg_categories: Optional[List[str]] = None,
        severity_filter: Optional[str] = None,
        auth_token: Optional[str] = None,
        rate_limit: int = 150,
        timeout: Optional[int] = None,
    ) -> VulnScanResult:
        """Run a comprehensive web vulnerability scan.

        Combines Nuclei, WSTG, and ZAP scans for maximum coverage.

        Args:
            target: URL to scan
            use_nuclei: Whether to run Nuclei scan
            use_wstg: Whether to run WSTG scan
            use_zap: Whether to run ZAP scan
            nuclei_templates: Specific Nuclei templates
            wstg_categories: Specific WSTG categories
            severity_filter: Minimum severity to report
            auth_token: Bearer token for authenticated scans
            rate_limit: Max requests per second
            timeout: Scan timeout in seconds

        Returns:
            Merged VulnScanResult
        """
        if self._closed:
            raise RuntimeError("VulnClient is closed")

        results = []

        if use_nuclei:
            try:
                nr = await self._nuclei.scan_web(
                    target=target,
                    templates=nuclei_templates,
                    severity=severity_filter,
                    rate_limit=rate_limit,
                    timeout=timeout or 300,
                )
                results.append(nr)
            except Exception as e:
                logger.error(f"Nuclei scan failed: {e}")

        if use_wstg:
            try:
                wr = await self._wstg.scan_web(
                    target=target,
                    categories=wstg_categories,
                    auth_token=auth_token,
                    timeout=timeout or 600,
                )
                results.append(wr)
            except Exception as e:
                logger.error(f"WSTG scan failed: {e}")

        if use_zap:
            try:
                zr = await self._zap.scan_web(
                    target=target,
                )
                results.append(zr)
            except Exception as e:
                logger.error(f"ZAP scan failed: {e}")

        if not results:
            return VulnScanResult(
                scan_id="error",
                scanner="combined",
                scan_type="web",
                target=target,
                start_time=__import__("datetime").datetime.utcnow().isoformat() + "Z",
                end_time=__import__("datetime").datetime.utcnow().isoformat() + "Z",
                duration_seconds=0.0,
                error="All scanners failed or were disabled",
            )

        if len(results) == 1:
            return results[0]

        return UnifiedVulnParser.merge_results(results)

    async def scan_network(
        self,
        target: str,
        templates: Optional[List[str]] = None,
        severity_filter: Optional[str] = None,
        rate_limit: int = 500,
        timeout: Optional[int] = None,
    ) -> VulnScanResult:
        """Run a network vulnerability scan.

        Args:
            target: IP/CIDR range to scan
            templates: Specific Nuclei templates
            severity_filter: Minimum severity
            rate_limit: Max packets per second
            timeout: Scan timeout

        Returns:
            VulnScanResult
        """
        if self._closed:
            raise RuntimeError("VulnClient is closed")

        return await self._nuclei.scan_network(
            target=target,
            templates=templates,
            severity=severity_filter,
            rate_limit=rate_limit,
            timeout=timeout or 600,
        )

    async def scan_single(
        self,
        target: str,
        scanner: str = "nuclei",
        templates: Optional[List[str]] = None,
    ) -> VulnScanResult:
        """Run a scan using a single specified scanner.

        Args:
            target: Target URL or IP
            scanner: "nuclei", "wstg", or "zap"
            templates: Specific templates to use

        Returns:
            VulnScanResult
        """
        if scanner.lower() == "nuclei":
            return await self._nuclei.scan_web(target=target, templates=templates)
        elif scanner.lower() == "wstg":
            return await self._wstg.scan_web(target=target)
        elif scanner.lower() == "zap":
            return await self._zap.scan_web(target=target)
        else:
            raise ValueError(f"Unknown scanner: {scanner}. Use 'nuclei', 'wstg', or 'zap'.")

    def generate_report(
        self, result: VulnScanResult, base_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate vulnerability report in all formats.

        Args:
            result: Scan result to report
            base_name: Optional base filename

        Returns:
            Dict mapping format -> file path
        """
        if self._closed:
            raise RuntimeError("VulnClient is closed")

        return self._reporter.generate_all(result, base_name=base_name)

    async def list_nuclei_templates(self) -> List[Dict[str, Any]]:
        """List available Nuclei templates."""
        return await self._nuclei.list_templates()

    async def update_nuclei_templates(self) -> bool:
        """Update Nuclei templates to latest."""
        return await self._nuclei.update_templates()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all scanners.

        Returns:
            Dict with health status for each scanner
        """
        return {
            "nuclei": await self._nuclei.health_check(),
            "wstg": await self._wstg.health_check(),
            "zap": await self._zap.health_check(),
        }

    async def close(self):
        """Close the client and release resources."""
        self._closed = True
        await self._nuclei.close()
        await self._wstg.close()
        await self._zap.close()

    async def __aenter__(self) -> "VulnClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
