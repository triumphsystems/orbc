import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("core.utils.security")

BLOCKED_HOSTNAMES: set[str] = {
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def sanitize_css_color(color_val: str | None, default: str = "#00F2FE") -> str:
    """Validates and returns safe hex color string, preventing style tag escapes and CSS injection."""
    if not color_val or not isinstance(color_val, str):
        return default
    cleaned = color_val.strip()
    if HEX_COLOR_PATTERN.match(cleaned):
        return cleaned
    return default


def is_ip_prohibited(ip_str: str, allow_private: bool = False) -> bool:
    """Checks whether an IP address is loopback, link-local, multicast, or private."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.is_loopback:
        return True
    if ip.is_link_local:
        return True
    if ip.is_multicast:
        return True
    if ip.is_reserved:
        return True
    if ip.is_unspecified:
        return True

    # Cloud metadata link-local address (169.254.169.254)
    if str(ip) == "169.254.169.254":
        return True

    if not allow_private and ip.is_private:
        return True

    return False


def validate_url_target(url: str, allow_private: bool = False) -> tuple[bool, str | None]:
    """
    Validates that a URL is safe to request:
    - Scheme must be http or https.
    - Hostname must not be a cloud metadata endpoint.
    - Resolved IP must not be loopback, link-local (169.254.169.254), or unauthorized private.
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL syntax: {e}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL hostname is missing."

    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Access to internal metadata service '{hostname}' is blocked."

    # Check if hostname is a literal IP address
    try:
        ip = ipaddress.ip_address(hostname_lower)
        if is_ip_prohibited(str(ip), allow_private=allow_private):
            return False, f"Access to restricted IP address '{hostname_lower}' is blocked."
        return True, None
    except ValueError:
        # Not a literal IP address; proceed to DNS resolution
        pass

    # Resolve domain to IP and check resolved addresses against SSRF
    try:
        addr_info = socket.getaddrinfo(hostname_lower, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            if is_ip_prohibited(ip_str, allow_private=allow_private):
                return False, f"Resolved IP '{ip_str}' for host '{hostname}' is restricted."
    except socket.gaierror:
        # If DNS resolution fails, allow HTTP client to attempt or handle network failure
        pass
    except Exception as e:
        logger.warning("DNS resolution check failed for %s: %s", hostname, e)

    return True, None


async def safe_redirect_hook(response: httpx.Response, allow_private: bool = False) -> None:
    """HTTPX response event hook that validates redirect targets against SSRF."""
    if response.is_redirect and "location" in response.headers:
        redirect_url = str(response.url.join(response.headers["location"]))
        valid, reason = validate_url_target(redirect_url, allow_private=allow_private)
        if not valid:
            raise ValueError(f"SSRF protection blocked redirect to: {redirect_url} ({reason})")


def sign_s3_request(
    method: str,
    endpoint_url: str | None,
    bucket: str,
    key: str,
    body: bytes,
    content_type: str,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
) -> tuple[str, dict[str, str]]:
    """Computes S3 Signature Version 4 authentication headers for REST API calls."""
    from datetime import datetime, timezone
    import hashlib
    import hmac
    import urllib.parse

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    if endpoint_url:
        parsed = urllib.parse.urlparse(endpoint_url)
        host = parsed.netloc
        canonical_uri = f"/{bucket}/{key}"
        target_url = f"{endpoint_url.rstrip('/')}/{bucket}/{key}"
    else:
        host = f"{bucket}.s3.{region}.amazonaws.com"
        canonical_uri = f"/{key}"
        target_url = f"https://{host}/{key}"

    payload_hash = hashlib.sha256(body).hexdigest()

    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"

    canonical_request = (
        f"{method.upper()}\n"
        f"{canonical_uri}\n"
        f"\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = (
        f"{algorithm}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    k_date = hmac.new(("AWS4" + secret_key).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, b"s3", hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    headers = {
        "Content-Type": content_type,
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": authorization_header,
    }

    return target_url, headers


def generate_s3_presigned_url(
    endpoint_url: str | None,
    bucket: str,
    key: str,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    expires_seconds: int = 86400,
) -> str:
    """Generates an S3 SigV4 presigned GET URL for secure object downloads."""
    from datetime import datetime, timezone
    import hashlib
    import hmac
    import urllib.parse

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    if endpoint_url:
        parsed = urllib.parse.urlparse(endpoint_url)
        host = parsed.netloc
        canonical_uri = f"/{bucket}/{key}"
        base_url = f"{endpoint_url.rstrip('/')}/{bucket}/{key}"
    else:
        host = f"{bucket}.s3.{region}.amazonaws.com"
        canonical_uri = f"/{key}"
        base_url = f"https://{host}/{key}"

    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    query_params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{access_key}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_seconds),
        "X-Amz-SignedHeaders": "host",
    }
    canonical_query = urllib.parse.urlencode(sorted(query_params.items()))

    canonical_headers = f"host:{host}\n"
    signed_headers = "host"
    payload_hash = "UNSIGNED-PAYLOAD"

    canonical_request = (
        f"GET\n"
        f"{canonical_uri}\n"
        f"{canonical_query}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    string_to_sign = (
        f"AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    k_date = hmac.new(("AWS4" + secret_key).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, b"s3", hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"{base_url}?{canonical_query}&X-Amz-Signature={signature}"
