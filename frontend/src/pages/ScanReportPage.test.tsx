import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as scansApi from "../api/scans";
import type { Finding, Scan } from "../api/types";
import { ScanReportPage } from "./ScanReportPage";

vi.mock("../api/scans");

// ScanReportPage renders inside <Layout>, which calls useAuth() for
// the nav rail's signed-in-user display -- these tests aren't
// exercising auth at all, so the module is mocked with a fixed,
// unused-by-these-tests user rather than wrapping every render in a
// real AuthProvider (which would need ../api/auth mocked too, for no
// benefit to what this file is actually testing).
vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "person@example.com",
      organization_id: "org1",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    },
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

function renderScanReport(scanId = "scan-1") {
  return render(
    <MemoryRouter initialEntries={[`/scans/${scanId}`]}>
      <Routes>
        <Route path="/scans/:scanId" element={<ScanReportPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function makeScan(overrides: Partial<Scan> = {}): Scan {
  return {
    id: "scan-1",
    target_id: "target-1",
    status: "queued",
    started_at: null,
    completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    error_message: null,
    ...overrides,
  };
}

const sampleFinding: Finding = {
  id: "f1",
  scan_id: "scan-1",
  category: "https",
  finding_type: "detected_configuration",
  severity: "info",
  title: "Site served over HTTPS",
  description: "The scanned page was served over HTTPS.",
  evidence: { final_url: "https://example.com" },
  created_at: "2026-01-01T00:00:05Z",
};

describe("ScanReportPage", () => {
  beforeEach(() => {
    // Fake timers give deterministic control over the 3-second poll
    // interval -- tests advance time explicitly rather than waiting
    // on a real setTimeout. The first poll still runs immediately
    // (it's not gated by a timer), so findByText queries against the
    // initial render don't need any time advancement at all.
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.resetAllMocks();
  });

  it("shows a waiting message and no scope banner while queued", async () => {
    vi.mocked(scansApi.getScan).mockResolvedValue(makeScan({ status: "queued" }));
    vi.mocked(scansApi.listScanFindings).mockResolvedValue([]);
    renderScanReport();

    expect(await screen.findByText(/Waiting for the worker/)).toBeInTheDocument();
    expect(screen.queryByText(/not legal advice/)).not.toBeInTheDocument();
  });

  it("polls again while running, and stops once completed", async () => {
    vi.mocked(scansApi.getScan)
      .mockResolvedValueOnce(makeScan({ status: "running" }))
      .mockResolvedValueOnce(makeScan({ status: "completed", completed_at: "2026-01-01T00:00:10Z" }));
    vi.mocked(scansApi.listScanFindings).mockResolvedValue([sampleFinding]);
    renderScanReport();

    await screen.findByText(/Scan in progress/);
    expect(scansApi.getScan).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(3000);

    await waitFor(() => expect(scansApi.getScan).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/not legal advice/)).toBeInTheDocument();

    // Further time passing should not trigger a third poll -- the
    // effect stops rescheduling once status is completed/failed.
    await vi.advanceTimersByTimeAsync(10000);
    expect(scansApi.getScan).toHaveBeenCalledTimes(2);
  });

  it("renders findings grouped under their category heading", async () => {
    vi.mocked(scansApi.getScan).mockResolvedValue(makeScan({ status: "completed" }));
    vi.mocked(scansApi.listScanFindings).mockResolvedValue([sampleFinding]);
    renderScanReport();

    expect(await screen.findByText("HTTPS / TLS")).toBeInTheDocument();
    expect(screen.getByText("Site served over HTTPS")).toBeInTheDocument();
  });

  it("shows the error message and no scope banner for a failed scan", async () => {
    vi.mocked(scansApi.getScan).mockResolvedValue(
      makeScan({ status: "failed", error_message: "Could not reach https://example.com" }),
    );
    vi.mocked(scansApi.listScanFindings).mockResolvedValue([]);
    renderScanReport();

    expect(await screen.findByText("Could not reach https://example.com")).toBeInTheDocument();
    expect(screen.queryByText(/not legal advice/)).not.toBeInTheDocument();
  });
});
