import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { SearchPage } from "./SearchPage";

vi.mock("../hooks/useSearch", () => ({
  useSearch: () => ({
    query: { data: { data: [] }, count: 0, isLoading: false, isError: false, error: null },
    enabled: true,
  }),
}));

vi.mock("../hooks/useFavorites", () => ({
  useFavorites: () => ({ saveFavorite: { mutate: vi.fn() }, isFavorite: () => false }),
}));

describe("SearchPage", () => {
  it("renders the empty state when no results are available", () => {
    render(
      <MemoryRouter>
        <SearchPage airportOptions={[]} today="2025-01-01" onNotify={() => {}} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no results yet/i)).toBeInTheDocument();
  });
});
