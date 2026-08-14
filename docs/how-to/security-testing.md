# Security Testing Module

The Security Testing Module provides comprehensive security vulnerability testing including SQL injection, XSS, authentication, and rate limiting tests.

## Overview

This module helps identify common security vulnerabilities:
- **SQL Injection**: Tests for SQL injection vulnerabilities
- **XSS (Cross-Site Scripting)**: Tests for XSS vulnerabilities
- **Authentication**: Tests authentication mechanisms
- **Rate Limiting**: Tests API rate limiting implementation
- **Security Headers**: Validates security headers

## Architecture

```
src/adapters/security/
├── __init__.py              # Module exports
├── security_client.py       # Main facade client
├── sql_injection_tester.py  # SQL injection testing
├── xss_tester.py           # XSS testing
├── auth_tester.py          # Authentication testing
└── rate_limit_tester.py    # Rate limiting testing
```

## Quick Start

### SQL Injection Testing

```python
from src.adapters.security import SecurityClient
from src.adapters.http import HTTPXClient

async def test_sql_injection():
    http_client = HTTPXClient(base_url="http://example.com")
    client = SecurityClient(http_client)
    
    results = await client.test_sql_injection(
        target_url="/search",
        parameter="q",
        method="GET"
    )
    
    if results['vulnerable']:
        print(f"⚠️  SQL Injection vulnerabilities found!")
        for vuln in results['vulnerabilities']:
            print(f"  - Type: {vuln['injection_type']}")
            print(f"    Payload: {vuln['payload']}")
    
    await client.close()
```

### XSS Testing

```python
async def test_xss():
    http_client = HTTPXClient(base_url="http://example.com")
    client = SecurityClient(http_client)
    
    results = await client.test_xss(
        target_url="/comment",
        parameter="message",
        method="POST"
    )
    
    if results['vulnerable']:
        print(f"⚠️  XSS vulnerabilities found!")
        for vuln in results['vulnerabilities']:
            print(f"  - Type: {vuln['xss_type']}")
            print(f"    Severity: {vuln['severity']}")
    
    await client.close()
```

### Security Headers

```python
async def test_security_headers():
    http_client = HTTPXClient(base_url="http://example.com")
    client = SecurityClient(http_client)
    
    results = await client.test_security_headers("/")
    
    print(f"Security Score: {results['score']}/100")
    print(f"Grade: {results['grade']}")
    
    if results.get('missing_required'):
        print(f"\nMissing headers:")
        for header in results['missing_required']:
            print(f"  - {header}")
    
    await client.close()
```

### Full Security Scan

```python
async def full_security_scan():
    http_client = HTTPXClient(base_url="http://example.com")
    client = SecurityClient(http_client)
    
    results = await client.run_full_security_scan(
        target_url="/",
        parameters=["id", "search", "name"]
    )
    
    print(f"Overall Score: {results['overall_score']}/100")
    print(f"Overall Grade: {results['overall_grade']}")
    
    # Check individual test results
    headers_test = results['tests'].get('security_headers', {})
    if headers_test:
        print(f"Headers Score: {headers_test.get('score', 0)}/100")
    
    await client.close()
```

## Components

### SQLInjectionTester

Tests for SQL injection vulnerabilities using various payloads:

```python
from src.adapters.security import SQLInjectionTester
from src.adapters.security.sql_injection_tester import SQLInjectionPayload, InjectionType

tester = SQLInjectionTester()

# Use default payloads
results = await tester.test_parameter(
    http_client=http_client,
    target_url="http://example.com/search",
    parameter="q",
    method="GET"
)

# Add custom payloads
custom_payload = SQLInjectionPayload(
    payload="' UNION SELECT * FROM users--",
    injection_type=InjectionType.UNION_BASED,
    description="Union-based injection",
    expected_patterns=["union"],
    database_types=["mysql", "postgresql"]
)
tester.add_payload(custom_payload)
```

### XSSTester

Tests for Cross-Site Scripting vulnerabilities:

```python
from src.adapters.security import XSSTester
from src.adapters.security.xss_tester import XSSPayload, XSSType

tester = XSSTester()

# Test parameter
results = await tester.test_parameter(
    http_client=http_client,
    target_url="http://example.com/comment",
    parameter="message",
    method="POST"
)

# Test URL reflection
reflection_results = await tester.test_url_reflection(
    http_client=http_client,
    target_url="http://example.com/page"
)
```

