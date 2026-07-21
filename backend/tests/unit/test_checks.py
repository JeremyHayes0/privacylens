from datetime import datetime, timezone

from app.models.finding import FindingSeverity, FindingType
from app.scanning.checks.cookies_check import CookiesCheck
from app.scanning.checks.headers_check import SECURITY_HEADERS, SecurityHeadersCheck
from app.scanning.checks.https_check import HttpsCheck
from app.scanning.checks.policy_links_check import PrivacyPolicyCheck, TermsOfServiceCheck
from app.scanning.context import CookieObservation, LinkObservation, ScanContext


def _context(**overrides) -> ScanContext:
    defaults: dict = dict(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        headers={},
        used_https=True,
        tls_certificate_expires_at=None,
        redirected=False,
        cookies=[],
        links=[],
    )
    defaults.update(overrides)
    return ScanContext(**defaults)


class TestHttpsCheck:
    def test_flags_plain_http_as_potential_issue(self):
        context = _context(used_https=False, final_url="http://example.com")
        findings = HttpsCheck().run(context)

        assert any(
            f.finding_type == FindingType.POTENTIAL_ISSUE and f.severity == FindingSeverity.HIGH
            for f in findings
        )

    def test_reports_detected_configuration_for_https(self):
        context = _context(used_https=True)
        findings = HttpsCheck().run(context)

        assert any(f.finding_type == FindingType.DETECTED_CONFIGURATION for f in findings)

    def test_reports_certificate_expiry_when_available(self):
        expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
        context = _context(used_https=True, tls_certificate_expires_at=expiry)
        findings = HttpsCheck().run(context)

        expiry_findings = [f for f in findings if "expiry" in f.title.lower()]
        assert len(expiry_findings) == 1
        assert expiry_findings[0].finding_type == FindingType.DETECTED_CONFIGURATION
        assert expiry_findings[0].evidence["expires_at"] == expiry.isoformat()

    def test_reports_observation_when_expiry_unknown(self):
        context = _context(used_https=True, tls_certificate_expires_at=None)
        findings = HttpsCheck().run(context)

        expiry_findings = [f for f in findings if "expiry" in f.title.lower()]
        assert len(expiry_findings) == 1
        assert expiry_findings[0].finding_type == FindingType.OBSERVATION

    def test_no_certificate_expiry_finding_over_plain_http(self):
        """A plain-HTTP site has no TLS certificate to report on at all."""
        context = _context(used_https=False, final_url="http://example.com")
        findings = HttpsCheck().run(context)

        assert not any("expiry" in f.title.lower() for f in findings)


class TestSecurityHeadersCheck:
    def test_flags_each_missing_header_as_potential_issue(self):
        context = _context(headers={})
        findings = SecurityHeadersCheck().run(context)

        assert len(findings) == len(SECURITY_HEADERS)
        assert all(f.finding_type == FindingType.POTENTIAL_ISSUE for f in findings)

    def test_detects_a_present_header_with_its_value(self):
        context = _context(headers={"content-security-policy": "default-src 'self'"})
        findings = SecurityHeadersCheck().run(context)

        csp_findings = [f for f in findings if f.evidence.get("header") == "content-security-policy"]
        assert len(csp_findings) == 1
        assert csp_findings[0].finding_type == FindingType.DETECTED_CONFIGURATION
        assert csp_findings[0].evidence["value"] == "default-src 'self'"

    def test_header_lookup_is_case_insensitive_via_context(self):
        """
        The fetcher lowercases header keys before building ScanContext
        (see app/scanning/fetcher.py) -- this test documents that the
        check relies on that normalization rather than doing its own.
        """
        context = _context(headers={"x-frame-options": "DENY"})
        findings = SecurityHeadersCheck().run(context)

        xfo_findings = [f for f in findings if f.evidence.get("header") == "x-frame-options"]
        assert len(xfo_findings) == 1
        assert xfo_findings[0].finding_type == FindingType.DETECTED_CONFIGURATION


class TestCookiesCheck:
    def test_no_cookies_produces_a_single_observation(self):
        context = _context(cookies=[])
        findings = CookiesCheck().run(context)

        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.OBSERVATION

    def test_cookie_missing_secure_flag_is_a_potential_issue(self):
        cookie = CookieObservation(name="session", domain=None, secure=False, http_only=True, same_site="Lax")
        context = _context(cookies=[cookie])
        findings = CookiesCheck().run(context)

        secure_findings = [f for f in findings if f.evidence.get("secure") is False]
        assert len(secure_findings) == 1
        assert secure_findings[0].finding_type == FindingType.POTENTIAL_ISSUE
        assert secure_findings[0].severity == FindingSeverity.MEDIUM

    def test_cookie_missing_httponly_flag_is_an_observation(self):
        cookie = CookieObservation(name="tracker", domain=None, secure=True, http_only=False, same_site=None)
        context = _context(cookies=[cookie])
        findings = CookiesCheck().run(context)

        httponly_findings = [f for f in findings if f.evidence.get("http_only") is False]
        assert len(httponly_findings) == 1
        assert httponly_findings[0].finding_type == FindingType.OBSERVATION

    def test_fully_flagged_cookie_produces_no_potential_issue(self):
        cookie = CookieObservation(name="session", domain=None, secure=True, http_only=True, same_site="Strict")
        context = _context(cookies=[cookie])
        findings = CookiesCheck().run(context)

        assert not any(f.finding_type == FindingType.POTENTIAL_ISSUE for f in findings)
        # Still reports the SameSite value as a detected configuration.
        same_site_findings = [f for f in findings if "SameSite" in f.title]
        assert len(same_site_findings) == 1
        assert same_site_findings[0].evidence["same_site"] == "Strict"

    def test_multiple_cookies_are_each_evaluated_independently(self):
        cookies = [
            CookieObservation(name="a", domain=None, secure=False, http_only=False, same_site=None),
            CookieObservation(name="b", domain=None, secure=True, http_only=True, same_site="Lax"),
        ]
        context = _context(cookies=cookies)
        findings = CookiesCheck().run(context)

        names_with_issues = {f.evidence.get("cookie") for f in findings if f.finding_type == FindingType.POTENTIAL_ISSUE}
        assert names_with_issues == {"a"}


class TestPrivacyPolicyCheck:
    def test_no_matching_link_is_a_potential_issue(self):
        context = _context(links=[LinkObservation(href="/about", text="About us")])
        findings = PrivacyPolicyCheck().run(context)

        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.POTENTIAL_ISSUE

    def test_matches_link_by_visible_text(self):
        context = _context(links=[LinkObservation(href="/legal/pp", text="Privacy Policy")])
        findings = PrivacyPolicyCheck().run(context)

        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.DETECTED_CONFIGURATION
        assert findings[0].evidence["href"] == "/legal/pp"

    def test_matches_link_by_href_when_text_is_generic(self):
        context = _context(links=[LinkObservation(href="/privacy-policy", text="Learn more")])
        findings = PrivacyPolicyCheck().run(context)

        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.DETECTED_CONFIGURATION


class TestTermsOfServiceCheck:
    def test_no_matching_link_is_an_observation(self):
        context = _context(links=[])
        findings = TermsOfServiceCheck().run(context)

        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.OBSERVATION

    def test_matches_terms_of_use_link(self):
        context = _context(links=[LinkObservation(href="/terms-of-use", text="Terms of Use")])
        findings = TermsOfServiceCheck().run(context)

        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.DETECTED_CONFIGURATION
