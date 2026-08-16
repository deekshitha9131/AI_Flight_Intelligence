import { Heart, HeartOff, Clock3, Compass, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import type { Flight } from "../types";

export type FlightResultCardProps = {
  flight: Flight;
  onFavorite: (flight: Flight) => void;
  isFavorited?: boolean;
};

export function FlightResultCard({
  flight,
  onFavorite,
  isFavorited = false,
}: FlightResultCardProps) {
  const segment = flight.segments[0];
  const airlineName = segment?.airline_name ?? segment?.airline ?? "Airline";
  const airlineCode = segment?.airline ?? "AIR";
  const flightNumber = segment?.flight_number ? `${segment.flight_number}` : "Flight";

  const departureDate = new Date(flight.departure_time);
  const arrivalDate = new Date(flight.arrival_time);
  const durationLabel = flight.duration
    .replace(/^PT/, "")
    .replace(/H/g, "h ")
    .replace(/M/g, "m");

  const formattedDeparture = departureDate.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  const formattedArrival = arrivalDate.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <article className="result-card">
      <div className="result-card-main">
        <div className="result-card-head">
          <div className="airline-badge" aria-hidden="true">
            {airlineCode.slice(0, 3).toUpperCase()}
          </div>
          <div>
            <div className="result-title">{airlineName}</div>
            <div className="result-subtitle">
              {flight.origin} → {flight.destination}
            </div>
          </div>
          <button
            className={`icon-button ${isFavorited ? "active" : ""}`}
            type="button"
            aria-label="Save flight"
            onClick={() => onFavorite(flight)}
          >
            {isFavorited ? <Heart size={18} fill="currentColor" /> : <HeartOff size={18} />}
          </button>
        </div>

        <div className="route-grid">
          <div className="route-block">
            <span className="route-label">Departure</span>
            <strong>{formattedDeparture}</strong>
            <small>{flight.origin}</small>
          </div>
          <div className="route-block">
            <span className="route-label">Arrival</span>
            <strong>{formattedArrival}</strong>
            <small>{flight.destination}</small>
          </div>
        </div>

        <div className="meta-row">
          <span>
            <Clock3 size={14} /> {durationLabel}
          </span>
          <span>
            <Compass size={14} />{" "}
            {flight.stops ? `${flight.stops} stop${flight.stops > 1 ? "s" : ""}` : "Non-stop"}
          </span>
          <span>
            <Wallet size={14} /> {flight.currency} {flight.price.toFixed(2)}
          </span>
        </div>

        <div className="meta-row compact">
          <span className="pill">{flight.travel_class}</span>
          <span className="pill">{flightNumber}</span>
          <span className="pill">Seats available</span>
        </div>
      </div>

      <div className="price-panel">
        <div className="price">
          {flight.currency} {flight.price.toFixed(2)}
        </div>
        <div className="price-caption">Per traveler</div>
        <Link
          className="primary-button small"
          to={`/booking/${flight.flight_id}`}
          state={{ flight }}
        >
          Book
        </Link>
      </div>
    </article>
  );
}
