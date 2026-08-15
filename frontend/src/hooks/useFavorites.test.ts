import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { describe, it, expect, vi } from "vitest";
import { useFavorites } from "./useFavorites";
import * as flightsApi from "../api/flights";
import { useAuthStore } from "../store/auth";

vi.mock("../api/flights", () => ({
  getFavorites: vi.fn(),
  removeFavorite: vi.fn(),
  saveFavorite: vi.fn(),
}));

describe("useFavorites", () => {
  it("exposes filtered favorites and favorite ids", async () => {
    useAuthStore.getState().setTokens({
      access_token: "mock-access-token",
      refresh_token: "mock-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    });
    vi.mocked(flightsApi.getFavorites).mockResolvedValue({
      success: true,
      message: "ok",
      data: [{ id: "1", flight_offer_id: "flight-1", airline: "Emirates", origin: "HYD", destination: "DXB", departure: "2025-01-01T00:00:00Z", arrival: "2025-01-01T03:00:00Z", price: 100, currency: "USD", created_at: "2025-01-01T00:00:00Z" }],
      count: 1,
    } as never);

    const wrapper = ({ children }: { children: ReactNode }) => createElement(QueryClientProvider, { client: new QueryClient() }, children);

    const { result } = renderHook(() => useFavorites(), { wrapper });

    await waitFor(() => expect(result.current.filteredFavorites.length).toBe(1));
    expect(result.current.isFavorite("flight-1")).toBe(true);
  });
});
