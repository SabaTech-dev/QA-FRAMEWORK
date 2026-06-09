"""WSTG Scanner - OWASP Web Security Testing Guide Scanner

Docker-based wrapper for OWASP WSTG automated scanning.
Executes tests based on the OWASP Web Security Testing Guide v4.2.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .vuln_parser import (
    VulnScanResult,
    VulnerabilityFinding,
    VulnSeverity,
    VulnCategory,
    UnifiedVulnParser,
)

logger = logging.getLogger(__name__)

# Default WSTG Docker image
WSTG_IMAGE = "owasp/wstg-scanner:latest"
WSTG_NETWORK = "qa-network"


class WSTGScanner:
    """Scanner wrapping OWASP WSTG-Scan via Docker.

    Executes WSTG-based security tests against web targets.
    Follows the OWASP Web Security Testing Guide methodology.

    Usage:
        scanner = WSTGScanner()
        result = await scanner.scan_web("https://example.com")
        result = await scanner.scan_with_category("https://example.com", "WSTG-INPV")
    """

    # Available WSTG test categories
    WSTG_CATEGORIES = {
        "WSTG-INFO": "Information Gathering",
        "WSTG-CONF": "Configuration and Deployment Management Testing",
        "WSTG-IDNT": "Identity Management Testing",
        "WSTG-ATHN": "Authentication Testing",
        "WSTG-ATHZ": "Authorization Testing",
        "WSTG-SESS": "Session Management Testing",
        "WSTG-INPV": "Input Validation Testing",
        "WSTG-ERRH": "Error Handling Testing",
        "WSTG-CRYP": "Cryptography Testing",
        "WSTG-BUSL": "Business Logic Testing",
        "WSTG-CLI": "Client-side Testing",
    }

    def __init__(
        self,
        network: str = WSTG_NETWORK,
        output_dir: str = "./reports/vuln",
    ):
        """Initialize WSTG scanner.

        Args:
            network: Docker network name
            output_dir: Output directory for results
        """
        self.network = network
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def scan_web(
        self,
        target: str,
        categories: Optional[List[str]] = None,
        auth_token: Optional[str] = None,
        cookie: Optional[str] = None,
        proxy: Optional[str] = None,
        rate_limit: int = 10,
        timeout: int = 300,
        scan_id: Optional[str] = None,
    ) -> VulnScanResult:
        """Run a comprehensive WSTG web scan.

        Args:
            target: URL to scan
            categories: WSTG categories to test (e.g., ["WSTG-INPV", "WSTG-ATHN"]).
                       None = all categories.
            auth_token: Bearer token for authenticated scanning
            cookie: Session cookie for authenticated scanning
            proxy: Proxy URL (e.g., http://proxy:8080)
            rate_limit: Requests per second
            timeout: Overall scan timeout in seconds
            scan_id: Custom scan ID

        Returns:
            VulnScanResult with normalized findings
        """
        scan_id = scan_id or f"wstg-web-{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow().isoformat() + "Z"

        cmd = self._build_command(
            target=target,
            categories=categories,
            auth_token=auth_token,
            cookie=cookie,
            proxy=proxy,
            rate_limit=rate_limit,
        )

        logger.info(
            f"WSTG web scan starting: target={target}, "
            f"categories={categories or 'ALL'}, scan_id={scan_id}"
        )

        try:
            stdout, stderr, duration = await self._run_docker(cmd, timeout=timeout)

            if not stdout.strip():
                return VulnScanResult(
                    scan_id=scan_id,
                    scanner="wstg",
                    scan_type="web",
                    target=target,
                    start_time=start_time,
                    end_time=datetime.utcnow().isoformat() + "Z",
                    duration_seconds=duration,
                    error=f"No WSTG output. Stderr: {stderr[:500] if stderr else 'None'}",
                )

            # Try to parse as JSON
            try:
                raw_data = json.loads(stdout)
            except json.JSONDecodeError:
                # Try JSONL (line-by-line)
                lines = stdout.strip().split("\n")
                json_objects = []
                for line in lines:
                    try:
                        json_objects.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                raw_data = json_objects if json_objects else {"raw": stdout[:5000]}

            result = UnifiedVulnParser.parse_wstg_json(
                json_data=raw_data,
                scan_id=scan_id,
                target=target,
                scan_type="web",
            )
            result.duration_seconds = duration
            result.start_time = start_time
            result.end_time = datetime.utcnow().isoformat() + "Z"
            result.raw_output = stdout[:10000] if stdout else None

            if stderr:
                logger.warning(f"WSTG stderr: {stderr[:500]}")

            logger.info(
                f"WSTG scan complete: {result.total_findings} findings "
                f"({result.critical_count}C/{result.high_count}H/{result.medium_count}M)"
            )
            return result

        except Exception as e:
            logger.error(f"WSTG scan failed: {e}")
            return VulnScanResult(
                scan_id=scan_id,
                scanner="wstg",
                scan_type="web",
                target=target,
                start_time=start_time,
                end_time=datetime.utcnow().isoformat() + "Z",
                duration_seconds=0.0,
                error=str(e),
            )

    async def scan_with_category(
        self,
        target: str,
        category: str,
        scan_id: Optional[str] = None,
    ) -> VulnScanResult:
        """Run a specific WSTG category scan.

        Args:
            target: URL to scan
            category: WSTG category code (e.g., "WSTG-INPV")
            scan_id: Custom scan ID

        Returns:
            VulnScanResult
        """
        return await self.scan_web(
            target=target,
            categories=[category],
            scan_id=scan_id or f"wstg-{category.lower()}-{uuid.uuid4().hex[:12]}",
        )

    def _build_command(
        self,
        target: str,
        categories: Optional[List[str]] = None,
        auth_token: Optional[str] = None,
        cookie: Optional[str] = None,
        proxy: Optional[str] = None,
        rate_limit: int = 10,
    ) -> List[str]:
        """Build the Docker command for WSTG scanner."""
        cmd = [
            "docker", "run", "--rm",
            "--network", self.network,
        ]

        # Mount output volume
        cmd.extend(["-v", f"{self.output_dir}:/output"])

        cmd.append(WSTG_IMAGE)

        # Target
        cmd.extend(["--target", target])

        # Output format
        cmd.extend(["--format", "json"])
        cmd.extend(["--output", "/output/wstg_result.json"])

        # Category filters
        if categories:
            cmd.extend(["--categories", ",".join(categories)])

        # Authentication
        if auth_token:
            cmd.extend(["--auth-token", auth_token])
        if cookie:
            cmd.extend(["--cookie", cookie])

        # Proxy
        if proxy:
            cmd.extend(["--proxy", proxy])

        # Rate limiting
        cmd.extend(["--rate-limit", str(rate_limit)])

        return cmd

    async def _run_docker(
        self, cmd: List[str], timeout: int = 600
    ) -> tuple[str, str, float]:
        """Execute Docker command and capture output."""
        start = datetime.utcnow()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            duration = (datetime.utcnow() - start).total_seconds()
            logger.warning(f"WSTG scan timed out after {timeout}s")
            return "", f"TIMEOUT after {timeout}s", duration

        duration = (datetime.utcnow() - start).total_seconds()
        return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), duration

    async def list_categories(self) -> Dict[str, str]:
        """List available WSTG test categories.

        Returns:
            Dict mapping category codes to descriptions
        """
        return dict(self.WSTG_CATEGORIES)

    async def health_check(self) -> Dict[str, Any]:
        """Check if WSTG scanner is available.

        Returns:
            Dict with health status
        """
        try:
            cmd = ["docker", "run", "--rm", WSTG_IMAGE, "--help"]
            stdout, stderr, _ = await self._run_docker(cmd, timeout=30)

            return {
                "status": "healthy",
                "scanner": "wstg",
                "docker_image": WSTG_IMAGE,
                "categories_available": len(self.WSTG_CATEGORIES),
                "network": self.network,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "scanner": "wstg",
                "error": str(e),
            }

    async def close(self):
        """Cleanup resources."""
        pass
