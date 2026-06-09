"""Scan API Routes - Vulnerability scanning endpoints

Provides API endpoints for Nuclei and WSTG vulnerability scanning.
Integrates with the QA-Framework vulnerability scanner modules.
"""

import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session as get_db
from services.auth_service import get_current_user
from models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["Vulnerability Scanning"])


# In-memory scan results store (would be DB in production)
_active_scans: Dict[str, Dict[str, Any]] = {}
_scan_results: Dict[str, Dict[str, Any]] = {}


from pydantic import BaseModel, Field, HttpUrl


class WebScanRequest(BaseModel):
    """Request body for web vulnerability scan."""

    target: str = Field(
        ..., description="Target URL to scan (e.g., https://example.com)",
        examples=["https://example.com"],
    )
    skip_nuclei: bool = Field(False, description="Skip Nuclei scan")
    skip_wstg: bool = Field(False, description="Skip WSTG scan")
    nuclei_templates: Optional[List[str]] = Field(
        None, description="Specific Nuclei templates to run"
    )
    wstg_categories: Optional[List[str]] = Field(
        None, description="WSTG categories to test (e.g., WSTG-INPV, WSTG-ATHN)"
    )
    severity_filter: Optional[str] = Field(
        None, description="Minimum severity filter (critical, high, medium, low, info)",
        pattern="^(critical|high|medium|low|info)$",
    )
    auth_token: Optional[str] = Field(None, description="Bearer token for authenticated scanning")
    cookie: Optional[str] = Field(None, description="Session cookie for authenticated scanning")
    rate_limit: int = Field(150, ge=5, le=1000, description="Max requests per second")
    timeout: Optional[int] = Field(None, ge=60, le=3600, description="Scan timeout in seconds")


class NetworkScanRequest(BaseModel):
    """Request body for network vulnerability scan."""

    target: str = Field(
        ..., description="Target IP/CIDR to scan (e.g., 10.0.0.1/24)",
        examples=["10.0.0.1/24", "192.168.1.0/24"],
    )
    templates: Optional[List[str]] = Field(
        None, description="Specific Nuclei templates to use (default: network, dns, ssl)"
    )
    severity_filter: Optional[str] = Field(
        None, description="Minimum severity filter",
        pattern="^(critical|high|medium|low|info)$",
    )
    rate_limit: int = Field(500, ge=10, le=5000, description="Max packets per second")
    timeout: Optional[int] = Field(None, ge=60, le=7200, description="Scan timeout in seconds")


def get_nuclei_scanner():
    """Get Nuclei scanner instance (lazy import to avoid dependency issues)."""
    try:
        from src.adapters.vuln.nuclei_scanner import NucleiScanner
        return NucleiScanner()
    except ImportError:
        logger.warning("NucleiScanner not available, using stub")
        return None


def get_wstg_scanner():
    """Get WSTG scanner instance."""
    try:
        from src.adapters.vuln.wstg_scanner import WSTGScanner
        return WSTGScanner()
    except ImportError:
        logger.warning("WSTGScanner not available, using stub")
        return None


# ─── Health & Status ──────────────────────────────────────────


@router.get(
    "/vuln/status",
    summary="Scanner health status",
    description="Check the health status of all vulnerability scanners.",
)
async def scan_status(current_user: User = Depends(get_current_user)):
    """Check health of Nuclei and WSTG scanners."""
    results = {
        "nuclei": {"status": "unavailable", "message": "Scanner not initialized"},
        "wstg": {"status": "unavailable", "message": "Scanner not initialized"},
        "active_scans": len(_active_scans),
    }

    nuclei = get_nuclei_scanner()
    if nuclei:
        try:
            results["nuclei"] = await nuclei.health_check()
        except Exception as e:
            results["nuclei"] = {"status": "error", "error": str(e)}

    wstg = get_wstg_scanner()
    if wstg:
        try:
            results["wstg"] = await wstg.health_check()
        except Exception as e:
            results["wstg"] = {"status": "error", "error": str(e)}

    return results


# ─── Web Vulnerability Scan ───────────────────────────────────


