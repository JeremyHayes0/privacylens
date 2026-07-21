import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { useAsync } from "./useAsync";

describe("useAsync", () => {
  it("starts loading and resolves to the fetcher's data", async () => {
    const fetcher = vi.fn().mockResolvedValue({ id: "1" });
    const { result } = renderHook(() => useAsync(fetcher));

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeNull();

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data).toEqual({ id: "1" });
    expect(result.current.error).toBeNull();
  });

  it("surfaces an ApiError's message as the error state", async () => {
    const fetcher = vi.fn().mockRejectedValue(new ApiError(404, "Target not found."));
    const { result } = renderHook(() => useAsync(fetcher));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Target not found.");
    expect(result.current.data).toBeNull();
  });

  it("falls back to a generic message for a non-ApiError failure", async () => {
    const fetcher = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const { result } = renderHook(() => useAsync(fetcher));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Something went wrong.");
  });

  it("reload() re-invokes the fetcher and refreshes the data", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ count: 1 }).mockResolvedValueOnce({ count: 2 });
    const { result } = renderHook(() => useAsync(fetcher));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toEqual({ count: 1 });

    act(() => {
      result.current.reload();
    });

    await waitFor(() => expect(result.current.data).toEqual({ count: 2 }));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
