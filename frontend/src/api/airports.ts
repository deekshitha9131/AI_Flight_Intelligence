import client from "./client";
import type { AirportOption, Envelope } from "../types";

export interface BackendAirport {
  airport_code: string;
  airport_name: string;
  city: string;
  country: string;
  iata_code: string;
  latitude?: number | null;
  longitude?: number | null;
}

export async function searchAirports(keyword: string): Promise<AirportOption[]> {
  const trimmed = keyword.trim();
  if (!trimmed || trimmed.length < 2) {
    return [];
  }

  try {
    const response = await client.get<Envelope<BackendAirport[]>>("/airports/search", {
      params: { keyword: trimmed },
    });

    const data = response.data?.data || [];
    return data.map((item) => ({
      code: item.iata_code || item.airport_code,
      label: `${item.airport_name} (${item.iata_code || item.airport_code})`,
      city: item.city || item.iata_code,
      country: item.country || "",
    }));
  } catch (err) {
    return [];
  }
}
