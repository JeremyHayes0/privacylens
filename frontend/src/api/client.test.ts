import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch, ApiError, setAuthToken } from "./client";

function mockFetchOnce(response: { status: number; body: unknown }) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      status: response.status,
      ok: response.status >= 200 && response.status < 300,
      statusText: "Error",
      json: () => Promise.resolve(response.body),
    }),
  );
}

describe("apiFetch", () => {
  afterEach(() => {
    setAuthToken(null);
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on a successful response", async () => {
    mockFetchOnce({ status: 200, body: { id: "abc" } });

    const result = await apiFetch<{ id: string }>("/targets/abc");

    expect(result).toEqual({ id: "abc" });
  });

  it("attaches the Authorization header when a token is set", async () => {
    setAuthToken("test-token-123");
    mockFetchOnce({ status: 200, body: {} });

    await apiFetch("/targets");

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.headers["Authorization"]).toBe("Bearer test-token-123");
  });

  it("omits the Authorization header when no token is set", async () => {
    mockFetchOnce({ status: 200, body: {} });

    await apiFetch("/targets");

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.headers["Authorization"]).toBeUndefined();
  });

  it("throws an ApiError using the backend's `detail` message on failure", async () => {
    mockFetchOnce({ status: 401, body: { detail: "Incorrect email or password." } });

    await expect(apiFetch("/auth/login")).rejects.toMatchObject({
      status: 401,
      message: "Incorrect email or password.",
    });
  });

  it("falls back to statusText when the error body has no `detail`", async () => {
    mockFetchOnce({ status: 500, body: null });

    await expect(apiFetch("/targets")).rejects.toBeInstanceOf(ApiError);
  });
});
