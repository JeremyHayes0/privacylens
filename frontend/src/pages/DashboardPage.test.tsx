import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import * as targetsApi from "../api/targets";
import type { Target, User } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/targets");
vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

function mockUser(role: User["role"]): User {
  return {
    id: "u1",
    email: "person@example.com",
    organization_id: "org1",
    role,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function mockAuth(role: User["role"]) {
  vi.mocked(useAuth).mockReturnValue({
    user: mockUser(role),
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

const sampleTarget: Target = {
  id: "t1",
  organization_id: "org1",
  url: "https://example.com",
  label: "Example site",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

describe("DashboardPage", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("hides the Add target control for a viewer", async () => {
    mockAuth("viewer");
    vi.mocked(targetsApi.listTargets).mockResolvedValue([sampleTarget]);
    renderDashboard();

    await screen.findByText("Example site");

    expect(screen.queryByRole("button", { name: "Add target" })).not.toBeInTheDocument();
  });

  it("shows the Add target control for an analyst", async () => {
    mockAuth("analyst");
    vi.mocked(targetsApi.listTargets).mockResolvedValue([]);
    renderDashboard();

    expect(await screen.findByRole("button", { name: "Add target" })).toBeInTheDocument();
  });

  it("shows an empty state when there are no targets", async () => {
    mockAuth("admin");
    vi.mocked(targetsApi.listTargets).mockResolvedValue([]);
    renderDashboard();

    expect(await screen.findByText(/No targets yet/)).toBeInTheDocument();
  });

  it("submits the add-target form and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(targetsApi.listTargets).mockResolvedValueOnce([]).mockResolvedValueOnce([sampleTarget]);
    vi.mocked(targetsApi.createTarget).mockResolvedValue(sampleTarget);
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByText(/No targets yet/);

    await user.click(screen.getByRole("button", { name: "Add target" }));
    await user.type(screen.getByLabelText("URL"), "https://example.com");
    await user.type(screen.getByLabelText("Label"), "Example site");
    await user.click(screen.getByRole("button", { name: "Add target" }));

    await waitFor(() =>
      expect(targetsApi.createTarget).toHaveBeenCalledWith({
        url: "https://example.com",
        label: "Example site",
      }),
    );
    expect(await screen.findByText("Example site")).toBeInTheDocument();
  });

  it("shows the backend's error message when adding a target fails", async () => {
    mockAuth("admin");
    vi.mocked(targetsApi.listTargets).mockResolvedValue([]);
    vi.mocked(targetsApi.createTarget).mockRejectedValue(
      new ApiError(422, "URL scheme must be one of ['http', 'https']."),
    );
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByText(/No targets yet/);

    await user.click(screen.getByRole("button", { name: "Add target" }));
    await user.type(screen.getByLabelText("URL"), "ftp://example.com");
    await user.type(screen.getByLabelText("Label"), "Bad scheme");
    await user.click(screen.getByRole("button", { name: "Add target" }));

    expect(await screen.findByText("URL scheme must be one of ['http', 'https'].")).toBeInTheDocument();
  });
});
