import client from "./client";
import { DEFAULT_CURRENCY, DEFAULT_MAX_RESULTS, DEFAULT_TRAVEL_CLASS } from "../constants";
import type { Envelope, Flight } from "../types";

export interface SearchFlightsParams {
  origin?: string | null;
  destination?: string | null;
  departure_date?: string | null;
  travel_class?: string | null;
  adults?: number | null;
  children?: number | null;
  infants?: number | null;
  non_stop?: boolean | null;
  currency?: string | null;
  max_results?: number | null;
}

export interface FavoriteItem {
  id: string;
  flight_offer_id: string;
  airline: string;
  origin: string;
  destination: string;
  departure: string;
  arrival: string;
  price: number;
  currency: string;
  created_at?: string;
}

export interface FavoriteListResponse {
  success: boolean;
  message: string;
  data: FavoriteItem[];
  count: number;
}

export interface FavoritePayload {
  flight_offer_id: string;
  airline: string;
  origin: string;
  destination: string;
  departure: string;
  arrival: string;
  price: number;
  currency: string;
}

export async function searchFlights(params: SearchFlightsParams) {
  const response = await client.get<Envelope<Flight[]> & { count: number; message?: string }>("/flights/search", {
    params: {
      origin: params.origin || undefined,
      destination: params.destination || undefined,
      departure_date: params.departure_date || undefined,
      travel_class: params.travel_class || DEFAULT_TRAVEL_CLASS,
      adults: Number(params.adults || 1),
      children: Number(params.children || 0),
      infants: Number(params.infants || 0),
      non_stop: Boolean(params.non_stop),
      currency: params.currency || DEFAULT_CURRENCY,
      max_results: params.max_results || DEFAULT_MAX_RESULTS,
    },
  });

  return response.data;
}

export async function getFavorites(page = 1, pageSize = 20) {
  const response = await client.get<Envelope<FavoriteItem[]>>("/flights/favorites", {
    params: { page, page_size: pageSize },
  });

  return response.data;
}

export async function saveFavorite(payload: FavoritePayload) {
  return client.post("/flights/favorites", payload);
}

export async function removeFavorite(id: string) {
  return client.delete(`/flights/favorites/${id}`);
}
