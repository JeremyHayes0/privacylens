import type { FindingType, ScanStatus } from "../api/types";

const FINDING_TYPE_LABELS: Record<FindingType, string> = {
  potential_issue: "Potential Issue",
  observation: "Observation",
  detected_configuration: "Detected Configuration",
  recommendation: "Recommendation",
};

const SCAN_STATUS_LABELS: Record<ScanStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

export function FindingTypePill({ findingType }: { findingType: FindingType }) {
  return (
    <span className={`pill pill--${findingType}`}>
      <span className="pill-tick" />
      {FINDING_TYPE_LABELS[findingType]}
    </span>
  );
}

export function ScanStatusPill({ status }: { status: ScanStatus }) {
  return (
    <span className={`pill pill--${status}`}>
      <span className="pill-tick" />
      {SCAN_STATUS_LABELS[status]}
    </span>
  );
}
