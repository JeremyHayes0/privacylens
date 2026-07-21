import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../api/auth";
import { ApiError } from "../api/client";
import { AuthProvider, useAuth } from "./AuthContext";

// AuthContext talks to the backend exclusively through ../api/auth --
// mocking that module (rather than stubbing global fetch, as
// api/client.test.ts does) keeps these tests focused on AuthContext's
// own logic: token persistence, state transitions, error propagation.
vi.mock("../api/auth");

const SESSION_STORAGE_KEY = "privacylens_token";

/** A minimal component that exposes AuthContext's state/actions as clickable buttons and text, for assertions. */
function AuthHarness() {
  const { user, isLoading, login, register, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{String(isLoading)}</div>
      <div data-testid="user-email">{user?.email ?? "none"}</div>
      <button onClick={() => login("person@example.com", "hunter2").catch(() => {})}>Log in</button>
      <button onClick={() => register("new@example.com", "hunter2", "New Org").catch(() => {})}>
        Register
      </button>
      <button onClick={logout}>Log out</button>
    </div>
  );
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <AuthHarness />
    </AuthProvider>,
  );
}

const fakeUser = {
  id: "user-1",
  email: "person@example.com",
  organization_id: "org-1",
  role: "admin" as const,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

describe("AuthContext", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("starts with no user and isLoading false when there is no stored token", async () => {
    renderWithAuth();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(authApi.fetchCurrentUser).not.toHaveBeenCalled();
  });

  it("logs in successfully: fetches the user and persists the token", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: "tok-123", token_type: "bearer" });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(fakeUser);
    const user = userEvent.setup();
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByText("Log in"));

    await waitFor(() => expect(screen.getByTestId("user-email")).toHaveTextContent("person@example.com"));
    expect(sessionStorage.getItem(SESSION_STORAGE_KEY)).toBe("tok-123");
  });

  it("a failed login leaves the user unset", async () => {
    vi.mocked(authApi.login).mockRejectedValue(new ApiError(401, "Incorrect email or password."));
    const user = userEvent.setup();
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByText("Log in"));

    await waitFor(() => expect(authApi.login).toHaveBeenCalled());
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(sessionStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it("register() calls the register endpoint and then logs in", async () => {
    vi.mocked(authApi.register).mockResolvedValue(fakeUser);
    vi.mocked(authApi.login).mockResolvedValue({ access_token: "tok-456", token_type: "bearer" });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(fakeUser);
    const user = userEvent.setup();
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByText("Register"));

    await waitFor(() => expect(screen.getByTestId("user-email")).toHaveTextContent("person@example.com"));
    expect(authApi.register).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "hunter2",
      organization_name: "New Org",
    });
  });

  it("logout() clears the user and the stored token", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: "tok-123", token_type: "bearer" });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(fakeUser);
    const user = userEvent.setup();
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    await user.click(screen.getByText("Log in"));
    await waitFor(() => expect(screen.getByTestId("user-email")).toHaveTextContent("person@example.com"));

    await user.click(screen.getByText("Log out"));

    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(sessionStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it("clears an invalid stored token on mount rather than surfacing an error", async () => {
    sessionStorage.setItem(SESSION_STORAGE_KEY, "stale-token");
    vi.mocked(authApi.fetchCurrentUser).mockRejectedValue(new ApiError(401, "Could not validate credentials."));

    renderWithAuth();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(sessionStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });
});
