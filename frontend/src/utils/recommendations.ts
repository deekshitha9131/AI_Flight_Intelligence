export interface RecommendationInsight {
  origin: string;
  destination: string;
  estimated_price: number;
  currency: string;
  reason: string;
  budgetTier?: "budget" | "value" | "premium";
  season?: "winter" | "summer" | "spring" | "autumn";
  highlights?: string[];
  similarityScore?: number;
}

const seasonByMonth = {
  0: "winter",
  1: "winter",
  2: "spring",
  3: "spring",
  4: "summer",
  5: "summer",
  6: "summer",
  7: "autumn",
  8: "autumn",
  9: "autumn",
  10: "winter",
  11: "winter",
} as const;

export function enrichRecommendations(items: Array<Omit<RecommendationInsight, "budgetTier" | "season" | "highlights" | "similarityScore">>) {
  const month = new Date().getMonth();
  const season = seasonByMonth[month as keyof typeof seasonByMonth] ?? "spring";

  return items.map((item, index) => {
    const budgetTier = item.estimated_price < 160 ? "budget" : item.estimated_price < 260 ? "value" : "premium";
    const highlights = [
      `${budgetTier} option for ${item.destination}`,
      `${season} travel window`,
      index % 2 === 0 ? "similar routes loved by frequent travelers" : "balanced fare and comfort",
    ];

    return {
      ...item,
      budgetTier,
      season,
      highlights,
      similarityScore: Number((0.7 + index * 0.05).toFixed(2)),
    } satisfies RecommendationInsight;
  });
}
