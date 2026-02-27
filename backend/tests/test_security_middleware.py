# =============================================================================
# Security Middleware Test Suite
# =============================================================================
# Tests for SecurityHeadersMiddleware and TrustedHostMiddleware.
# =============================================================================

import pytest
from httpx import AsyncClient


class TestSecurityHeaders:
    """Tests for security headers on API responses."""

    async def test_response_has_x_content_type_options(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    async def test_response_has_x_frame_options(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    async def test_response_has_x_xss_protection(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    async def test_response_has_referrer_policy(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert (
            response.headers.get("Referrer-Policy")
            == "strict-origin-when-cross-origin"
        )

    async def test_response_has_permissions_policy(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        pp = response.headers.get("Permissions-Policy")
        assert pp is not None
        assert "camera=()" in pp
        assert "microphone=()" in pp

    async def test_response_has_cache_control(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        cc = response.headers.get("Cache-Control")
        assert cc is not None
        assert "no-store" in cc

    async def test_security_headers_on_error_responses(self, client: AsyncClient):
        """Security headers should be present even on error responses."""
        response = await client.get("/api/v1/analysis/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    async def test_security_headers_on_post_request(self, client: AsyncClient):
        """Security headers should be present on POST responses too."""
        response = await client.post("/api/v1/analyze", json={"url": ""})
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


# =============================================================================
# Test TrustedHostMiddleware (unit)
# =============================================================================


class TestTrustedHostMiddleware:
    """Unit tests for TrustedHostMiddleware logic."""

    def test_middleware_import(self):
        from app.middleware.security import TrustedHostMiddleware
        assert TrustedHostMiddleware is not None

    def test_valid_host_check(self):
        from app.middleware.security import TrustedHostMiddleware

        middleware = TrustedHostMiddleware(
            app=None, allowed_hosts=["example.com", "*.example.com"]
        )
        assert middleware._is_valid_host("example.com") is True
        assert middleware._is_valid_host("sub.example.com") is True
        assert middleware._is_valid_host("evil.com") is False

    def test_wildcard_allows_any(self):
        from app.middleware.security import TrustedHostMiddleware

        middleware = TrustedHostMiddleware(app=None, allowed_hosts=["*"])
        assert middleware.allow_any is True

    def test_hosts_are_lowercased(self):
        from app.middleware.security import TrustedHostMiddleware

        middleware = TrustedHostMiddleware(
            app=None, allowed_hosts=["Example.COM"]
        )
        assert "example.com" in middleware.allowed_hosts
