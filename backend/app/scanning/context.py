from dataclasses import dataclass
from datetime import datetime


@dataclass
class CookieObservation:
    """One cookie set via a Set-Cookie header on the initial response."""

    name: str
    domain: str | None
    secure: bool
    http_only: bool
    same_site: str | None


@dataclass
class LinkObservation:
    """One <a> tag found in the page body -- its href and visible text."""

    href: str
    text: str


@dataclass
class ScanContext:
    """
    Everything a check might need to read, gathered once by the
    fetcher (app/scanning/fetcher.py) so that no individual check ever
    makes its own network request or re-parses the page body. See
    BaseCheck's docstring (app/scanning/base_check.py) for why that
    separation is the whole point of this abstraction.
    """

    requested_url: str
    """The URL as stored on the Target -- before any redirect."""

    final_url: str
    """The URL actually served, after following any redirects."""

    status_code: int

    headers: dict[str, str]
    """Response headers with lowercased keys, so checks never have to
    worry about case sensitivity when looking one up."""

    used_https: bool
    """Whether `final_url` uses the https:// scheme."""

    tls_certificate_expires_at: datetime | None
    """
    Best-effort; None if the certificate's expiry couldn't be
    determined (e.g. the site isn't served over HTTPS, or a transient
    connection issue prevented reading it). A check should treat None
    as "unknown," never as "no certificate" or "expired."
    """

    redirected: bool
    """Whether final_url differs from requested_url at all (scheme, host, or path)."""

    cookies: list[CookieObservation]
    """
    Cookies set via Set-Cookie headers on this one response only.
    Cookies set later via client-side JavaScript (common for
    analytics/ad scripts) are out of scope for a plain HTTP fetch and
    would need a rendered-page fetch (e.g. via Playwright) to observe
    -- see the project blueprint's TrackersCheck for that follow-on
    work.
    """

    links: list[LinkObservation]
    """Every <a> tag found in the page body, extracted once so no
    check needs to re-parse HTML for its own purposes."""