### AuthTester

Tests authentication mechanisms:

```python
from src.adapters.security import AuthTester, AuthTestCase
from src.adapters.security.auth_tester import AuthTestType

tester = AuthTester()

# Test specific cases
test_cases = [
    AuthTestCase(
        name="Weak password test",
        test_type=AuthTestType.PASSWORD_POLICY,
        username="testuser",
        password="123",
        expected_success=False,
        description="Test weak password rejection"
    )
]

results = await tester.test_authentication(
    http_client=http_client,
    login_url="http://example.com/login",
    test_cases=test_cases
)

# Test common credentials
results = await tester.test_common_credentials(
    http_client=http_client,
    login_url="http://example.com/login"
)

# Test brute force protection
results = await tester.test_brute_force_protection(
    http_client=http_client,
    login_url="http://example.com/login",
    valid_username="admin",
    attempts=20
)
```

### RateLimitTester

Tests API rate limiting:

```python
from src.adapters.security import RateLimitTester

tester = RateLimitTester()

# Test rate limiting
results = await tester.test_rate_limiting(
    http_client=http_client,
    target_url="http://api.example.com/data",
    requests_count=100,
    time_window=10
)

# Test burst capacity
results = await tester.test_burst_capacity(
    http_client=http_client,
    target_url="http://api.example.com/data",
    burst_size=50
)

# Test rate limit recovery
results = await tester.test_rate_limit_recovery(
    http_client=http_client,
    target_url="http://api.example.com/data",
    limit=10,
    recovery_time=60
)
```

## Configuration

Add to your `config/qa.yaml`:

```yaml
security:
  sql_injection:
    enabled: true
    payloads: default        # default, extended, custom
    max_tests_per_endpoint: 50
  
  xss:
    enabled: true
    payloads: default
    test_reflection: true
  
  authentication:
    enabled: true
    test_common_credentials: true
    test_brute_force_protection: true
    brute_force_attempts: 10
  
  rate_limiting:
    enabled: true
    test_requests: 100
    test_window_seconds: 60
  
  headers:
    required:
      - Strict-Transport-Security
      - Content-Security-Policy
      - X-Content-Type-Options
      - X-Frame-Options
      - Referrer-Policy
```

## Security Test Types

### SQL Injection Types

- **Error-based**: Triggers database errors
- **Union-based**: Uses UNION statements
- **Boolean-based**: True/false inference
- **Time-based**: Time delay detection
- **Stacked queries**: Multiple statement execution

### XSS Types

- **Reflected**: Immediate reflection in response
- **Stored**: Persisted in database
- **DOM-based**: Client-side JavaScript execution
- **Blind**: Requires out-of-band detection

## Best Practices

1. **Test in Non-Production**: Always test in staging/dev environments
2. **Use Test Data**: Don't use real user credentials
3. **Check All Inputs**: Test all user-controllable parameters
4. **Review Results**: Manually verify positive findings
5. **Regular Testing**: Run security tests as part of CI/CD
6. **Stay Updated**: Keep payload lists current with new attack vectors

## Interpreting Results

### Security Scores

- **90-100 (A)**: Excellent security posture
- **80-89 (B)**: Good, minor improvements needed
- **70-79 (C)**: Acceptable, some vulnerabilities present
- **60-69 (D)**: Poor, significant issues found
- **Below 60 (F)**: Critical, immediate action required

### Vulnerability Severity

- **Critical**: Immediate exploitation possible (SQL injection, RCE)
- **High**: Easy to exploit, high impact (XSS, auth bypass)
- **Medium**: Moderate difficulty/impact (information disclosure)
- **Low**: Low impact or difficult to exploit

## Troubleshooting

### False Positives

If you encounter false positives:
1. Review the evidence provided
2. Manually verify the vulnerability
3. Adjust payload lists if needed
4. Consider application-specific context

### Test Failures

If tests fail to complete:
1. Check network connectivity
2. Verify target URL is accessible
3. Check for WAF blocking
4. Review timeout settings

## Examples

See `examples/security_testing_example.py` for complete working examples.