import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { searchFlights } from "../api/flights";

export function useSearch() {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const enabled = Boolean(params.get("origin") && params.get("destination") && params.get("departure_date"));

  const query = useQuery({
    queryKey: ["flights", location.search],
    enabled,
    queryFn: async () => searchFlights({
      origin: params.get("origin"),
      destination: params.get("destination"),
      departure_date: params.get("departure_date"),
      travel_class: params.get("travel_class"),
      adults: Number(params.get("adults") || 1),
      children: Number(params.get("children") || 0),
      infants: Number(params.get("infants") || 0),
      non_stop: params.get("non_stop") === "true",
      max_results: Number(params.get("max_results") || undefined),
    }),
  });

  return { query, params, enabled };
}
