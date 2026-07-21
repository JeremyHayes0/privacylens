import socket
import ssl
from datetime import datetime, timezone

import httpx

from app.scanning.context import CookieObservation, ScanContext
from app.scanning.cookie_utils import parse_set_cookie_header
from app.scanning.html_utils import extract_links

FETCH_TIMEOUT_SECONDS = 10.0

# Identifying the scanner in its own User-Agent is a small but
# deliberate transparency choice: a site operator inspecting their
# access logs should be able to tell PrivacyLens apart from a generic
# bot, rather than have it masquerade as a regular browser.
USER_AGENT = "PrivacyLensBot/0.1 (compliance-scanner; not a browser)"


class FetchError(Exception):
    """
    Raised when the target could not be reached at all -- DNS failure,
    connection refused, timeout, TLS handshake failure. This is
    distinct from a check finding "no CSP header": FetchError means
    the orchestrator never got a ScanContext to run checks against at
    all, and the scan should be marked FAILED rather than COMPLETED.
    """


def fetch_target(url: str) -> ScanContext:
    """
    Perform the one network request a scan needs and package the
    result into a ScanContext. This is the ONLY function in the
    scanning engine that talks to the public internet -- every
    BaseCheck subclass operates purely on the ScanContext this returns.
    """
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        raise FetchError(f"Could not reach {url}: {exc}") from exc

    final_url = str(response.url)
    used_https = response.url.scheme == "https"

    tls_expires_at = _get_tls_certificate_expiry(response.url.host) if used_https else None

    return ScanContext(
        requested_url=url,
        final_url=final_url,
        status_code=response.status_code,
        headers={key.lower(): value for key, value in response.headers.items()},
        used_https=used_https,
        tls_certificate_expires_at=tls_expires_at,
        redirected=final_url != url,
        cookies=_parse_cookies(response.headers),
        links=extract_links(response.text),
    )


def _parse_cookies(headers: httpx.Headers) -> list[CookieObservation]:
    """
    A response can set multiple cookies via multiple Set-Cookie
    headers -- httpx.Headers.get_list handles that multi-value case
    (a plain headers.get("set-cookie") would only ever return one).
    Any single header this scanner can't parse is skipped rather than
    failing the whole scan; one malformed cookie shouldn't prevent
    reporting on every other one.
    """
    cookies: list[CookieObservation] = []
    for raw_header in headers.get_list("set-cookie"):
        try:
            cookies.append(parse_set_cookie_header(raw_header))
        except ValueError:
            continue
    return cookies


def _get_tls_certificate_expiry(host: str) -> datetime | None:
    """
    Best-effort: open a direct TLS connection to read the server
    certificate's expiry date.

    Any failure here (a flaky second connection, a host that only
    accepts one connection per client, an unusual certificate format)
    returns None rather than propagating -- reading the certificate
    expiry is a nice-to-have enrichment of the HTTPS check, not a
    reason to fail an otherwise-successful scan. The HTTPS check itself
    is responsible for reporting "expiry unknown" as an Observation
    when this returns None (see checks/https_check.py).
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=FETCH_TIMEOUT_SECONDS) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert()
        not_after = cert.get("notAfter") if cert else None
        if not_after is None:
            return None
        return datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except (OSError, ssl.SSLError, ValueError):
        return None
