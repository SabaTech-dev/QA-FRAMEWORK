"""Example: OWASP ZAP Scanner Usage

This example demonstrates how to use the ZAPScanner
for web application security testing.
"""

import asyncio
from pathlib import Path

from src.adapters.vuln import ZAPScanner, ZAPScannerConfig, VulnClient


async def example_basic_scan():
    """Example 1: Basic web scan with ZAP."""
    print("=== Example 1: Basic Web Scan ===")

    scanner = ZAPScanner()

    # Check if ZAP is healthy before scanning
    health = await scanner.health_check()
    print(f"ZAP Status: {health['status']}")

    # Scan a target (replace with your target URL)
    target = "https://example.com"
    result = await scanner.scan_web(target)

    # Display results
    print(f"\nScan Results for {target}:")
    print(f"  Total Findings: {result.total_findings}")
    print(f"  Critical: {result.critical_count}")
    print(f"  High: {result.high_count}")
    print(f"  Medium: {result.medium_count}")
    print(f"  Low: {result.low_count}")
    print(f"  Info: {result.info_count}")
    print(f"  Duration: {result.duration_seconds:.2f}s")

    # Show top 5 findings by severity
    print("\nTop Critical Findings:")
    critical_findings = result.get_findings_by_severity(
        result.findings[0].severity.__class__.CRITICAL
    )
    for finding in critical_findings[:5]:
        print(f"\n  [{finding.severity}] {finding.title}")
        print(f"    Endpoint: {finding.endpoint}")
        print(f"    CWE: {finding.cwe_id}")
        print(f"    Description: {finding.description[:100]}...")

    await scanner.close()


async def example_custom_config():
    """Example 2: Custom ZAP configuration."""
    print("\n=== Example 2: Custom Configuration ===")

    # Create custom configuration
    config = ZAPScannerConfig(
        proxy_host="127.0.0.1",
        proxy_port=8080,
        spider_duration=120,  # 2 minutes
        active_scan_duration=300,  # 5 minutes
        api_key=None,  # Set your API key here if needed
    )

    scanner = ZAPScanner(config=config)

    # Scan with custom configuration
    target = "https://example.com"
    result = await scanner.scan_web(
        target=target,
        spider_enabled=True,
        active_scan_enabled=True,
    )

    print(f"Scan completed with {result.total_findings} findings")

    await scanner.close()


async def example_scan_with_policy():
    """Example 3: Scan with a specific ZAP policy."""
    print("\n=== Example 3: Scan with Policy ===")

    scanner = ZAPScanner()

    target = "https://example.com"
    policy_name = "default-policy"

    result = await scanner.scan_with_policy(
        target=target,
        policy_name=policy_name,
        spider_enabled=True,
        active_scan_enabled=True,
    )

    print(f"Policy scan '{policy_name}' completed")
    print(f"Findings: {result.total_findings}")

    await scanner.close()


async def example_disabled_components():
    """Example 4: Scan without spider or active scan."""
    print("\n=== Example 4: Spider Only (No Active Scan) ===")

    scanner = ZAPScanner()

    target = "https://example.com"

    # Only run spider, no active scan
    result = await scanner.scan_web(
        target=target,
        spider_enabled=True,
        active_scan_enabled=False,
        spider_duration=60,
    )

    print(f"Spider-only scan completed")
    print(f"Findings from spider context: {result.total_findings}")

    await scanner.close()


async def example_async_context_manager():
    """Example 5: Using ZAPScanner as async context manager."""
    print("\n=== Example 5: Async Context Manager ===")

    async with ZAPScanner() as scanner:
        target = "https://example.com"
        result = await scanner.scan_web(target)

        print(f"Scan completed: {result.total_findings} findings")
        print("Scanner automatically closed")


async def example_vuln_client():
    """Example 6: Using ZAP through VulnClient."""
    print("\n=== Example 6: VulnClient with ZAP ===")

    async with VulnClient() as client:
        # Run only ZAP scan
        result = await client.scan_web(
            target="https://example.com",
            use_nuclei=False,
            use_wstg=False,
            use_zap=True,
        )

        print(f"VulnClient ZAP scan: {result.total_findings} findings")

        # Check health of all scanners
        health = await client.health_check()
        print(f"\nHealth Check:")
        for scanner_name, status in health.items():
            print(f"  {scanner_name}: {status['status']}")


async def example_filter_findings():
    """Example 7: Filter findings by severity and category."""
    print("\n=== Example 7: Filter Findings ===")

    scanner = ZAPScanner()

    target = "https://example.com"
    result = await scanner.scan_web(target)

    from src.adapters.vuln import VulnSeverity, VulnCategory

    # Get only high and critical findings
    high_critical = [
        f for f in result.findings if f.severity in (VulnSeverity.HIGH, VulnSeverity.CRITICAL)
    ]
    print(f"High and Critical findings: {len(high_critical)}")

    # Get injection vulnerabilities
    injection_vulns = result.get_findings_by_category(VulnCategory.INJECTION)
    print(f"Injection vulnerabilities: {len(injection_vulns)}")

    # Show details of injection findings
    for finding in injection_vulns[:3]:
        print(f"\n  {finding.title}")
        print(f"    Severity: {finding.severity}")
        print(f"    Endpoint: {finding.endpoint}")
        if finding.remediation:
            print(f"    Remediation: {finding.remediation[:100]}...")

    await scanner.close()


async def example_error_handling():
    """Example 8: Error handling for ZAP scans."""
    print("\n=== Example 8: Error Handling ===")

    scanner = ZAPScanner()

    # Try to scan an invalid target
    target = "https://invalid-target-that-does-not-exist.example.com"
    result = await scanner.scan_web(target)

    if result.error:
        print(f"Scan failed with error: {result.error}")
    else:
        print(f"Scan completed: {result.total_findings} findings")

    await scanner.close()


async def main():
    """Run all examples."""
    print("OWASP ZAP Scanner Examples")
    print("=" * 50)
    print()

    # Run examples (comment out the ones you don't want to run)
    try:
        await example_basic_scan()
        await example_custom_config()
        await example_scan_with_policy()
        await example_disabled_components()
        await example_async_context_manager()
        await example_vuln_client()
        await example_filter_findings()
        await example_error_handling()
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
