import { Compass, Info } from "lucide-react";
import { AuthMessage } from "../components/AuthMessage";
import { FlightResultCard } from "../components/FlightResultCard";
import { SearchForm } from "../components/SearchForm";
import { useFavorites } from "../hooks/useFavorites";
import { useSearch } from "../hooks/useSearch";
import type { AirportOption, Flight, ToastType } from "../types";

function getErrorMessage(error: unknown): string | undefined {
  if (!error || typeof error !== "object") {
    return undefined;
  }

  const responseData = (error as { response?: { data?: { message?: string; detail?: string; error?: string } } }).response?.data;
  return responseData?.message || responseData?.detail || responseData?.error;
}

export type SearchPageProps = {
  airportOptions: AirportOption[];
  today: string;
  onNotify: (message: string, type?: ToastType) => void;
};

export function SearchPage({ airportOptions, today, onNotify }: SearchPageProps) {
  const { query, enabled } = useSearch();
  const { saveFavorite, isFavorite } = useFavorites(onNotify);

  const flights: Flight[] = Array.isArray(query.data?.data) ? query.data.data : [];
  const resultCount = typeof query.data?.count === "number" ? query.data.count : flights.length;
  const errorMessage = getErrorMessage(query.error) ?? (query.error instanceof Error ? query.error.message : undefined);

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Find a flight</h1>
        <p>Validated airport suggestions, polished cards, and easier booking actions.</p>
      </div>
      <SearchForm compact onNotify={onNotify} today={today} airportOptions={airportOptions} />
      {query.isLoading ? (
        <div className="skeleton-list">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      ) : null}
      {query.isError ? <AuthMessage variant="error">{errorMessage ?? "We could not retrieve flights. Please retry."}</AuthMessage> : null}
      {!enabled ? (
        <div className="empty-state">
          <div className="empty-icon"><Compass size={32} /></div>
          <h3>Choose a route to begin</h3>
          <p>Use the quick search above to explore flights from popular airports and curated destinations.</p>
        </div>
      ) : null}
      {!query.isLoading && !query.isError && enabled && flights.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Info size={32} /></div>
          <h3>No results yet</h3>
          <p>Try broadening the search window or switching to another airport.</p>
        </div>
      ) : null}
      {!query.isLoading && !query.isError && enabled && flights.length > 0 ? (
        <div className="meta-row compact" style={{ marginBottom: "1rem" }}>
          <span className="pill">Showing {flights.length} result{flights.length === 1 ? "" : "s"}</span>
          {typeof query.data?.count === "number" ? <span className="pill">{resultCount} total match{resultCount === 1 ? "" : "es"}</span> : null}
        </div>
      ) : null}
      <div className="results">
        {flights.map((flight) => (
          <FlightResultCard key={flight.flight_id} flight={flight} onFavorite={() => saveFavorite.mutate({
            flight_offer_id: flight.flight_id,
            airline: flight.segments[0]?.airline ?? "AIR",
            origin: flight.origin,
            destination: flight.destination,
            departure: flight.departure_time,
            arrival: flight.arrival_time,
            price: flight.price,
            currency: flight.currency,
          })} isFavorited={isFavorite(flight.flight_id)} />
        ))}
      </div>
    </section>
  );
}
