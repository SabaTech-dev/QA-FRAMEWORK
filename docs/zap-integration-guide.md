# OWASP ZAP Integration Guide

## Overview

The QA-FRAMEWORK includes an OWASP ZAP (Zed Attack Proxy) scanner adapter for comprehensive web application security testing. ZAP is a widely used security tool for finding vulnerabilities in web applications.

## Features

- **Automated Docker-based execution**: ZAP runs in a Docker container for isolation and reproducibility
- **Spider and Active Scan**: Full web crawling and vulnerability detection
- **Policy-based scanning**: Support for custom ZAP scan policies
- **Unified results**: Normalized vulnerability findings consistent with Nuclei and WSTG
- **Async/await support**: Non-blocking operations for efficient scanning
- **Health monitoring**: Built-in health checks for the ZAP daemon

## Setup

### Prerequisites

1. **Docker**: Ensure Docker is installed and running
2. **Python 3.12+**: Required for the Python adapter
3. **Network access**: The `qa-network` Docker network should exist (created automatically)

### Installation

The required dependencies are already in `requirements.txt`:

```txt
aiohttp>=3.13.3
zaproxy>=0.4.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

### Default Configuration

The `ZAPScanner` uses sensible defaults:

```python
proxy_host: str = "127.0.0.1"
proxy_port: int = 8080
api_key: Optional[str] = None
daemon_port: int = 8080
spider_duration: int = 60
active_scan_duration: int = 120
ajax_spider_enabled: bool = False
docker_image: str = "ghcr.io/zaproxy/zaproxy:stable"
network: str = "qa-network"
```

### Custom Configuration

You can customize the ZAP scanner configuration:

```python
from src.adapters.vuln import ZAPScanner, ZAPScannerConfig

config = ZAPScannerConfig(
    proxy_host="127.0.0.1",
    proxy_port=8080,
    api_key="your-api-key-here",  # Optional
    spider_duration=120,  # 2 minutes for spider
    active_scan_duration=300,  # 5 minutes for active scan
    docker_image="ghcr.io/zaproxy/zaproxy:stable",
)

scanner = ZAPScanner(config=config)
```

## Usage

### Basic Web Scan

```python
import asyncio
from src.adapters.vuln import ZAPScanner

async def main():
    scanner = ZAPScanner()

    # Scan a web target
    result = await scanner.scan_web("https://example.com")

    # Check results
    print(f"Total findings: {result.total_findings}")
    print(f"Critical: {result.critical_count}")
    print(f"High: {result.high_count}")
    print(f"Medium: {result.medium_count}")
    print(f"Low: {result.low_count}")

    # View individual findings
    for finding in result.findings:
        print(f"[{finding.severity}] {finding.title}")
        print(f"  Description: {finding.description}")
        print(f"  Remediation: {finding.remediation}")
        print()

    await scanner.close()

asyncio.run(main())
```

### Using VulnClient

```python
import asyncio
from src.adapters.vuln import VulnClient

async def main():
    async with VulnClient() as client:
        # Run ZAP scan along with other scanners
        result = await client.scan_web(
            target="https://example.com",
            use_nuclei=False,  # Only use ZAP
            use_wstg=False,
            use_zap=True,
        )

        print(f"ZAP findings: {result.total_findings}")

asyncio.run(main())
```

### Scan with Custom Policy

```python
import asyncio
from src.adapters.vuln import ZAPScanner

async def main():
    scanner = ZAPScanner()

    # Scan with a specific policy
    result = await scanner.scan_with_policy(
        target="https://example.com",
        policy_name="default-policy",
    )

    print(f"Policy scan findings: {result.total_findings}")

    await scanner.close()

asyncio.run(main())
```

### Async Context Manager

```python
import asyncio
from src.adapters.vuln import ZAPScanner

async def main():
    async with ZAPScanner() as scanner:
        # Use the scanner
        result = await scanner.scan_web("https://example.com")
        print(f"Findings: {result.total_findings}")
    # Automatically closed

asyncio.run(main())
```

### Health Check

```python
import asyncio
from src.adapters.vuln import ZAPScanner

