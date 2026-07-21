"""
The list of checks the orchestrator runs for every scan.

Adding a new check category later (trackers/consent-banner detection
-- see the project blueprint) is a two-step change: write one
BaseCheck subclass under app/scanning/checks/, then add it to this
list. The orchestrator (app/services/scan_orchestrator.py) never needs
to change.
"""

from app.scanning.base_check import BaseCheck
from app.scanning.checks.cookies_check import CookiesCheck
from app.scanning.checks.headers_check import SecurityHeadersCheck
from app.scanning.checks.https_check import HttpsCheck
from app.scanning.checks.policy_links_check import PrivacyPolicyCheck, TermsOfServiceCheck

REGISTERED_CHECKS: list[BaseCheck] = [
    HttpsCheck(),
    SecurityHeadersCheck(),
    CookiesCheck(),
    PrivacyPolicyCheck(),
    TermsOfServiceCheck(),
]
