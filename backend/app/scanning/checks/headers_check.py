from app.models.finding import FindingCategory, FindingSeverity, FindingType
from app.scanning.base_check import BaseCheck, FindingDraft
from app.scanning.context import ScanContext

# header name (lowercase) -> (severity if absent, human-readable display name).
#
# This is a short, well-known set for the MVP -- not an exhaustive
# header audit (e.g. it doesn't yet parse *whether* a CSP value is
# meaningfully restrictive, just whether the header is present at
# all). Extending the check is adding one entry here; the run() method
# below never needs to change for a new header.
SECURITY_HEADERS: dict[str, tuple[FindingSeverity, str]] = {
    "content-security-policy": (FindingSeverity.MEDIUM, "Content-Security-Policy"),
    "strict-transport-security": (FindingSeverity.MEDIUM, "Strict-Transport-Security (HSTS)"),
    "x-content-type-options": (FindingSeverity.LOW, "X-Content-Type-Options"),
    "x-frame-options": (FindingSeverity.LOW, "X-Frame-Options"),
    "referrer-policy": (FindingSeverity.INFO, "Referrer-Policy"),
}


class SecurityHeadersCheck(BaseCheck):
    """
    Reports whether each header in SECURITY_HEADERS was present on the
    response. Presence-only for this milestone -- assessing whether a
    present header's *value* is well-configured (e.g. a CSP that
    actually restricts inline scripts) is a natural, separate
    follow-on check once this one exists.
    """

    category = FindingCategory.HEADERS

    def run(self, context: ScanContext) -> list[FindingDraft]:
        return [
            self._finding_for_header(context, header_name, severity, display_name)
            for header_name, (severity, display_name) in SECURITY_HEADERS.items()
        ]

    def _finding_for_header(
        self,
        context: ScanContext,
        header_name: str,
        severity_if_absent: FindingSeverity,
        display_name: str,
    ) -> FindingDraft:
        value = context.headers.get(header_name)

        if value is not None:
            return FindingDraft(
                category=self.category,
                finding_type=FindingType.DETECTED_CONFIGURATION,
                severity=FindingSeverity.INFO,
                title=f"{display_name} header present",
                description=f"The response included a {display_name} header.",
                evidence={"header": header_name, "value": value},
            )

        return FindingDraft(
            category=self.category,
            finding_type=FindingType.POTENTIAL_ISSUE,
            severity=severity_if_absent,
            title=f"{display_name} header not detected",
            description=(
                f"No {display_name} header was observed in the response. Its "
                "absence doesn't necessarily indicate a problem for every kind of "
                "site, but it is a commonly recommended hardening measure worth "
                "reviewing."
            ),
            evidence={"header": header_name},
        )
