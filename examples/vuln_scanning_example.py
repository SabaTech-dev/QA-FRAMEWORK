"""Vulnerability Scanning Example

Example usage of the unified vulnerability scanning system.
Shows how to scan web and network targets, parse results, and generate reports.
"""

import asyncio
import json
import logging
from src.adapters.vuln import (
    VulnClient,
    VulnScanResult,
    VulnerabilityFinding,
    VulnSeverity,
    VulnCategory,
    UnifiedVulnParser,
    VulnReportGenerator,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_web_scan():
    """Example: Run a web vulnerability scan."""
    logger.info("=" * 60)
    logger.info("DEMO 1: Web Vulnerability Scan")
    logger.info("=" * 60)

    client = VulnClient()

    # Check scanner health
    health = await client.health_check()
    logger.info(f"Scanner health: {json.dumps(health, indent=2)}")

    # List available Nuclei templates
    templates = await client.list_nuclei_templates()
    logger.info(f"Available templates: {len(templates)}")

    # Run web scan (replace with your target)
    result = await client.scan_web(
        target="https://example.com",
        use_nuclei=True,
        use_wstg=False,  # WSTG requires Docker image
        nuclei_templates=["qafw-sensitive-endpoints"],  # Our custom template
        severity_filter="medium",
    )

    logger.info(f"\nScan Result: {result.scan_id}")
    logger.info(f"  Total findings: {result.total_findings}")
    logger.info(f"  Critical: {result.critical_count}")
    logger.info(f"  High: {result.high_count}")
    logger.info(f"  Medium: {result.medium_count}")
    logger.info(f"  Duration: {result.duration_seconds:.1f}s")

    # Print findings
    if result.findings:
        logger.info("\nFindings:")
        for f in result.findings[:5]:
            logger.info(f"  [{f.severity.value.upper()}] {f.title}")
            logger.info(f"    Target: {f.endpoint}")
            logger.info(f"    Remediation: {f.remediation or 'N/A'}")
            logger.info("")

    # Generate reports
    report_paths = client.generate_report(result)
    logger.info(f"\nReports generated:")
    for fmt, path in report_paths.items():
        logger.info(f"  {fmt}: {path}")

    await client.close()


async def demo_network_scan():
    """Example: Run a network vulnerability scan."""
    logger.info("=" * 60)
    logger.info("DEMO 2: Network Vulnerability Scan")
    logger.info("=" * 60)

    client = VulnClient()

    result = await client.scan_network(
        target="127.0.0.1/32",
        templates=["dns", "ssl"],
        severity_filter="medium",
    )

    logger.info(f"\nNetwork Scan Result: {result.scan_id}")
    logger.info(f"  Total findings: {result.total_findings}")
    logger.info(f"  Critical: {result.critical_count}")
    logger.info(f"  High: {result.high_count}")

    if result.findings:
        for f in result.findings[:5]:
            logger.info(f"  [{f.severity.value.upper()}] {f.title}")

    await client.close()


async def demo_parse_existing():
    """Example: Parse existing Nuclei JSON output."""
    logger.info("=" * 60)
    logger.info("DEMO 3: Parse Existing Nuclei JSON")
    logger.info("=" * 60)

    # Simulated Nuclei JSON output
    sample_nuclei_output = [
        {
            "template-id": "missing-security-headers",
            "info": {
                "name": "Missing Security Headers",
                "description": "The target is missing important security headers",
                "severity": "medium",
                "tags": ["security", "headers", "misconfig"],
                "remediation": "Add Strict-Transport-Security, X-Frame-Options, and Content-Security-Policy headers",
            },
            "matched-at": "https://example.com/login",
            "type": "http",
        },
        {
            "template-id": "CVE-2023-1234",
            "info": {
                "name": "Example CVE Detection",
                "description": "Detected vulnerable library version",
                "severity": "critical",
                "tags": ["cve-2023-1234", "cwe-79", "injection"],
                "classification": {
                    "cvss-score": 9.8,
                },
                "reference": [
                    "https://nvd.nist.gov/vuln/detail/CVE-2023-1234",
                ],
            },
            "matched-at": "https://example.com/js/lib.js",
            "extracted-results": ["jquery-1.7.2.min.js"],
        },
    ]

    result = UnifiedVulnParser.parse_nuclei_json(
        json_data=sample_nuclei_output,
        scan_id="demo-parse-001",
        target="https://example.com",
        scan_type="web",
    )

    logger.info(f"Parsed {result.total_findings} findings:")
    for f in result.findings:
        logger.info(f"  [{f.severity.value.upper()}] {f.title}")
        logger.info(f"    CVE: {f.cve_id or 'N/A'}, CVSS: {f.cvss_score or 'N/A'}")
        logger.info(f"    Category: {f.category.value}")

    # Generate OWASP format
    owasp = UnifiedVulnParser.to_owasp_format(result)
    logger.info(f"\nOWASP Risk Assessment:")
    logger.info(f"  Risk Score: {owasp['risk_score']}")
    logger.info(f"  Risk Level: {owasp['risk_level']}")
    logger.info(f"  Category Breakdown: {json.dumps(owasp['category_breakdown'], indent=2)}")

    # Generate reports
    reporter = VulnReportGenerator()
    paths = reporter.generate_all(result, base_name="demo_parse")
    logger.info(f"\nReports: {json.dumps(paths, indent=2)}")


async def demo_manual_finding():
    """Example: Manually create findings and generate reports."""
    logger.info("=" * 60)
    logger.info("DEMO 4: Manual Finding Creation")
    logger.info("=" * 60)

    from datetime import datetime

    finding1 = VulnerabilityFinding(
        id="MANUAL-001",
        title="SQL Injection in Login Parameter",
        description="The 'username' parameter is vulnerable to SQL injection attacks",
        severity=VulnSeverity.CRITICAL,
        category=VulnCategory.INJECTION,
        scanner="manual",
        target="https://example.com/login",
        endpoint="/login?username=admin",
        method="POST",
        evidence="' OR '1'='1' -- returned all users",
        remediation="Use parameterized queries or prepared statements",
        references=[
            "https://owasp.org/www-community/attacks/SQL_Injection",
            "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
        ],
        cve_id="CVE-2023-0001",
        cvss_score=9.1,
    )

    finding2 = VulnerabilityFinding(
        id="MANUAL-002",
        title="Missing X-Frame-Options Header",
        description="The application does not set X-Frame-Options header, making it vulnerable to clickjacking",
        severity=VulnSeverity.MEDIUM,
        category=VulnCategory.CLICKJACKING,
        scanner="manual",
        target="https://example.com",
        remediation="Add 'X-Frame-Options: DENY' header to all responses",
        references=["https://owasp.org/www-community/attacks/Clickjacking"],
    )

    result = VulnScanResult(
        scan_id="manual-demo",
        scanner="manual",
        scan_type="web",
        target="https://example.com",
        start_time=datetime.utcnow().isoformat() + "Z",
        end_time=datetime.utcnow().isoformat() + "Z",
        duration_seconds=0.0,
        findings=[finding1, finding2],
    )

    logger.info(f"Created {result.total_findings} findings manually")

    reporter = VulnReportGenerator()
    paths = reporter.generate_all(result, base_name="manual_demo")
    logger.info(f"Reports generated:")
    for fmt, path in paths.items():
        logger.info(f"  {fmt}: {path}")


async def main():
    """Run all demos."""
    logger.info("🔍 QA-Framework Vulnerability Scanning Demo")
    logger.info("")

    try:
        await demo_web_scan()
    except Exception as e:
        logger.error(f"Web scan demo failed: {e}")

    logger.info("")
    try:
        await demo_parse_existing()
    except Exception as e:
        logger.error(f"Parse demo failed: {e}")

    logger.info("")
    try:
        await demo_manual_finding()
    except Exception as e:
        logger.error(f"Manual finding demo failed: {e}")

    logger.info("\n✅ Demos completed")


if __name__ == "__main__":
    asyncio.run(main())
