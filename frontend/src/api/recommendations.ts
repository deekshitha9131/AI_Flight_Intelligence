import client from "./client";
import type { Envelope } from "../types";

export interface Recommendation {
  origin: string;
  destination: string;
  airline: string;
  cabin_class: string;
  estimated_price: number;
  currency: string;
  reason: string;
  score: number;
}

export async function getRecommendations(limit = 6) {
  const response = await client.get<Envelope<Recommendation[]>>("/recommendations", {
    params: { limit },
  });
  return response.data;
}