async def main():
    scanner = ZAPScanner()

    # Check if ZAP is healthy
    health = await scanner.health_check()
    print(f"Status: {health['status']}")
    print(f"Version: {health.get('version', 'unknown')}")
    print(f"API URL: {health.get('api_url', 'unknown')}")

    await scanner.close()

asyncio.run(main())
```

## Advanced Usage

### Disabling Spider or Active Scan

```python
import asyncio
from src.adapters.vuln import ZAPScanner

async def main():
    scanner = ZAPScanner()

    # Only run spider (no active scan)
    result = await scanner.scan_web(
        target="https://example.com",
        spider_enabled=True,
        active_scan_enabled=False,
    )

    # Only run active scan (no spider)
    result = await scanner.scan_web(
        target="https://example.com",
        spider_enabled=False,
        active_scan_enabled=True,
    )

    await scanner.close()

asyncio.run(main())
```

### Custom Scan Durations

```python
import asyncio
from src.adapters.vuln import ZAPScanner

async def main():
    scanner = ZAPScanner()

    # Extended scan durations
    result = await scanner.scan_web(
        target="https://example.com",
        spider_duration=300,  # 5 minutes spider
        active_scan_duration=600,  # 10 minutes active scan
    )

    await scanner.close()

asyncio.run(main())
```

## Result Interpretation

### VulnScanResult Structure

```python
result = VulnScanResult(
    scan_id="zap-web-abc123...",
    scanner="zap",
    scan_type="web",
    target="https://example.com",
    start_time="2024-01-01T00:00:00Z",
    end_time="2024-01-01T00:05:00Z",
    duration_seconds=300.0,
    total_findings=15,
    critical_count=2,
    high_count=5,
    medium_count=6,
    low_count=2,
    findings=[...],  # List of VulnerabilityFinding objects
    scan_metadata={
        "zap_version": "2.x",
        "alerts_count": 15,
    },
)
```

### VulnerabilityFinding Structure

```python
finding = VulnerabilityFinding(
    id="ZAP-abc123-def456...",
    title="ZAP: Cross Site Scripting (Reflected)",
    description="The application is vulnerable to reflected XSS...",
    severity=VulnSeverity.HIGH,
    category=VulnCategory.INJECTION,
    scanner="zap",
    target="https://example.com",
    endpoint="/search",
    method="GET",
    evidence="Attack: <script>alert(1)</script>\nEvidence: reflection in response",
    remediation="Encode all user input before reflecting in responses",
    cwe_id="CWE-79",
    raw_data={...},  # Original ZAP alert data
)
```

## Severity Mapping

ZAP risk levels are mapped to the framework's severity levels:

| ZAP Risk | Framework Severity |
|----------|-------------------|
| High | HIGH |
| Medium | MEDIUM |
| Low | LOW |
| Informational | INFO |

## Category Mapping

ZAP alerts are automatically categorized based on:

1. **CWE ID** (Common Weakness Enumeration)
2. **Alert name** patterns
3. **WASC ID** (Web Application Security Consortium)

Categories include:
- Injection (SQLi, XSS, Command Injection)
- Authentication Failures
- Broken Access Control
- Cryptographic Failures
- Information Disclosure
- Security Misconfiguration
- SSRF (Server-Side Request Forgery)

## Docker Details

### Container Management

The ZAP scanner automatically:
1. Starts a ZAP daemon container
2. Waits for the daemon to be ready
3. Executes the scan
4. Collects alerts
5. Stops and removes the container

### Network

The scanner uses the `qa-network` Docker network. Ensure this network exists:

```bash
docker network create qa-network
```

### Resource Limits

For production use, consider adding Docker resource limits:

```python
# In ZAPScannerConfig (not yet implemented)
memory_limit: str = "2g"
cpu_limit: str = "2.0"
```

## Troubleshooting

### Container Won't Start

**Symptom**: `Failed to start ZAP daemon`

**Solutions**:
1. Check Docker is running: `docker ps`
2. Verify Docker network exists: `docker network ls`
3. Check available disk space: `df -h`
4. Verify ZAP image can be pulled: `docker pull ghcr.io/zaproxy/zaproxy:stable`

### Scan Timeout

**Symptom**: Scan takes too long or times out

**Solutions**:
1. Increase `spider_duration` or `active_scan_duration`
2. Disable spider if the site is already well-known: `spider_enabled=False`
3. Use scan with policy instead of full scan
4. Check network connectivity to target

### No Findings

**Symptom**: Scan completes with zero findings

**Solutions**:
1. Verify target is accessible: `curl https://example.com`
2. Check ZAP logs: `docker logs <container-id>`
3. Ensure target is not blocking scanners (WAF, rate limits)
4. Try a different scan policy
5. Verify ZAP daemon is healthy: `await scanner.health_check()`

