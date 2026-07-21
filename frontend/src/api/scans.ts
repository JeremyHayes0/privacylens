import { apiFetch } from "./client";
import type { Finding, Scan, ScanCreateResponse } from "./types";

export function listScansForTarget(targetId: string): Promise<Scan[]> {
  return apiFetch<Scan[]>(`/targets/${targetId}/scans`);
}

export function createScan(targetId: string): Promise<ScanCreateResponse> {
  return apiFetch<ScanCreateResponse>(`/targets/${targetId}/scans`, { method: "POST" });
}

export function getScan(scanId: string): Promise<Scan> {
  return apiFetch<Scan>(`/scans/${scanId}`);
}

export function listScanFindings(scanId: string): Promise<Finding[]> {
  return apiFetch<Finding[]>(`/scans/${scanId}/findings`);
}
