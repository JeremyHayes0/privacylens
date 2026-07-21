import type { Finding } from "../api/types";
import { FindingTypePill } from "./Pills";

const CATEGORY_LABELS: Record<Finding["category"], string> = {
  https: "HTTPS / TLS",
  headers: "Security Headers",
  cookies: "Cookies",
  trackers: "Third-Party Trackers",
  privacy_policy: "Privacy Policy",
  tos: "Terms of Service",
  consent_banner: "Consent Banner",
};

export function categoryLabel(category: Finding["category"]): string {
  return CATEGORY_LABELS[category];
}

export function FindingCard({ finding }: { finding: Finding }) {
  const hasEvidence = Object.keys(finding.evidence).length > 0;

  return (
    <div className={`finding-card finding-card--${finding.finding_type}`}>
      <div className="finding-header">
        <span className="finding-title">{finding.title}</span>
        <FindingTypePill findingType={finding.finding_type} />
      </div>
      <p className="finding-description">{finding.description}</p>
      {hasEvidence && (
        <div className="finding-evidence mono">
          {Object.entries(finding.evidence).map(([key, value]) => (
            <div key={key}>
              {key}: {String(value)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
