import { describe, expect, it } from "vitest";
import { enrichRecommendations } from "./recommendations";

describe("enrichRecommendations", () => {
  it("adds budget and seasonal metadata for recommendations", () => {
    const result = enrichRecommendations([
      { origin: "HYD", destination: "DXB", estimated_price: 180, currency: "USD", reason: "Popular route" },
    ]);

    expect(result[0]).toMatchObject({
      budgetTier: "value",
      season: expect.any(String),
      highlights: expect.arrayContaining([expect.stringContaining("option for")]),
    });
  });
});
