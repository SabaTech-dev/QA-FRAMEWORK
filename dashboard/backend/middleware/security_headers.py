"""
Security Headers Middleware for QA-FRAMEWORK.

Adds essential security headers to all responses to protect against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.)
"""

import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# F-5 (OWASP API8:2023 / ASVS V14.4): explicit HTTP caching policy.
# Default is the safe no-store — covers every authenticated response
# (PII must never be CDN/browser cacheable). Only explicitly listed
# public endpoints opt into caching, with a short env-driven max-age.
PUBLIC_CACHEABLE_PATHS = {"/api/v1/billing/plans"}


def cache_policy_for(path: str) -> str:
    """Return the Cache-Control value for a request path."""
    if path in PUBLIC_CACHEABLE_PATHS:
        max_age = int(os.getenv("CACHE_CONTROL_PUBLIC_MAX_AGE", "300"))
        return f"public, max-age={max_age}"
    return "no-store"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Headers added:
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME sniffing
    - Strict-Transport-Security: Forces HTTPS
    - X-XSS-Protection: XSS filter (legacy but still useful)
    - Content-Security-Policy: Prevents XSS and injection attacks
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features
    - Cache-Control: Default no-store; explicit short max-age on public
      cacheable endpoints (F-5, OWASP API8:2023 / ASVS V14.4)
    """

    async def dispatch(self, request: Request, call_next):
        # Call next middleware/route handler
        response: Response = await call_next(request)

        # Add security headers
        headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Force HTTPS (1 year, include subdomains)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            # XSS Protection (legacy but still useful for older browsers)
            "X-XSS-Protection": "1; mode=block",
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Restrict browser features
            "Permissions-Policy": (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            ),
            # Content Security Policy (restrictive but functional)
            # Note: Adjust as needed for your application
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self'; "  # Removed unsafe-inline and unsafe-eval
                "style-src 'self'; "  # Removed unsafe-inline
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "  # Allow HTTPS API calls
                "frame-ancestors 'none'; "  # Equivalent to X-Frame-Options: DENY
                "base-uri 'self'; "
                "form-action 'self'"
            ),
        }

        # Add headers to response
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value

        # F-5: default-safe cache policy; never override a handler's
        # explicit Cache-Control.
        if "cache-control" not in response.headers:
            response.headers["Cache-Control"] = cache_policy_for(request.url.path)

        return response


# Alternative: Function to add headers manually if middleware is not desired
def add_security_headers(response: Response) -> Response:
    """
    Manually add security headers to a response.
    Use this if you can't use middleware for some reason.
    """
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "  # Removed unsafe-inline and unsafe-eval
        "style-src 'self'; "  # Removed unsafe-inline
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response
