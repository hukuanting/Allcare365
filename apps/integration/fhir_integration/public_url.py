"""Helpers for deriving a single canonical public base URL for SMART/FHIR endpoints."""

from urllib.parse import urlsplit, urlunsplit

from django.conf import settings


def _strip_oauth_suffix(url: str) -> str:
    normalized = (url or "").rstrip("/")
    if normalized.endswith("/o"):
        return normalized[:-2]
    return normalized


def _force_scheme(url: str, scheme: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url
    return urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))


def _has_absolute_origin(url: str) -> bool:
    parts = urlsplit(url or "")
    return bool(parts.scheme and parts.netloc)


def _origin_from_uri(uri: str) -> str:
    parts = urlsplit(uri or "")
    if not parts.scheme or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def get_public_base_url(request=None) -> str:
    configured_public = getattr(settings, "PUBLIC_BASE_URL", "").strip()
    if configured_public:
        base_url = configured_public.rstrip("/")
    else:
        oidc_iss = getattr(settings, "OAUTH2_PROVIDER", {}).get("OIDC_ISS_ENDPOINT", "")
        if _has_absolute_origin(oidc_iss):
            base_url = _strip_oauth_suffix(oidc_iss)
        elif request is not None and hasattr(request, "build_absolute_uri"):
            base_url = request.build_absolute_uri("/").rstrip("/")
        elif request is not None:
            base_url = _origin_from_uri(getattr(request, "uri", ""))
        else:
            base_url = "http://localhost:8000"

    if request is None:
        return base_url

    meta = getattr(request, "META", {}) or {}
    forwarded_proto = meta.get("HTTP_X_FORWARDED_PROTO", "").split(",")[0].strip().lower()
    request_is_secure = request.is_secure() if hasattr(request, "is_secure") else False
    
    # Only force HTTPS if we are sure it's being used via a proxy/tunnel
    # or if the request itself is secure.
    if forwarded_proto == "https" or request_is_secure:
        base_url = _force_scheme(base_url, "https")
    elif "localhost" in base_url or "127.0.0.1" in base_url:
        # Explicitly keep http for localhost unless secure
        base_url = _force_scheme(base_url, "http")

    return base_url


def build_public_url(path: str, request=None) -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{get_public_base_url(request)}{normalized_path}"


def get_token_endpoint_candidates(request) -> list[str]:
    base_candidates = [
        build_public_url("/o/token/", request),
        build_public_url("/o/token", request),
    ]

    request_uri = getattr(request, "uri", None)
    if request_uri:
        base_candidates.extend([request_uri, request_uri.rstrip("/")])

    seen = set()
    ordered = []
    for item in base_candidates:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
