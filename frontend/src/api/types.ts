// These types are hand-mirrored from the backend's Pydantic schemas
// (backend/app/schemas/) rather than generated. For a project this
// size that's a reasonable choice; generating them from the OpenAPI
// schema (e.g. via openapi-typescript) is the natural upgrade once
// the API surface stabilizes -- see the project blueprint's frontend
// architecture notes for why that matters at larger scale.

export type UserRole = "admin" | "analyst" | "viewer";

export interface User {
  id: string;
  email: string;
  organization_id: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Target {
  id: string;
  organization_id: string;
  url: string;
  label: string;
  is_active: boolean;
  created_at: string;
}

export type ScanStatus = "queued" | "running" | "completed" | "failed";

export interface Scan {
  id: string;
  target_id: string;
  status: ScanStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  error_message: string | null;
}

export interface ScanCreateResponse {
  scan_id: string;
  status: ScanStatus;
}

export type FindingCategory =
  | "https"
  | "headers"
  | "cookies"
  | "trackers"
  | "privacy_policy"
  | "tos"
  | "consent_banner";

export type FindingType =
  | "potential_issue"
  | "observation"
  | "detected_configuration"
  | "recommendation";

export type FindingSeverity = "info" | "low" | "medium" | "high";

export interface Finding {
  id: string;
  scan_id: string;
  category: FindingCategory;
  finding_type: FindingType;
  severity: FindingSeverity;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  created_at: string;
}
