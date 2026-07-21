from app.scanning.context import CookieObservation


def parse_set_cookie_header(raw_header: str) -> CookieObservation:
    """
    Parse a single raw Set-Cookie header value into a CookieObservation.

    Deliberately hand-rolled rather than using http.cookiejar/
    http.cookies: Python's stdlib cookie jars are built to *manage*
    cookies for making further requests, and normalize away exactly
    the attributes (Secure, HttpOnly, SameSite) this check exists to
    read. A simple split-on-semicolon parser keeps every attribute
    visible.

    This function is intentionally pure -- no I/O, no ScanContext
    construction -- so it's unit-testable with hand-written header
    strings (see tests/unit/test_cookie_utils.py) independent of the
    fetcher that calls it.
    """
    parts = [segment.strip() for segment in raw_header.split(";") if segment.strip()]
    if not parts:
        raise ValueError("Empty Set-Cookie header.")

    name = parts[0].split("=", 1)[0].strip()

    attributes: dict[str, str | bool] = {}
    for part in parts[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            attributes[key.strip().lower()] = value.strip()
        else:
            attributes[part.strip().lower()] = True

    same_site = attributes.get("samesite")
    domain = attributes.get("domain")

    return CookieObservation(
        name=name,
        domain=domain if isinstance(domain, str) else None,
        secure=bool(attributes.get("secure", False)),
        http_only=bool(attributes.get("httponly", False)),
        same_site=same_site if isinstance(same_site, str) else None,
    )
