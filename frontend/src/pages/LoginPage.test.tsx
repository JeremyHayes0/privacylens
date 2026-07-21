import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../api/auth";
import { ApiError } from "../api/client";
import { AuthProvider } from "../context/AuthContext";
import { LoginPage } from "./LoginPage";

vi.mock("../api/auth");

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  afterEach(() => {
    vi.resetAllMocks();
    sessionStorage.clear();
  });

  it("shows the backend's error message when login fails", async () => {
    vi.mocked(authApi.login).mockRejectedValue(new ApiError(401, "Incorrect email or password."));
    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "person@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Incorrect email or password.")).toBeInTheDocument();
  });

  it("disables the submit button while a login is in flight", async () => {
    let resolveLogin!: (value: { access_token: string; token_type: string }) => void;
    vi.mocked(authApi.login).mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve;
      }),
    );
    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "person@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();

    resolveLogin({ access_token: "tok", token_type: "bearer" });
    await waitFor(() => expect(authApi.fetchCurrentUser).toHaveBeenCalled());
  });

  it("calls the login API with the entered credentials", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: "tok-789", token_type: "bearer" });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: "u1",
      email: "person@example.com",
      organization_id: "org1",
      role: "viewer",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "person@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() =>
      expect(authApi.login).toHaveBeenCalledWith({
        email: "person@example.com",
        password: "correct-password",
      }),
    );
  });
});
