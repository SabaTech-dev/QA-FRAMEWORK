"""OWASP ZAP Scanner - Docker-based wrapper

Docker-based wrapper for OWASP Zed Attack Proxy (ZAP).
Supports web vulnerability scanning using spider, active scan, and alerts collection.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp

from .vuln_parser import (
    VulnScanResult,
    VulnerabilityFinding,
    VulnSeverity,
    VulnCategory,
    UnifiedVulnParser,
)

logger = logging.getLogger(__name__)

ZAP_IMAGE = "ghcr.io/zaproxy/zaproxy:stable"
ZAP_NETWORK = "qa-network"  # Docker network for scanning
ZAP_DAEMON_PORT = 8080  # Default port for ZAP API


@dataclass
class ZAPScannerConfig:
    """Configuration for ZAP scanner."""

    proxy_host: str = "127.0.0.1"
    proxy_port: int = 8080
    api_key: Optional[str] = None
    daemon_port: int = 8080
    spider_duration: int = 60
    active_scan_duration: int = 120
    ajax_spider_enabled: bool = False
    docker_image: str = ZAP_IMAGE
    network: str = ZAP_NETWORK
    docker_socket: str = "/var/run/docker.sock"
    output_dir: str = "./reports/vuln"


class ZAPScanner:
    """Scanner wrapping OWASP ZAP via Docker.

    Executes ZAP scans against web targets and returns
    normalized results.

    Usage:
        scanner = ZAPScanner()
        result = await scanner.scan_web("https://example.com")
        result = await scanner.scan_with_policy("https://example.com", "default-policy")
    """

    def __init__(
        self,
        config: Optional[ZAPScannerConfig] = None,
        docker_socket: Optional[str] = None,
        network: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        """Initialize ZAP scanner.

        Args:
            config: Optional ZAPScannerConfig instance
            docker_socket: Path to Docker socket (overrides config)
            network: Docker network name (overrides config)
            output_dir: Output directory for raw results (overrides config)
        """
        if config is None:
            config = ZAPScannerConfig()

        if docker_socket:
            config.docker_socket = docker_socket
        if network:
            config.network = network
        if output_dir:
            config.output_dir = output_dir

        self.config = config
        self._container_id: Optional[str] = None
        self._api_url = f"http://{config.proxy_host}:{config.daemon_port}"
        self._session: Optional[aiohttp.ClientSession] = None
        self._output_dir = Path(config.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def scan_web(
        self,
        target: str,
        scan_id: Optional[str] = None,
        spider_enabled: bool = True,
        active_scan_enabled: bool = True,
        spider_duration: Optional[int] = None,
        active_scan_duration: Optional[int] = None,
    ) -> VulnScanResult:
        """Scan a web target for vulnerabilities.

        Performs a full ZAP web scan: start daemon → spider → active scan → collect alerts.

        Args:
            target: URL to scan (e.g., https://example.com)
            scan_id: Custom scan ID (auto-generated if not provided)
            spider_enabled: Whether to run spider
            active_scan_enabled: Whether to run active scan
            spider_duration: Spider duration in seconds (overrides config)
            active_scan_duration: Active scan duration in seconds (overrides config)

        Returns:
            VulnScanResult with normalized findings
        """
        scan_id = scan_id or f"zap-web-{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow().isoformat() + "Z"

        logger.info(f"ZAP web scan starting: target={target}, scan_id={scan_id}")

        try:
            # Start ZAP daemon
            await self._start_daemon()

            # Access the target to seed ZAP
            await self._access_target(target)

            # Run spider if enabled
            spider_duration = spider_duration or self.config.spider_duration
            if spider_enabled:
                await self._run_spider(target, duration=spider_duration)

            # Run active scan if enabled
            active_scan_duration = active_scan_duration or self.config.active_scan_duration
            if active_scan_enabled:
                await self._run_active_scan(target, duration=active_scan_duration)

            # Collect alerts
            alerts = await self._get_alerts()

            # Parse alerts into VulnScanResult
            result = self._parse_alerts(alerts, scan_id, target)
            result.start_time = start_time
            result.end_time = datetime.utcnow().isoformat() + "Z"

            duration = (
                datetime.utcnow() - datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            ).total_seconds()
            result.duration_seconds = duration

            logger.info(
                f"ZAP web scan complete: {result.total_findings} findings "
                f"({result.critical_count}C/{result.high_count}H/{result.medium_count}M)"
            )
            return result

        except Exception as e:
            logger.error(f"ZAP web scan failed: {e}")
            return VulnScanResult(
                scan_id=scan_id,
                scanner="zap",
                scan_type="web",
                target=target,
                start_time=start_time,
                end_time=datetime.utcnow().isoformat() + "Z",
                duration_seconds=0.0,
                error=str(e),
            )

    async def scan_with_policy(
        self,
        target: str,
        policy_name: str,
        scan_id: Optional[str] = None,
        spider_enabled: bool = True,
        active_scan_enabled: bool = True,
    ) -> VulnScanResult:
        """Scan a web target using a specific ZAP policy.

        Args:
            target: URL to scan
            policy_name: Name of the ZAP policy to use
            scan_id: Custom scan ID
            spider_enabled: Whether to run spider
            active_scan_enabled: Whether to run active scan

        Returns:
            VulnScanResult with normalized findings
        """
        scan_id = scan_id or f"zap-policy-{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow().isoformat() + "Z"

        logger.info(
            f"ZAP policy scan starting: target={target}, policy={policy_name}, scan_id={scan_id}"
        )

        try:
            # Start ZAP daemon
            await self._start_daemon()

            # Access the target to seed ZAP
            await self._access_target(target)

            # Load the policy (if it exists)
            try:
                await self._load_policy(policy_name)
            except Exception as e:
                logger.warning(f"Could not load policy '{policy_name}': {e}, using default scan")

            # Run spider if enabled
            if spider_enabled:
                await self._run_spider(target, duration=self.config.spider_duration)

            # Run active scan if enabled
            if active_scan_enabled:
                await self._run_active_scan(target, duration=self.config.active_scan_duration)

            # Collect alerts
            alerts = await self._get_alerts()

            # Parse alerts into VulnScanResult
            result = self._parse_alerts(alerts, scan_id, target)
            result.start_time = start_time
            result.end_time = datetime.utcnow().isoformat() + "Z"

            duration = (
                datetime.utcnow() - datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            ).total_seconds()
            result.duration_seconds = duration

            logger.info(
                f"ZAP policy scan complete: {result.total_findings} findings "
                f"({result.critical_count}C/{result.high_count}H/{result.medium_count}M)"
            )
            return result

        except Exception as e:
            logger.error(f"ZAP policy scan failed: {e}")
            return VulnScanResult(
                scan_id=scan_id,
                scanner="zap",
                scan_type="web",
                target=target,
                start_time=start_time,
                end_time=datetime.utcnow().isoformat() + "Z",
                duration_seconds=0.0,
                error=str(e),
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check if ZAP daemon is available and healthy.

        Returns:
            Dict with health status information
        """
        try:
            # Try to connect to ZAP API
            session = await self._get_session()
            version = await self._zap_api_request("/JSON/core/view/version/", session)

            if version:
                version_str = version.get("version", "unknown")
                return {
                    "status": "healthy",
                    "scanner": "zap",
                    "version": version_str,
                    "docker_image": self.config.docker_image,
                    "network": self.config.network,
                    "api_url": self._api_url,
                }
            else:
                return {
                    "status": "degraded",
                    "scanner": "zap",
                    "error": "Could not retrieve ZAP version",
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "scanner": "zap",
                "error": str(e),
            }

    async def close(self):
        """Stop the ZAP daemon and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None

        if self._container_id:
            await self._stop_daemon()

    async def __aenter__(self) -> "ZAPScanner":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # ─── Private Methods ────────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _zap_api_request(
        self,
        endpoint: str,
        session: Optional[aiohttp.ClientSession] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the ZAP API.

        Args:
            endpoint: API endpoint (e.g., /JSON/core/view/version/)
            session: Optional session to use
            params: Optional query parameters

        Returns:
            JSON response as dict, or None if request fails
        """
        if session is None:
            session = await self._get_session()

        url = self._api_url + endpoint
        request_params = params or {}

        # Add API key if configured
        if self.config.api_key:
            request_params["apikey"] = self.config.api_key

        try:
            async with session.get(url, params=request_params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"ZAP API request failed: {response.status} - {url}")
                    return None
        except Exception as e:
            logger.warning(f"ZAP API request error: {e}")
            return None

    async def _start_daemon(self) -> None:
        """Start ZAP daemon in a Docker container."""
        if self._container_id:
            # Container already running
            return

        # Build Docker command to start ZAP in daemon mode
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            f"zap-{uuid.uuid4().hex[:8]}",
            "--network",
            self.config.network,
            "-p",
            f"{self.config.proxy_port}:{self.config.daemon_port}",
            "-v",
            f"{self.config.docker_socket}:/var/run/docker.sock",
            "-v",
            f"{self._output_dir}:/output",
            self.config.docker_image,
            "-daemon",
            "-host",
            "0.0.0.0",
            "-port",
            str(self.config.daemon_port),
            "-config",
            f"api.addrs.addr.name=.*",
            "-config",
            f"api.addrs.addr.regex=true",
            "-config",
            "api.disablekey=true",
        ]

        # Add API key if configured
        if self.config.api_key:
            cmd.extend(["-config", f"api.key={self.config.api_key}"])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"Failed to start ZAP daemon: {error_msg}")

            container_id = stdout.decode("utf-8", errors="replace").strip()
            self._container_id = container_id

            # Wait for ZAP to be ready
            await self._wait_for_daemon_ready()

            logger.info(f"ZAP daemon started: container_id={container_id}")

        except Exception as e:
            logger.error(f"Failed to start ZAP daemon: {e}")
            raise

    async def _wait_for_daemon_ready(self, max_attempts: int = 30, delay: float = 2.0) -> None:
        """Wait for ZAP daemon to be ready to accept API calls."""
        session = await self._get_session()

        for attempt in range(max_attempts):
            try:
                result = await self._zap_api_request("/JSON/core/view/version/", session)
                if result and "version" in result:
                    logger.info(f"ZAP daemon ready after {attempt * delay:.1f}s")
                    return
            except Exception:
                pass

            await asyncio.sleep(delay)

        raise TimeoutError(f"ZAP daemon did not become ready after {max_attempts * delay}s")

    async def _stop_daemon(self) -> None:
        """Stop the ZAP daemon container."""
        if not self._container_id:
            return

        try:
            cmd = ["docker", "stop", self._container_id]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Also remove the container
            cmd = ["docker", "rm", self._container_id]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            logger.info(f"ZAP daemon stopped: container_id={self._container_id}")
            self._container_id = None

        except Exception as e:
            logger.warning(f"Failed to stop ZAP daemon: {e}")

    async def _access_target(self, target: str) -> None:
        """Access the target to seed ZAP's history."""
        session = await self._get_session()

        # Use ZAP's API to access the target
        await self._zap_api_request(
            "/JSON/core/action/accessUrl/",
            session,
            params={"url": target},
        )

        # Wait a moment for the request to complete
        await asyncio.sleep(1)

    async def _run_spider(self, target: str, duration: int) -> None:
        """Run ZAP spider on the target.

        Args:
            target: URL to spider
            duration: Maximum duration in seconds
        """
        session = await self._get_session()

        logger.info(f"Starting ZAP spider: target={target}, duration={duration}s")

        # Start spider
        result = await self._zap_api_request(
            "/JSON/spider/action/scan/",
            session,
            params={"url": target},
        )

        if not result or "scan" not in result:
            logger.warning("Failed to start ZAP spider")
            return

        scan_id = result["scan"]

        # Wait for spider to complete or timeout
        start_time = datetime.utcnow()
        while True:
            status = await self._zap_api_request(
                "/JSON/spider/view/status/",
                session,
                params={"scanId": scan_id},
            )

            if status:
                progress = int(status.get("status", "0"))
                if progress >= 100:
                    logger.info(f"ZAP spider completed: {progress}%")
                    break

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= duration:
                logger.warning(f"ZAP spider timed out after {elapsed:.1f}s")
                break

            await asyncio.sleep(2)

    async def _run_active_scan(self, target: str, duration: int) -> None:
        """Run ZAP active scan on the target.

        Args:
            target: URL to scan
            duration: Maximum duration in seconds
        """
        session = await self._get_session()

        logger.info(f"Starting ZAP active scan: target={target}, duration={duration}s")

        # Start active scan
        result = await self._zap_api_request(
            "/JSON/ascan/action/scan/",
            session,
            params={"url": target},
        )

        if not result or "scan" not in result:
            logger.warning("Failed to start ZAP active scan")
            return

        scan_id = result["scan"]

        # Wait for scan to complete or timeout
        start_time = datetime.utcnow()
        while True:
            status = await self._zap_api_request(
                "/JSON/ascan/view/status/",
                session,
                params={"scanId": scan_id},
            )

            if status:
                progress = int(status.get("status", "0"))
                if progress >= 100:
                    logger.info(f"ZAP active scan completed: {progress}%")
                    break

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= duration:
                logger.warning(f"ZAP active scan timed out after {elapsed:.1f}s")
                break

            await asyncio.sleep(2)

    async def _get_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts from ZAP.

        Returns:
            List of alert dictionaries
        """
        session = await self._get_session()

        result = await self._zap_api_request("/JSON/core/view/alerts/", session)

        if not result or "alerts" not in result:
            return []

        return result["alerts"]

    def _parse_alerts(
        self,
        alerts: List[Dict[str, Any]],
        scan_id: str,
        target: str,
    ) -> VulnScanResult:
        """Parse ZAP alerts into VulnScanResult.

        Args:
            alerts: List of ZAP alert dictionaries
            scan_id: Scan identifier
            target: Target URL

        Returns:
            VulnScanResult with normalized findings
        """
        findings = []

        for alert in alerts:
            # Extract alert information
            alert_name = alert.get("name", "Unknown Alert")
            risk_str = alert.get("risk", "Info").lower()
            description = alert.get("description", "")
            solution = alert.get("solution", "")
            url = alert.get("url", target)
            method = alert.get("method", "GET")
            param = alert.get("param", "")
            attack = alert.get("attack", "")
            evidence = alert.get("evidence", "")
            cwe_id = alert.get("cweid", "")
            wasc_id = alert.get("wascid", "")

            # Map ZAP risk to VulnSeverity
            severity = self._map_zap_risk_to_severity(risk_str)

            # Map ZAP alert to VulnCategory
            category = self._map_zap_alert_to_category(alert_name, cwe_id, wasc_id)

            # Generate finding ID
            finding_id = f"ZAP-{hash(alert_name + url)[:8]}-{uuid.uuid4().hex[:8]}"

            # Build evidence string
            evidence_parts = []
            if attack:
                evidence_parts.append(f"Attack: {attack}")
            if evidence:
                evidence_parts.append(f"Evidence: {evidence}")
            if param:
                evidence_parts.append(f"Parameter: {param}")

            # References
            references = []
            if alert.get("reference"):
                ref = alert["reference"]
                if isinstance(ref, str):
                    references.append(ref)
                elif isinstance(ref, list):
                    references.extend(ref)

            # Create finding
            finding = VulnerabilityFinding(
                id=finding_id,
                title=f"ZAP: {alert_name}",
                description=description or f"{alert_name} detected at {url}",
                severity=severity,
                category=category,
                scanner="zap",
                target=target,
                endpoint=url,
                method=method,
                evidence="\n".join(evidence_parts) if evidence_parts else None,
                remediation=solution,
                references=references,
                cwe_id=f"CWE-{cwe_id}" if cwe_id else None,
                raw_data=alert,
                tags=[cwe_id, wasc_id, alert_name],
            )
            findings.append(finding)

        return VulnScanResult(
            scan_id=scan_id,
            scanner="zap",
            scan_type="web",
            target=target,
            start_time=datetime.utcnow().isoformat() + "Z",
            end_time=datetime.utcnow().isoformat() + "Z",
            duration_seconds=0.0,
            findings=findings,
            scan_metadata={
                "zap_version": "2.x",
                "alerts_count": len(alerts),
            },
        )

    def _map_zap_risk_to_severity(self, risk_str: str) -> VulnSeverity:
        """Map ZAP risk level to VulnSeverity.

        ZAP uses: High, Medium, Low, Informational
        """
        risk_lower = risk_str.lower()

        if risk_lower == "high":
            return VulnSeverity.HIGH
        elif risk_lower == "medium":
            return VulnSeverity.MEDIUM
        elif risk_lower == "low":
            return VulnSeverity.LOW
        elif risk_lower in ("informational", "info"):
            return VulnSeverity.INFO
        else:
            return VulnSeverity.UNKNOWN

    def _map_zap_alert_to_category(
        self,
        alert_name: str,
        cwe_id: str,
        wasc_id: str,
    ) -> VulnCategory:
        """Map ZAP alert to VulnCategory.

        Args:
            alert_name: Name of the ZAP alert
            cwe_id: CWE identifier
            wasc_id: WASC identifier

        Returns:
            VulnCategory
        """
        alert_lower = alert_name.lower()

        # CWE-based mapping
        if cwe_id:
            try:
                cwe_num = int(str(cwe_id)) if str(cwe_id).isdigit() else 0
            except (ValueError, TypeError):
                cwe_num = 0
            # Injection (CWE-78, CWE-89, CWE-90, CWE-94, etc.)
            if cwe_num in [78, 89, 90, 94, 95, 917, 943]:
                return VulnCategory.INJECTION
            # XSS (CWE-79)
            elif cwe_num == 79:
                return VulnCategory.INJECTION
            # Auth (CWE-287, CWE-306, CWE-307)
            elif cwe_num in [287, 306, 307, 384]:
                return VulnCategory.AUTH_FAILURES
            # Access Control (CWE-284, CWE-639)
            elif cwe_num in [284, 639, 862]:
                return VulnCategory.BROKEN_ACCESS_CONTROL
            # Crypto (CWE-311, CWE-312, CWE-326, CWE-327)
            elif cwe_num in [311, 312, 326, 327]:
                return VulnCategory.CRYPTOGRAPHIC_FAILURES
            # Info Disclosure (CWE-200, CWE-201)
            elif cwe_num in [200, 201]:
                return VulnCategory.INFO_DISCLOSURE
            # SSRF (CWE-918)
            elif cwe_num == 918:
                return VulnCategory.SSRF

        # Name-based mapping
        if any(
            k in alert_lower
            for k in [
                "injection",
                "sqli",
                "xss",
                "cross-site scripting",
                "csrf",
                "command",
                "ldap",
            ]
        ):
            return VulnCategory.INJECTION

        if any(k in alert_lower for k in ["auth", "session", "login", "password"]):
            return VulnCategory.AUTH_FAILURES

        if any(
            k in alert_lower
            for k in [
                "access control",
                "idor",
                "privilege",
                "authorization",
                "path traversal",
            ]
        ):
            return VulnCategory.BROKEN_ACCESS_CONTROL

        if any(
            k in alert_lower
            for k in [
                "crypto",
                "ssl",
                "tls",
                "certificate",
                "encryption",
                "cipher",
            ]
        ):
            return VulnCategory.CRYPTOGRAPHIC_FAILURES

        if any(
            k in alert_lower
            for k in [
                "header",
                "misconfig",
                "configuration",
                "cors",
                "content-type",
            ]
        ):
            return VulnCategory.SECURITY_MISCONFIGURATION

        if any(k in alert_lower for k in ["disclosure", "leak", "information", "exposure"]):
            return VulnCategory.INFO_DISCLOSURE

        if "ssrf" in alert_lower or "server-side request" in alert_lower:
            return VulnCategory.SSRF

        if any(
            k in alert_lower
            for k in [
                "cookie",
                "clickjack",
                "frame",
                "content security policy",
            ]
        ):
            return VulnCategory.SECURITY_MISCONFIGURATION

        return VulnCategory.UNKNOWN

    async def _load_policy(self, policy_name: str) -> None:
        """Load a ZAP scan policy.

        Args:
            policy_name: Name of the policy to load
        """
        session = await self._get_session()

        # First, try to get all policies
        result = await self._zap_api_request("/JSON/ascan/view/policies/", session)

        if result and "policies" in result:
            # Check if policy exists
            for policy in result["policies"]:
                if policy.get("name") == policy_name:
                    logger.info(f"Using ZAP policy: {policy_name}")
                    return

        logger.warning(f"ZAP policy '{policy_name}' not found, using default policy")
