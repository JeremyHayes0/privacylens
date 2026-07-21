import { apiFetch } from "./client";
import type { User } from "./types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  organization_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function login(payload: LoginPayload): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", { method: "POST", body: payload });
}

export function register(payload: RegisterPayload): Promise<User> {
  return apiFetch<User>("/auth/register", { method: "POST", body: payload });
}

export function fetchCurrentUser(): Promise<User> {
  return apiFetch<User>("/auth/me");
}
