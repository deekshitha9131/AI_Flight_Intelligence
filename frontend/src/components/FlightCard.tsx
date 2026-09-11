import React from 'react';
import { FlightResponse } from '../types/flight';
import Badge from './ui/Badge';

interface FlightCardProps {
  flight: FlightResponse;
  onSelect?: (flight: FlightResponse) => void;
}

const FlightCard: React.FC<FlightCardProps> = ({
  flight,
  onSelect
}) => {
  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const stopsText = flight.stops === 0 ? 'Nonstop' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`;
  const stopsBadge = flight.stops === 0 ? 'success' : 'warning';

  return (

    <article className="surface flight-card">
      <div>
        <div className="flight-meta"><span className="badge">{flight.airline}</span><span>{flight.flight_number}</span><span>·</span><span>{formatDuration(flight.duration)}</span></div>
        <div className="flight-route"><div><strong className="airport-code">{flight.origin}</strong><div className="time">{formatTime(flight.departure_time)}</div></div><span className="route-line" aria-hidden="true" /><div><strong className="airport-code">{flight.destination}</strong><div className="time">{formatTime(flight.arrival_time)}</div></div></div>
        <div className="flight-meta"><span className={`badge ${flight.stops > 0 ? 'badge-warning' : ''}`}>{stopsText}</span>{flight.fare_options && flight.fare_options.length > 1 && <span>{flight.fare_options.length} fare options</span>}</div>
      </div>
      <div className="flight-price"><div className="price">{flight.currency} {flight.price.toFixed(2)}</div><div className="price-caption">per passenger</div><button className="btn btn-outline" type="button" onClick={() => onSelect?.(flight)}>View details <span aria-hidden="true">→</span></button></div>
    </article>
  );
};

export default FlightCard;