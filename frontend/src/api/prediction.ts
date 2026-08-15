import client from "./client";
import { DEFAULT_CURRENCY, DEFAULT_TRAVEL_CLASS } from "../constants";
import type { Envelope, Prediction } from "../types";

export async function predictPrice(values: Record<string, unknown>) {
  const payload = {
    origin: String(values.origin ?? "").trim().toUpperCase(),
    destination: String(values.destination ?? "").trim().toUpperCase(),
    departure_date: values.departure_date,
    return_date: values.return_date ?? null,
    airline: values.airline ? String(values.airline).trim().toUpperCase() : null,
    cabin_class: String(values.cabin_class ?? DEFAULT_TRAVEL_CLASS).trim().toUpperCase(),
    adults: Number(values.adults ?? 1),
    children: Number(values.children ?? 0),
    infants: Number(values.infants ?? 0),
    stops: values.stops ? Number(values.stops) : null,
    duration_minutes: values.duration_minutes ? Number(values.duration_minutes) : null,
    departure_time: values.departure_time ? String(values.departure_time) : null,
    arrival_time: values.arrival_time ? String(values.arrival_time) : null,
    trip_type: String(values.trip_type ?? "ONE_WAY").toUpperCase(),
    currency: String(values.currency ?? DEFAULT_CURRENCY).trim().toUpperCase(),
  };

  const response = await client.post<Envelope<Prediction>>("/ai/predict-price", payload);
  return response.data;
}
