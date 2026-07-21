import { apiFetch } from "./client";
import type { Target } from "./types";

export interface CreateTargetPayload {
  url: string;
  label: string;
}

export function listTargets(): Promise<Target[]> {
  return apiFetch<Target[]>("/targets");
}

export function getTarget(targetId: string): Promise<Target> {
  return apiFetch<Target>(`/targets/${targetId}`);
}

export function createTarget(payload: CreateTargetPayload): Promise<Target> {
  return apiFetch<Target>("/targets", { method: "POST", body: payload });
}

export function deactivateTarget(targetId: string): Promise<Target> {
  return apiFetch<Target>(`/targets/${targetId}`, { method: "DELETE" });
}
