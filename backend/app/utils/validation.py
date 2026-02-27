import re
import ipaddress
from urllib.parse import urlparse
from typing import Optional


BLOCKED_HOSTS = frozenset(
    [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",  # nosec B104 - This is a blocklist, not a binding address
        "::1",
        "metadata.google.internal",
        "169.254.169.254",
    ]
)

BLOCKED_SCHEMES = frozenset(["file", "ftp", "data", "javascript"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

XSS_PATTERN = re.compile(r"<[^>]*script|javascript:|on\w+\s*=", re.IGNORECASE)


def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    value = XSS_PATTERN.sub("", value)
    return value[:max_length] if len(value) > max_length else value


def validate_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if not parsed.scheme:
        return False, "URL must include protocol (http:// or https://)"

    if parsed.scheme.lower() in BLOCKED_SCHEMES:
        return False, f"URL scheme '{parsed.scheme}' is not allowed"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are allowed"

    if not parsed.netloc:
        return False, "URL must include a domain"

    hostname = parsed.hostname or ""

    # Also check the raw netloc for IPv6 patterns that urlparse misses
    netloc = parsed.netloc or ""
    if hostname.lower() in BLOCKED_HOSTS or netloc.lower() in BLOCKED_HOSTS:
        return False, "This host is not allowed"

    # Check both hostname and raw netloc for IP-based SSRF
    for addr_str in (hostname, netloc.split(":")[0].strip("[]")):
        if not addr_str:
            continue
        try:
            ip = ipaddress.ip_address(addr_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False, "Private IP addresses are not allowed"
        except ValueError:
            pass

    if len(url) > 2048:
        return False, "URL exceeds maximum length (2048 characters)"

    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    if len(email) > 254:
        return False, "Email exceeds maximum length"

    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"

    return True, ""


def normalize_url(url: str) -> str:
    url = url.strip()
    # Reject dangerous schemes before normalization
    lower = url.lower()
    for scheme in BLOCKED_SCHEMES:
        if lower.startswith(f"{scheme}:"):
            raise ValueError(f"URL scheme '{scheme}' is not allowed")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url
