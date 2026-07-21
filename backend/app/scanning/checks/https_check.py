from app.models.finding import FindingCategory, FindingSeverity, FindingType
from app.scanning.base_check import BaseCheck, FindingDraft
from app.scanning.context import ScanContext


class HttpsCheck(BaseCheck):
    """
    Reports on transport security: whether the final response was
    served over HTTPS, and (best-effort) how soon the TLS certificate
    expires.

    Purely observational, per the project's core design constraint --
    it never claims a site "is compliant" or "meets a legal
    requirement" for encryption, only what was technically observed.
    """

    category = FindingCategory.HTTPS

    def run(self, context: ScanContext) -> list[FindingDraft]:
        findings: list[FindingDraft] = [self._https_usage_finding(context)]

        expiry_finding = self._certificate_expiry_finding(context)
        if expiry_finding is not None:
            findings.append(expiry_finding)

        return findings

    def _https_usage_finding(self, context: ScanContext) -> FindingDraft:
        if context.used_https:
            return FindingDraft(
                category=self.category,
                finding_type=FindingType.DETECTED_CONFIGURATION,
                severity=FindingSeverity.INFO,
                title="Site served over HTTPS",
                description=(
                    f"The scanned page was served over HTTPS at {context.final_url}."
                ),
                evidence={"final_url": context.final_url, "redirected": context.redirected},
            )

        return FindingDraft(
            category=self.category,
            finding_type=FindingType.POTENTIAL_ISSUE,
            severity=FindingSeverity.HIGH,
            title="Site not served over HTTPS",
            description=(
                "The scanned page was served over plain HTTP, and no redirect to "
                "HTTPS was observed."
            ),
            evidence={"final_url": context.final_url},
        )

    def _certificate_expiry_finding(self, context: ScanContext) -> FindingDraft | None:
        if not context.used_https:
            return None

        if context.tls_certificate_expires_at is not None:
            return FindingDraft(
                category=self.category,
                finding_type=FindingType.DETECTED_CONFIGURATION,
                severity=FindingSeverity.INFO,
                title="TLS certificate expiry observed",
                description="The server's TLS certificate expiry date was read during the scan.",
                evidence={"expires_at": context.tls_certificate_expires_at.isoformat()},
            )

        return FindingDraft(
            category=self.category,
            finding_type=FindingType.OBSERVATION,
            severity=FindingSeverity.INFO,
            title="Could not determine TLS certificate expiry",
            description=(
                "The scan was unable to read the TLS certificate's expiry date. "
                "This does not necessarily indicate a problem -- it may reflect a "
                "transient network condition during the scan."
            ),
        )
