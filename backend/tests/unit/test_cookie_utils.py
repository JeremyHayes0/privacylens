import pytest

from app.scanning.cookie_utils import parse_set_cookie_header


def test_parses_name_from_simple_cookie():
    cookie = parse_set_cookie_header("sessionid=abc123")
    assert cookie.name == "sessionid"
    assert cookie.secure is False
    assert cookie.http_only is False
    assert cookie.same_site is None
    assert cookie.domain is None


def test_parses_secure_and_httponly_flags():
    cookie = parse_set_cookie_header("sessionid=abc123; Path=/; HttpOnly; Secure; SameSite=Lax")
    assert cookie.name == "sessionid"
    assert cookie.secure is True
    assert cookie.http_only is True
    assert cookie.same_site == "Lax"


def test_parses_domain_attribute():
    cookie = parse_set_cookie_header("tracker=xyz; Domain=.example.com; Path=/")
    assert cookie.domain == ".example.com"


def test_missing_flags_default_to_false_or_none():
    cookie = parse_set_cookie_header("basic=1; Path=/; Max-Age=3600")
    assert cookie.secure is False
    assert cookie.http_only is False
    assert cookie.same_site is None


def test_attribute_matching_is_case_insensitive():
    """Set-Cookie attribute names are conventionally capitalized but not required to be."""
    cookie = parse_set_cookie_header("a=1; secure; httponly; samesite=strict")
    assert cookie.secure is True
    assert cookie.http_only is True
    assert cookie.same_site == "strict"


def test_empty_header_raises_value_error():
    with pytest.raises(ValueError):
        parse_set_cookie_header("")
