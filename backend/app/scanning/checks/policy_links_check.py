from app.models.finding import FindingCategory, FindingSeverity, FindingType
from app.scanning.base_check import BaseCheck, FindingDraft
from app.scanning.context import LinkObservation, ScanContext

PRIVACY_POLICY_KEYWORDS = ("privacy policy", "privacy notice", "/privacy")
TERMS_OF_SERVICE_KEYWORDS = (
    "terms of service",
    "terms of use",
    "terms and conditions",
    "/terms",
    "/tos",
)


def _find_matching_link(
    links: list[LinkObservation], keywords: tuple[str, ...]
) -> LinkObservation | None:
    """
    Shared heuristic for both checks below: a link "matches" if any
    keyword appears in its visible text or its href, case-insensitive.
    Checking both text and href catches the common cases of a
    plainly-labeled link ("Privacy Policy") and an icon-only or
    generically-labeled one ("Learn more" pointing at /privacy-policy).
    """
    for link in links:
        haystack = f"{link.text} {link.href}".lower()
        if any(keyword in haystack for keyword in keywords):
            return link
    return None


class PrivacyPolicyCheck(BaseCheck):
    """
    Heuristic detection only: looks for a link whose visible text or
    href resembles a privacy policy.

    A missing match does NOT mean a privacy policy doesn't exist -- it
    may be linked from a different page than the one scanned, embedded
    behind a cookie-consent tool, or simply worded in a way this
    heuristic doesn't catch. This check reports what it found on this
    one page, not a conclusion about whether disclosure requirements
    are met.
    """

    category = FindingCategory.PRIVACY_POLICY

    def run(self, context: ScanContext) -> list[FindingDraft]:
        match = _find_matching_link(context.links, PRIVACY_POLICY_KEYWORDS)

        if match is not None:
            return [
                FindingDraft(
                    category=self.category,
                    finding_type=FindingType.DETECTED_CONFIGURATION,
                    severity=FindingSeverity.INFO,
                    title="Link resembling a privacy policy found",
                    description=(
                        f"A link with text '{match.text or '(no visible text)'}' "
                        f"pointing to '{match.href}' was found on the scanned page."
                    ),
                    evidence={"href": match.href, "text": match.text},
                )
            ]

        return [
            FindingDraft(
                category=self.category,
                finding_type=FindingType.POTENTIAL_ISSUE,
                severity=FindingSeverity.MEDIUM,
                title="No link resembling a privacy policy found",
                description=(
                    "No link with text or a URL resembling a privacy policy was "
                    "found on the scanned page. This is a heuristic based on "
                    "common link text and URL patterns -- it does not confirm a "
                    "privacy policy is absent from the site."
                ),
            )
        ]


class TermsOfServiceCheck(BaseCheck):
    """Same heuristic approach as PrivacyPolicyCheck, for Terms of Service / Terms of Use links."""

    category = FindingCategory.TERMS_OF_SERVICE

    def run(self, context: ScanContext) -> list[FindingDraft]:
        match = _find_matching_link(context.links, TERMS_OF_SERVICE_KEYWORDS)

        if match is not None:
            return [
                FindingDraft(
                    category=self.category,
                    finding_type=FindingType.DETECTED_CONFIGURATION,
                    severity=FindingSeverity.INFO,
                    title="Link resembling Terms of Service found",
                    description=(
                        f"A link with text '{match.text or '(no visible text)'}' "
                        f"pointing to '{match.href}' was found on the scanned page."
                    ),
                    evidence={"href": match.href, "text": match.text},
                )
            ]

        return [
            FindingDraft(
                category=self.category,
                finding_type=FindingType.OBSERVATION,
                severity=FindingSeverity.LOW,
                title="No link resembling Terms of Service found",
                description=(
                    "No link with text or a URL resembling Terms of Service/Use "
                    "was found on the scanned page. This is a heuristic based on "
                    "common link text and URL patterns -- it does not confirm "
                    "terms are absent from the site."
                ),
            )
        ]
