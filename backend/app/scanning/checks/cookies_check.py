from app.models.finding import FindingCategory, FindingSeverity, FindingType
from app.scanning.base_check import BaseCheck, FindingDraft
from app.scanning.context import CookieObservation, ScanContext


class CookiesCheck(BaseCheck):
    """
    Reports on cookies set via the initial response's Set-Cookie
    headers: whether each is missing the Secure and/or HttpOnly flag,
    and what SameSite value (if any) it declares.

    Only covers cookies visible on this one HTTP fetch. Cookies set
    later by client-side JavaScript (common for analytics/advertising
    scripts) aren't observable this way -- that gap is exactly what a
    future rendered-page fetch (e.g. via Playwright) and a
    TrackersCheck would close, per the project blueprint.
    """

    category = FindingCategory.COOKIES

    def run(self, context: ScanContext) -> list[FindingDraft]:
        if not context.cookies:
            return [
                FindingDraft(
                    category=self.category,
                    finding_type=FindingType.OBSERVATION,
                    severity=FindingSeverity.INFO,
                    title="No cookies observed on initial response",
                    description=(
                        "No Set-Cookie headers were present on the initial page "
                        "load. Cookies set later via JavaScript are not covered "
                        "by this check."
                    ),
                )
            ]

        findings: list[FindingDraft] = []
        for cookie in context.cookies:
            findings.extend(self._findings_for_cookie(cookie))
        return findings

    def _findings_for_cookie(self, cookie: CookieObservation) -> list[FindingDraft]:
        findings: list[FindingDraft] = []

        if not cookie.secure:
            findings.append(
                FindingDraft(
                    category=self.category,
                    finding_type=FindingType.POTENTIAL_ISSUE,
                    severity=FindingSeverity.MEDIUM,
                    title=f"Cookie '{cookie.name}' set without Secure flag",
                    description=(
                        f"The cookie '{cookie.name}' was set without the Secure "
                        "flag, meaning it could be transmitted over an "
                        "unencrypted connection if one were ever made."
                    ),
                    evidence={"cookie": cookie.name, "secure": False},
                )
            )

        if not cookie.http_only:
            findings.append(
                FindingDraft(
                    category=self.category,
                    finding_type=FindingType.OBSERVATION,
                    severity=FindingSeverity.LOW,
                    title=f"Cookie '{cookie.name}' set without HttpOnly flag",
                    description=(
                        f"The cookie '{cookie.name}' was set without the HttpOnly "
                        "flag, meaning client-side JavaScript can read it. This is "
                        "sometimes intentional (e.g. a cookie a script is meant to "
                        "read) and is not inherently a problem for every cookie."
                    ),
                    evidence={"cookie": cookie.name, "http_only": False},
                )
            )

        findings.append(
            FindingDraft(
                category=self.category,
                finding_type=FindingType.DETECTED_CONFIGURATION,
                severity=FindingSeverity.INFO,
                title=f"Cookie '{cookie.name}' SameSite attribute",
                description=(
                    f"The cookie '{cookie.name}' declared "
                    f"SameSite={cookie.same_site or 'not set'}."
                ),
                evidence={"cookie": cookie.name, "same_site": cookie.same_site},
            )
        )

        return findings
