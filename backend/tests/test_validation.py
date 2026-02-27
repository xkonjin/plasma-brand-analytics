# =============================================================================
# Validation Utilities Test Suite
# =============================================================================
# Tests for URL validation, email validation, string sanitization, and
# input normalization utilities.
# =============================================================================

import pytest
from app.utils.validation import (
    sanitize_string,
    validate_url,
    validate_email,
    normalize_url,
    BLOCKED_HOSTS,
    BLOCKED_SCHEMES,
)


# =============================================================================
# Test sanitize_string()
# =============================================================================


class TestSanitizeString:
    """Tests for string sanitization function."""

    def test_strips_whitespace(self):
        assert sanitize_string("  hello  ") == "hello"

    def test_returns_none_for_none(self):
        assert sanitize_string(None) is None

    def test_removes_control_characters(self):
        result = sanitize_string("hello\x00world\x07")
        assert "\x00" not in result
        assert "\x07" not in result
        assert "helloworld" == result

    def test_removes_xss_script_tags(self):
        result = sanitize_string('<script>alert("xss")</script>')
        assert "<script" not in result.lower()

    def test_removes_javascript_protocol(self):
        result = sanitize_string('javascript:alert("xss")')
        assert "javascript:" not in result.lower()

    def test_removes_onload_handler(self):
        result = sanitize_string('<img onerror="alert(1)">')
        # The XSS pattern matches on\w+\s*= so onerror= should be stripped
        assert "onerror=" not in result.lower()

    def test_truncates_to_max_length(self):
        long_string = "a" * 2000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    def test_preserves_normal_text(self):
        text = "This is a normal brand description with numbers 123."
        assert sanitize_string(text) == text

    def test_custom_max_length(self):
        result = sanitize_string("hello world", max_length=5)
        assert result == "hello"

    def test_empty_string(self):
        assert sanitize_string("") == ""

    def test_unicode_preserved(self):
        result = sanitize_string("Héllo wörld 你好")
        assert "Héllo" in result
        assert "你好" in result


# =============================================================================
# Test validate_url()
# =============================================================================


class TestValidateUrl:
    """Tests for URL validation function."""

    def test_valid_https_url(self):
        is_valid, error = validate_url("https://example.com")
        assert is_valid is True
        assert error == ""

    def test_valid_http_url(self):
        is_valid, error = validate_url("http://example.com")
        assert is_valid is True

    def test_rejects_no_scheme(self):
        is_valid, error = validate_url("example.com")
        assert is_valid is False
        assert "protocol" in error.lower()

    def test_rejects_file_scheme(self):
        is_valid, error = validate_url("file:///etc/passwd")
        assert is_valid is False
        assert "not allowed" in error.lower()

    def test_rejects_ftp_scheme(self):
        is_valid, error = validate_url("ftp://example.com")
        assert is_valid is False

    def test_rejects_javascript_scheme(self):
        is_valid, error = validate_url("javascript:alert(1)")
        assert is_valid is False

    def test_rejects_data_scheme(self):
        is_valid, error = validate_url("data:text/html,<h1>hi</h1>")
        assert is_valid is False

    def test_rejects_localhost(self):
        is_valid, error = validate_url("http://localhost")
        assert is_valid is False
        assert "not allowed" in error.lower()

    def test_rejects_127_0_0_1(self):
        is_valid, error = validate_url("http://127.0.0.1")
        assert is_valid is False

    def test_rejects_metadata_endpoint(self):
        is_valid, error = validate_url("http://169.254.169.254/latest/meta-data")
        assert is_valid is False

    def test_rejects_private_ip(self):
        is_valid, error = validate_url("http://192.168.1.1")
        assert is_valid is False
        assert "private" in error.lower()

    def test_rejects_loopback_ipv6_bracketed(self):
        is_valid, error = validate_url("http://[::1]")
        assert is_valid is False

    def test_bare_ipv6_loopback_passes_as_no_hostname(self):
        """Note: bare IPv6 like http://::1 parses hostname=None.
        urlparse requires brackets: http://[::1]. This is a known gap."""
        is_valid, _ = validate_url("http://::1")
        # Without brackets, urlparse yields hostname=None, so netloc exists
        # but hostname is None. The blocklist check on None doesn't block it.
        # This is documented as a hardening opportunity.
        assert is_valid is True  # documents current (imperfect) behavior

    def test_rejects_long_url(self):
        long_url = "https://example.com/" + "a" * 2048
        is_valid, error = validate_url(long_url)
        assert is_valid is False
        assert "length" in error.lower()

    def test_rejects_no_domain(self):
        is_valid, error = validate_url("https://")
        assert is_valid is False
        assert "domain" in error.lower()

    def test_accepts_url_with_path(self):
        is_valid, _ = validate_url("https://example.com/path/to/page")
        assert is_valid is True

    def test_accepts_url_with_query(self):
        is_valid, _ = validate_url("https://example.com?q=test")
        assert is_valid is True

    def test_rejects_gcp_metadata(self):
        is_valid, _ = validate_url("http://metadata.google.internal")
        assert is_valid is False


# =============================================================================
# Test validate_email()
# =============================================================================


class TestValidateEmail:
    """Tests for email validation function."""

    def test_valid_email(self):
        is_valid, _ = validate_email("user@example.com")
        assert is_valid is True

    def test_valid_email_with_subdomain(self):
        is_valid, _ = validate_email("user@mail.example.com")
        assert is_valid is True

    def test_rejects_missing_at(self):
        is_valid, error = validate_email("userexample.com")
        assert is_valid is False
        assert "format" in error.lower()

    def test_rejects_missing_domain(self):
        is_valid, error = validate_email("user@")
        assert is_valid is False

    def test_rejects_too_long(self):
        long_email = "a" * 250 + "@b.com"
        is_valid, error = validate_email(long_email)
        assert is_valid is False
        assert "length" in error.lower()

    def test_rejects_spaces(self):
        is_valid, _ = validate_email("user @example.com")
        assert is_valid is False

    def test_valid_plus_addressing(self):
        is_valid, _ = validate_email("user+tag@example.com")
        assert is_valid is True

    def test_valid_dots_in_local(self):
        is_valid, _ = validate_email("first.last@example.com")
        assert is_valid is True


# =============================================================================
# Test normalize_url()
# =============================================================================


class TestNormalizeUrl:
    """Tests for URL normalization function."""

    def test_adds_https_prefix(self):
        result = normalize_url("example.com")
        assert result == "https://example.com"

    def test_preserves_https(self):
        result = normalize_url("https://example.com")
        assert result == "https://example.com"

    def test_preserves_http(self):
        result = normalize_url("http://example.com")
        assert result == "http://example.com"

    def test_strips_whitespace(self):
        result = normalize_url("  https://example.com  ")
        assert result == "https://example.com"


# =============================================================================
# Test SSRF Protection Constants
# =============================================================================


class TestSSRFProtection:
    """Tests for SSRF protection blocklists."""

    def test_blocked_hosts_contains_localhost(self):
        assert "localhost" in BLOCKED_HOSTS

    def test_blocked_hosts_contains_metadata_ip(self):
        assert "169.254.169.254" in BLOCKED_HOSTS

    def test_blocked_hosts_contains_gcp_metadata(self):
        assert "metadata.google.internal" in BLOCKED_HOSTS

    def test_blocked_schemes_contains_file(self):
        assert "file" in BLOCKED_SCHEMES

    def test_blocked_schemes_contains_javascript(self):
        assert "javascript" in BLOCKED_SCHEMES