@router.post(
    "/vuln/web",
    summary="Scan web application for vulnerabilities",
    description="Run Nuclei + WSTG web vulnerability scan against a target URL.",
    response_description="Scan result with findings and severity breakdown",
    status_code=status.HTTP_202_ACCEPTED,
)
async def scan_web(
    scan_request: "WebScanRequest",
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Scan a web application for vulnerabilities.

    Combines Nuclei template-based scanning with OWASP WSTG methodology.
    Results include severity breakdown and remediation guidance.
    """
    scan_id = f"web-{uuid.uuid4().hex[:12]}"

    # Store initial scan state
    _active_scans[scan_id] = {
        "scan_id": scan_id,
        "type": "web",
        "target": scan_request.target,
        "status": "running",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "user_id": str(current_user.id) if hasattr(current_user, 'id') else "anonymous",
    }

    # Run scan in background
    background_tasks.add_task(
        _run_web_scan, scan_id, scan_request
    )

    return {
        "scan_id": scan_id,
        "status": "accepted",
        "target": scan_request.target,
        "message": "Web vulnerability scan started",
        "scan_url": f"/api/v1/scan/vuln/result/{scan_id}",
    }


@router.post(
    "/vuln/network",
    summary="Scan network for vulnerabilities",
    description="Run Nuclei network vulnerability scan against an IP/CIDR range.",
    response_description="Scan result with network findings",
    status_code=status.HTTP_202_ACCEPTED,
)
async def scan_network(
    scan_request: "NetworkScanRequest",
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Scan a network target for vulnerabilities.

    Uses Nuclei with network-specific templates (open ports, SSL/TLS, DNS).
    """
    scan_id = f"net-{uuid.uuid4().hex[:12]}"

    _active_scans[scan_id] = {
        "scan_id": scan_id,
        "type": "network",
        "target": scan_request.target,
        "status": "running",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "user_id": str(current_user.id) if hasattr(current_user, 'id') else "anonymous",
    }

    background_tasks.add_task(
        _run_network_scan, scan_id, scan_request
    )

    return {
        "scan_id": scan_id,
        "status": "accepted",
        "target": scan_request.target,
        "message": "Network vulnerability scan started",
        "scan_url": f"/api/v1/scan/vuln/result/{scan_id}",
    }


# ─── Scan Results ─────────────────────────────────────────────


@router.get(
    "/vuln/result/{scan_id}",
    summary="Get scan results",
    description="Retrieve the results of a completed or in-progress vulnerability scan.",
)
async def get_scan_result(
    scan_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get scan results by scan ID."""
    # Check active scans first
    if scan_id in _active_scans:
        scan_info = _active_scans[scan_id]
        if scan_info["status"] == "running":
            return {
                "scan_id": scan_id,
                "status": "running",
                "message": "Scan is still in progress",
                "started_at": scan_info["started_at"],
            }
        # If completed, check results
        if scan_id in _scan_results:
            return _scan_results[scan_id]

    # Check completed results
    if scan_id in _scan_results:
        return _scan_results[scan_id]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scan {scan_id} not found",
    )


@router.get(
    "/vuln/results",
    summary="List all scan results",
    description="List all completed vulnerability scan results.",
)
async def list_scan_results(
    limit: int = Query(20, ge=1, le=100),
    scanner: Optional[str] = Query(None, regex="^(nuclei|wstg|combined)$"),
    current_user: User = Depends(get_current_user),
):
    """List all completed scan results with optional filtering."""
    results = []
    for scan_id, result in _scan_results.items():
        if scanner and result.get("scanner") != scanner:
            continue

        results.append({
            "scan_id": scan_id,
            "scanner": result.get("scanner"),
            "scan_type": result.get("scan_type"),
            "target": result.get("target"),
            "total_findings": result.get("total_findings", 0),
            "critical_count": result.get("critical_count", 0),
            "high_count": result.get("high_count", 0),
            "medium_count": result.get("medium_count", 0),
            "end_time": result.get("end_time"),
        })

    # Sort by end_time descending
    results.sort(key=lambda r: r.get("end_time", ""), reverse=True)

    return {
        "total": len(results),
        "results": results[:limit],
        "active_scans": len(_active_scans),
    }


@router.delete(
    "/vuln/result/{scan_id}",
    summary="Delete scan result",
    description="Remove a scan result from storage.",
)
async def delete_scan_result(
    scan_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a scan result."""
    removed = False
    if scan_id in _active_scans:
        del _active_scans[scan_id]
        removed = True
    if scan_id in _scan_results:
        del _scan_results[scan_id]
        removed = True

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found",
        )

    return {"message": f"Scan {scan_id} deleted"}


# ─── Background Tasks ─────────────────────────────────────────


async def _run_web_scan(scan_id: str, request: "WebScanRequest"):
    """Execute web vulnerability scan in background."""
    import asyncio
    from src.adapters.vuln.vuln_report import VulnReportGenerator

    nuclei_results = None
    wstg_results = None
    errors = []

    # Run Nuclei scan
    nuclei = get_nuclei_scanner()
    if nuclei and not request.skip_nuclei:
        try:
            nuclei_results = await nuclei.scan_web(
                target=request.target,
                templates=request.nuclei_templates,
                severity=request.severity_filter,
                rate_limit=request.rate_limit,
                timeout=request.timeout or 300,
                scan_id=f"{scan_id}-nuclei",
            )
        except Exception as e:
            errors.append(f"Nuclei error: {e}")
            logger.error(f"Nuclei scan failed for {scan_id}: {e}")

    # Run WSTG scan
    wstg = get_wstg_scanner()
    if wstg and not request.skip_wstg:
        try:
            wstg_results = await wstg.scan_web(
                target=request.target,
                categories=request.wstg_categories,
                auth_token=request.auth_token,
                timeout=request.timeout or 600,
                scan_id=f"{scan_id}-wstg",
            )
        except Exception as e:
            errors.append(f"WSTG error: {e}")
            logger.error(f"WSTG scan failed for {scan_id}: {e}")

    # Merge results
    from src.adapters.vuln.vuln_parser import UnifiedVulnParser

    results_to_merge = [r for r in [nuclei_results, wstg_results] if r is not None]
    if results_to_merge:
        combined = UnifiedVulnParser.merge_results(results_to_merge)
        combined.scan_id = scan_id
        combined.scan_metadata.update({
            "scanners_used": [r.scanner for r in results_to_merge],
            "errors": errors,
        })

        # Generate reports
        try:
            reporter = VulnReportGenerator()
            report_paths = reporter.generate_all(combined, base_name=f"scan_{scan_id}")
            combined.scan_metadata["reports"] = report_paths
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
    else:
        combined = results_to_merge[0] if results_to_merge else None

    # Store result
    if combined:
        _scan_results[scan_id] = combined.to_dict()
    else:
        _scan_results[scan_id] = {
            "scan_id": scan_id,
            "scanner": "combined",
            "scan_type": "web",
            "target": request.target,
            "error": "; ".join(errors) if errors else "No scanners available",
            "total_findings": 0,
            "findings": [],
        }

    _active_scans[scan_id]["status"] = "completed"
    logger.info(f"Web scan {scan_id} completed: {_scan_results[scan_id].get('total_findings', 0)} findings")


async def _run_network_scan(scan_id: str, request: "NetworkScanRequest"):
    """Execute network vulnerability scan in background."""
    from src.adapters.vuln.vuln_report import VulnReportGenerator

    nuclei = get_nuclei_scanner()
    if not nuclei:
        _scan_results[scan_id] = {
            "scan_id": scan_id,
            "scanner": "nuclei",
            "scan_type": "network",
            "target": request.target,
            "error": "Nuclei scanner not available",
        }
        _active_scans[scan_id]["status"] = "completed"
        return

    try:
        result = await nuclei.scan_network(
            target=request.target,
            templates=request.templates,
            severity=request.severity_filter,
            rate_limit=request.rate_limit,
            timeout=request.timeout or 600,
            scan_id=scan_id,
        )

        # Generate reports
        try:
            reporter = VulnReportGenerator()
            report_paths = reporter.generate_all(result, base_name=f"scan_{scan_id}")
            result.scan_metadata["reports"] = report_paths
        except Exception as e:
            logger.error(f"Network report generation failed: {e}")

        _scan_results[scan_id] = result.to_dict()

    except Exception as e:
        logger.error(f"Network scan failed for {scan_id}: {e}")
        _scan_results[scan_id] = {
            "scan_id": scan_id,
            "scanner": "nuclei",
            "scan_type": "network",
            "target": request.target,
            "error": str(e),
            "total_findings": 0,
            "findings": [],
        }

    _active_scans[scan_id]["status"] = "completed"
    logger.info(f"Network scan {scan_id} completed: {_scan_results[scan_id].get('total_findings', 0)} findings")