### API Connection Errors

**Symptom**: `ZAP API request error`

**Solutions**:
1. Check ZAP daemon is running: `docker ps | grep zaproxy`
2. Verify API URL is correct: `http://127.0.0.1:8080`
3. If using API key, ensure it matches: `api_key="your-key"`
4. Check firewall rules allow local connections

## Best Practices

### 1. Scan Responsibly

- **Get permission**: Only scan targets you own or have authorization to test
- **Respect rate limits**: Use appropriate scan durations to avoid overwhelming servers
- **Scan in staging**: Test against non-production environments first

### 2. Optimize Scans

- **Use policies**: Create custom policies for different application types
- **Targeted scans**: Disable spider for known applications to save time
- **Incremental scanning**: Start with short durations, increase if needed

### 3. Monitor Resources

- **Check memory usage**: ZAP can be memory-intensive for large applications
- **Monitor disk space**: Scan results are stored in the output directory
- **Clean up containers**: Containers are automatically removed after scanning

### 4. Integrate with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run ZAP scan
  run: |
    python -c "
    import asyncio
    from src.adapters.vuln import ZAPScanner

    async def scan():
        scanner = ZAPScanner()
        result = await scanner.scan_web('https://staging.example.com')
        if result.critical_count > 0 or result.high_count > 0:
            raise Exception(f'Found {result.critical_count} critical and {result.high_count} high vulnerabilities')
        await scanner.close()

    asyncio.run(scan())
    "
```

## Performance Considerations

### Scan Duration

Typical scan times for different targets:

| Target Size | Spider Duration | Active Scan Duration | Total Time |
|-------------|-----------------|---------------------|------------|
| Small (10 pages) | 1-2 min | 2-5 min | 3-7 min |
| Medium (50 pages) | 2-5 min | 5-15 min | 7-20 min |
| Large (200+ pages) | 5-15 min | 15-60 min | 20-75 min |

### Resource Usage

- **Memory**: 1-2 GB typical, up to 4 GB for large scans
- **CPU**: 1-2 cores typical, bursts during active scan
- **Disk**: 100-500 MB for scan results

### Optimization Tips

1. **Skip spider** for well-known applications
2. **Use custom policies** to focus on relevant vulnerabilities
3. **Set appropriate timeouts** to avoid long-running scans
4. **Run during off-hours** for production scans

## Security Considerations

### API Key Usage

For production environments, use an API key:

```python
config = ZAPScannerConfig(api_key="your-secure-api-key")
```

Generate a secure key:

```bash
# Using Python
python -c "import secrets; print(secrets.token_hex(16))"
```

### Network Isolation

- ZAP runs in a Docker container
- Uses the `qa-network` for controlled network access
- Cannot access host filesystem (except mounted output directory)

### Data Handling

- Scan results contain sensitive vulnerability information
- Store reports securely
- Don't commit raw scan results to version control
- Clean up old reports regularly

## Further Reading

- [OWASP ZAP Official Documentation](https://www.zaproxy.org/docs/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [ZAP API Documentation](https://www.zaproxy.org/docs/api/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the test files in `tests/vuln/test_vuln_scanner.py`
3. Examine the implementation in `src/adapters/vuln/zap_scanner.py`
4. Check the example in `examples/zap_scan_example.py`

## Changelog

### Version 1.0.0 (2024-01-01)
- Initial implementation
- Docker-based ZAP daemon management
- Spider and active scan support
- Policy-based scanning
- Unified result parsing
- Health monitoring
- Async/await support