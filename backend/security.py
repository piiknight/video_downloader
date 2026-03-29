"""URL validation and API key authentication."""

import hmac
from urllib.parse import urlparse

ALLOWED_DOMAINS = [
    "tiktok.com",
    "douyin.com",
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "fb.watch",
    "pinterest.com",
    "pin.it",
    "xiaohongshu.com",
    "xhslink.com",
]


def validate_url(url: str) -> bool:
    """Validate URL is HTTPS and from an allowed domain."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    hostname = parsed.hostname or ""
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in ALLOWED_DOMAINS
    )


def verify_api_key(provided: str, expected: str) -> bool:
    """Constant-time API key comparison."""
    return hmac.compare_digest(provided, expected)
