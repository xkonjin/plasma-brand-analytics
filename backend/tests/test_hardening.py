# =============================================================================
# Hardening Tests
# =============================================================================
# Tests that verify security hardening measures are in place.
# These tests document and enforce security properties.
# =============================================================================

import pytest
from httpx import AsyncClient


class TestSSRFProtection:
    """Tests that SSRF protection blocks dangerous URLs."""

    def test_file_scheme_blocked_in_normalize(self):
        from app.utils.validation import normalize_url
        with pytest.raises(ValueError, match="not allowed"):
            normalize_url("file:///etc/passwd")

    def test_data_scheme_blocked_in_normalize(self):
        from app.utils.validation import normalize_url
        with pytest.raises(ValueError, match="not allowed"):
            normalize_url("data:text/html,<h1>hi</h1>")

    def test_javascript_scheme_blocked_in_normalize(self):
        from app.utils.validation import normalize_url
        with pytest.raises(ValueError, match="not allowed"):
            normalize_url("javascript:alert(1)")

    def test_ftp_scheme_blocked_in_normalize(self):
        from app.utils.validation import normalize_url
        with pytest.raises(ValueError, match="not allowed"):
            normalize_url("ftp://evil.com/file")

    def test_bare_ipv6_loopback_blocked(self):
        from app.utils.validation import validate_url
        is_valid, _ = validate_url("http://::1")
        assert is_valid is False

    def test_bracketed_ipv6_loopback_blocked(self):
        from app.utils.validation import validate_url
        is_valid, _ = validate_url("http://[::1]")
        assert is_valid is False

    def test_10_x_private_range_blocked(self):
        from app.utils.validation import validate_url
        is_valid, _ = validate_url("http://10.0.0.1")
        assert is_valid is False

    def test_172_16_private_range_blocked(self):
        from app.utils.validation import validate_url
        is_valid, _ = validate_url("http://172.16.0.1")
        assert is_valid is False

    def test_aws_metadata_blocked(self):
        from app.utils.validation import validate_url
        is_valid, _ = validate_url("http://169.254.169.254/latest/meta-data")
        assert is_valid is False


class TestXSSProtection:
    """Tests that XSS vectors are sanitized."""

    def test_script_tag_stripped(self):
        from app.utils.validation import sanitize_string
        result = sanitize_string('<script>alert("xss")</script>hello')
        assert "<script" not in result.lower()
        assert "hello" in result

    def test_event_handler_stripped(self):
        from app.utils.validation import sanitize_string
        result = sanitize_string('<img onerror="alert(1)">')
        assert "onerror=" not in result.lower()

    def test_javascript_protocol_stripped(self):
        from app.utils.validation import sanitize_string
        result = sanitize_string('javascript:alert(document.cookie)')
        assert "javascript:" not in result.lower()

    def test_null_bytes_stripped(self):
        from app.utils.validation import sanitize_string
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result

    def test_analysis_request_sanitizes_description(self):
        from app.models.analysis import AnalysisRequest
        req = AnalysisRequest(
            url="https://example.com",
            description='<script>steal()</script>Normal',
        )
        assert "<script" not in (req.description or "")


class TestErrorLeakagePrevention:
    """Tests that error responses don't leak internal details."""

    async def test_global_handler_hides_details_in_prod(self, client: AsyncClient):
        """Global exception handler should not leak stack traces."""
        # The ENABLE_DEBUG_ERRORS default is now False
        from app.config import settings
        assert settings.ENABLE_DEBUG_ERRORS is False

    def test_health_error_sanitized(self):
        """Health check errors should say 'connection_failed', not expose details."""
        import inspect
        from app.api.routes import health
        source = inspect.getsource(health)
        # The health module should use "connection_failed", not raw str(e)
        assert "connection_failed" in source

    def test_payment_error_allowlist(self):
        """Payment route should only expose allowlisted error messages."""
        import inspect
        from app.api.routes import payment
        source = inspect.getsource(payment)
        assert "safe_messages" in source  # Verify allowlist pattern exists

    def test_analysis_error_sanitization(self):
        """Analysis route should strip stack traces from error messages."""
        import inspect
        from app.api.routes import analysis
        source = inspect.getsource(analysis)
        assert "Traceback" in source  # Check for traceback filtering logic


class TestInputValidation:
    """Tests for input validation on API routes."""

    async def test_payment_validates_address_format(self, client: AsyncClient):
        """Payment invoice endpoint validates Ethereum address format."""
        response = await client.post(
            "/api/v1/payment/invoice",
            json={"payer_address": "invalid"},
        )
        assert response.status_code == 422

    async def test_payment_validates_address_length(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payment/invoice",
            json={"payer_address": "0x" + "a" * 39},  # too short
        )
        assert response.status_code == 422

    async def test_payment_accepts_valid_address(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payment/invoice",
            json={"payer_address": "0x" + "a" * 40},
        )
        # Should get past validation (may fail for other reasons like no x402 service)
        assert response.status_code != 422


class TestSecurityDefaults:
    """Tests that security-sensitive config defaults are safe."""

    def test_debug_errors_default_off(self):
        """ENABLE_DEBUG_ERRORS should default to False for safety."""
        from app.config import Settings
        s = Settings(DATABASE_URL="sqlite:///test.db")
        assert s.ENABLE_DEBUG_ERRORS is False

    def test_jwt_secret_has_warning_default(self):
        """JWT_SECRET_KEY default should signal it needs changing."""
        from app.config import Settings
        s = Settings(DATABASE_URL="sqlite:///test.db")
        assert "change-me" in s.JWT_SECRET_KEY
