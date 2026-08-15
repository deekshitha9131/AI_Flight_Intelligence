import { describe, expect, it } from "vitest";
import type { FavoriteItem, FavoriteListResponse } from "../api/flights";
import { mergeFavoriteItem, removeFavoriteItem } from "./favoritesUtils";

const baseFavorite: FavoriteItem = {
  id: "fav-1",
  flight_offer_id: "offer-1",
  airline: "EK",
  origin: "HYD",
  destination: "DXB",
  departure: "2025-12-01T10:30:00",
  arrival: "2025-12-01T12:45:00",
  price: 299.99,
  currency: "USD",
};

const baseResponse: FavoriteListResponse = {
  success: true,
  message: "ok",
  data: [baseFavorite],
  count: 1,
};

describe("favorites state helpers", () => {
  it("adds a newly created favorite to the current list", () => {
    const created: FavoriteItem = {
      ...baseFavorite,
      id: "fav-2",
      flight_offer_id: "offer-2",
      price: 399.99,
    };

    const next = mergeFavoriteItem(baseResponse, created);

    expect(next?.data).toHaveLength(2);
    expect(next?.data[0].flight_offer_id).toBe("offer-2");
    expect(next?.count).toBe(2);
  });

  it("removes a favorite by its record id", () => {
    const next = removeFavoriteItem(baseResponse, "fav-1");

    expect(next?.data).toHaveLength(0);
    expect(next?.count).toBe(0);
  });
});
