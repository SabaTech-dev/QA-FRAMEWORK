"""Nuclei Scanner - Docker-based wrapper

Docker-based wrapper for ProjectDiscovery's Nuclei scanner.
Supports web and network vulnerability scanning using templates.
"""

import asyncio
import json
import logging
import os
import tempfile
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

NUCLEI_IMAGE = "projectdiscovery/nuclei:latest"
NUCLEI_NETWORK = "qa-network"  # Docker network for scanning


class NucleiScanner:
    """Scanner wrapping Nuclei via Docker.

    Executes Nuclei scans against targets (URLs or IPs) and returns
    normalized results.

    Usage:
        scanner = NucleiScanner()
        result = await scanner.scan_web("https://example.com")
        result = await scanner.scan_network("10.0.0.1/24")
    """

    def __init__(
        self,
        docker_socket: str = "/var/run/docker.sock",
        network: str = NUCLEI_NETWORK,
        templates_dir: Optional[str] = None,
        custom_templates_dir: Optional[str] = None,
        output_dir: str = "./reports/vuln",
    ):
        """Initialize Nuclei scanner.

        Args:
            docker_socket: Path to Docker socket
            network: Docker network name for scanning
            templates_dir: Path to Nuclei templates (optional)
            custom_templates_dir: Path to custom templates
            output_dir: Output directory for raw results
        """
        self.docker_socket = docker_socket
        self.network = network
        self.templates_dir = templates_dir
        self.custom_templates_dir = custom_templates_dir or str(
            Path(__file__).parent.parent.parent.parent / "templates" / "vuln" / "custom"
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def scan_web(
        self,
        target: str,
        templates: Optional[List[str]] = None,
        severity: Optional[str] = None,
        rate_limit: int = 150,
        concurrency: int = 25,
        timeout: int = 30,
        extra_args: Optional[List[str]] = None,
        scan_id: Optional[str] = None,
    ) -> VulnScanResult:
        """Scan a web target for vulnerabilities.

        Args:
            target: URL to scan (e.g., https://example.com)
            templates: Specific templates to run (optional, runs all by default)
            severity: Filter by severity (critical, high, medium, low, info)
            rate_limit: Max requests per second
            concurrency: Max concurrent templates
            timeout: Per-template timeout in seconds
            extra_args: Additional CLI arguments for Nuclei
            scan_id: Custom scan ID (auto-generated if not provided)

        Returns:
            VulnScanResult with normalized findings
        """
        scan_id = scan_id or f"nuclei-web-{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow().isoformat() + "Z"

        # Build Docker command
        cmd = self._build_command(
            target=target,
            scan_type="web",
            templates=templates,
            severity=severity,
            rate_limit=rate_limit,
            concurrency=concurrency,
            timeout=timeout,
            extra_args=extra_args,
        )

        logger.info(f"Nuclei web scan starting: target={target}, scan_id={scan_id}")

        try:
            stdout, stderr, duration = await self._run_docker(cmd, timeout=timeout * 10)

            if not stdout.strip():
                return VulnScanResult(
                    scan_id=scan_id,
                    scanner="nuclei",
                    scan_type="web",
                    target=target,
                    start_time=start_time,
                    end_time=datetime.utcnow().isoformat() + "Z",
                    duration_seconds=duration,
                    error=f"No output from Nuclei. Stderr: {stderr[:500] if stderr else 'None'}",
                )

            # Nuclei outputs JSONL - collect all lines
            lines = stdout.strip().split("\n")
            json_results = []
            for line in lines:
                try:
                    data = json.loads(line)
                    json_results.append(data)
                except json.JSONDecodeError:
                    continue

            result = UnifiedVulnParser.parse_nuclei_json(
                json_data=json_results,
                scan_id=scan_id,
                target=target,
                scan_type="web",
            )
            result.duration_seconds = duration
            result.start_time = start_time
            result.end_time = datetime.utcnow().isoformat() + "Z"
            result.raw_output = stdout[:10000] if stdout else None

            if stderr:
                logger.warning(f"Nuclei stderr: {stderr[:500]}")

            logger.info(
                f"Nuclei web scan complete: {result.total_findings} findings "
                f"({result.critical_count}C/{result.high_count}H/{result.medium_count}M)"
            )
            return result

        except Exception as e:
            logger.error(f"Nuclei web scan failed: {e}")
            return VulnScanResult(
                scan_id=scan_id,
                scanner="nuclei",
                scan_type="web",
                target=target,
                start_time=start_time,
                end_time=datetime.utcnow().isoformat() + "Z",
                duration_seconds=0.0,
                error=str(e),
            )

    async def scan_network(
        self,
        target: str,
        templates: Optional[List[str]] = None,
        severity: Optional[str] = None,
        rate_limit: int = 500,
        concurrency: int = 50,
        timeout: int = 15,
        extra_args: Optional[List[str]] = None,
        scan_id: Optional[str] = None,
    ) -> VulnScanResult:
        """Scan a network target for vulnerabilities.

        Args:
            target: IP/CIDR to scan (e.g., 10.0.0.1/24)
            templates: Specific templates to run (optional)
            severity: Filter by severity
            rate_limit: Max packets per second
            concurrency: Max concurrent templates
            timeout: Per-template timeout in seconds
            extra_args: Additional CLI arguments
            scan_id: Custom scan ID

        Returns:
            VulnScanResult with normalized findings
        """
        scan_id = scan_id or f"nuclei-net-{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow().isoformat() + "Z"

        # For network scans, we add network-specific templates/args
        net_extra = extra_args or []
        net_extra.extend(["-stats", "-si", "10"])

        cmd = self._build_command(
            target=target,
            scan_type="network",
            templates=templates or ["network", "dns", "ssl"],
            severity=severity,
            rate_limit=rate_limit,
            concurrency=concurrency,
            timeout=timeout,
            extra_args=net_extra,
        )

        logger.info(f"Nuclei network scan starting: target={target}, scan_id={scan_id}")

        try:
            stdout, stderr, duration = await self._run_docker(cmd, timeout=timeout * 20)

            if not stdout.strip():
                return VulnScanResult(
                    scan_id=scan_id,
                    scanner="nuclei",
                    scan_type="network",
                    target=target,
                    start_time=start_time,
                    end_time=datetime.utcnow().isoformat() + "Z",
                    duration_seconds=duration,
                    error=f"No output from Nuclei. Stderr: {stderr[:500] if stderr else 'None'}",
                )

            lines = stdout.strip().split("\n")
            json_results = []
            for line in lines:
                try:
                    data = json.loads(line)
                    json_results.append(data)
                except json.JSONDecodeError:
                    continue

            result = UnifiedVulnParser.parse_nuclei_json(
                json_data=json_results,
                scan_id=scan_id,
                target=target,
                scan_type="network",
            )
            result.duration_seconds = duration
            result.start_time = start_time
            result.end_time = datetime.utcnow().isoformat() + "Z"
            result.raw_output = stdout[:10000] if stdout else None

            logger.info(
                f"Nuclei network scan complete: {result.total_findings} findings"
            )
            return result

        except Exception as e:
            logger.error(f"Nuclei network scan failed: {e}")
            return VulnScanResult(
                scan_id=scan_id,
                scanner="nuclei",
                scan_type="network",
                target=target,
                start_time=start_time,
                end_time=datetime.utcnow().isoformat() + "Z",
                duration_seconds=0.0,
                error=str(e),
            )

    async def scan_with_template(
        self,
        target: str,
        template_path: str,
        scan_id: Optional[str] = None,
    ) -> VulnScanResult:
        """Run a specific custom template against a target.

        Args:
            target: URL or IP to scan
            template_path: Path to custom template file
            scan_id: Custom scan ID

        Returns:
            VulnScanResult
        """
        scan_type = "network" if not target.startswith("http") else "web"
        return await self.scan_web(
            target=target,
            templates=[template_path],
            scan_id=scan_id or f"nuclei-custom-{uuid.uuid4().hex[:12]}",
        )

    def _build_command(
        self,
        target: str,
        scan_type: str = "web",
        templates: Optional[List[str]] = None,
        severity: Optional[str] = None,
        rate_limit: int = 150,
        concurrency: int = 25,
        timeout: int = 30,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """Build the Docker command for Nuclei."""
        cmd = [
            "docker", "run", "--rm",
            "--network", self.network,
            "-v", f"{self.docker_socket}:/var/run/docker.sock",
        ]

        # Mount custom templates if they exist
        if self.custom_templates_dir and os.path.isdir(self.custom_templates_dir):
            cmd.extend(["-v", f"{self.custom_templates_dir}:/custom-templates"])

        # Mount output directory
        cmd.extend(["-v", f"{self.output_dir}:/output"])

        cmd.append(NUCLEI_IMAGE)

        # Target
        if scan_type == "network" and not target.startswith("http"):
            cmd.extend(["-target", target])
        else:
            cmd.extend(["-u", target])

        # Output format (JSONL)
        cmd.extend(["-j", "-o", "/output/nuclei_raw.jsonl"])

        # Template selection
        if templates:
            for t in templates:
                if t.startswith("/") or t.startswith("./"):
                    cmd.extend(["-t", t])
                elif os.path.exists(str(Path(self.custom_templates_dir) / t)):
                    cmd.extend(["-t", f"/custom-templates/{t}"])
                else:
                    cmd.extend(["-t", t])

        # Severity filter
        if severity:
            cmd.extend(["-severity", severity])

        # Performance
        cmd.extend(["-rate-limit", str(rate_limit)])
        cmd.extend(["-concurrency", str(concurrency)])
        cmd.extend(["-timeout", str(timeout)])

        # Additional args
        if extra_args:
            cmd.extend(extra_args)

        # Always use JSONL output
        if "-j" not in cmd and "-jsonl" not in cmd:
            cmd.append("-j")

        return cmd

    async def _run_docker(
        self, cmd: List[str], timeout: int = 300
    ) -> tuple[str, str, float]:
        """Execute Docker command and capture output.

        Args:
            cmd: Docker command as list
            timeout: Maximum execution time in seconds

        Returns:
            Tuple of (stdout, stderr, duration_seconds)
        """
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
            logger.warning(f"Nuclei scan timed out after {timeout}s")
            return "", f"TIMEOUT after {timeout}s", duration

        duration = (datetime.utcnow() - start).total_seconds()
        return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), duration

    async def list_templates(self) -> List[Dict[str, Any]]:
        """List available Nuclei templates.

        Returns:
            List of template metadata dicts
        """
        cmd = [
            "docker", "run", "--rm", NUCLEI_IMAGE,
            "-tl",
        ]

        try:
            stdout, stderr, _ = await self._run_docker(cmd, timeout=60)
            templates = []
            for line in stdout.strip().split("\n"):
                if line.strip():
                    templates.append({"template": line.strip()})
            return templates
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []

    async def update_templates(self) -> bool:
        """Update Nuclei templates to latest version.

        Returns:
            True if update succeeded
        """
        cmd = [
            "docker", "run", "--rm", NUCLEI_IMAGE,
            "-update-templates",
        ]

        try:
            stdout, stderr, _ = await self._run_docker(cmd, timeout=120)
            logger.info(f"Nuclei templates updated. Output: {stdout[:200]}")
            return True
        except Exception as e:
            logger.error(f"Failed to update templates: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check if Nuclei is available and healthy.

        Returns:
            Dict with health status information
        """
        try:
            version_cmd = [
                "docker", "run", "--rm", NUCLEI_IMAGE,
                "--version",
            ]
            stdout, stderr, _ = await self._run_docker(version_cmd, timeout=30)

            # Parse version from output
            version = "unknown"
            for line in stdout.strip().split("\n"):
                if "Current Version:" in line:
                    version = line.split(":")[-1].strip()
                    break

            template_count = len(await self.list_templates())

            return {
                "status": "healthy" if version != "unknown" else "degraded",
                "scanner": "nuclei",
                "version": version,
                "templates_available": template_count,
                "docker_image": NUCLEI_IMAGE,
                "network": self.network,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "scanner": "nuclei",
                "error": str(e),
            }

    async def close(self):
        """Cleanup resources."""
        pass
