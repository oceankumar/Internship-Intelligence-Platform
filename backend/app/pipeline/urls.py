import ipaddress
from urllib.parse import urlsplit


def safe_public_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not host or "." not in host:
            return False
        if host.endswith((".local", ".localhost", ".internal")) or host == "localhost":
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except ValueError:
        return False
