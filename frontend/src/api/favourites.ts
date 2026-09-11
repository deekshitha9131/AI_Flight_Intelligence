import { api } from './client';
import { FlightResponse } from '../types/flight';

export type Favourite = Pick<FlightResponse, 'airline' | 'flight_number' | 'origin' | 'destination' | 'departure_time' | 'arrival_time' | 'duration' | 'stops' | 'price' | 'currency'> & { id: string; flight_id: string; created_at: string };

const toFavourite = (flight: FlightResponse): Omit<Favourite, 'created_at'> & { flight_id: string } => ({
  flight_id: flight.id,
  id: flight.id,
  airline: flight.airline,
  flight_number: flight.flight_number,
  origin: flight.origin,
  destination: flight.destination,
  departure_time: flight.departure_time,
  arrival_time: flight.arrival_time,
  duration: flight.duration,
  stops: flight.stops,
  price: flight.price,
  currency: flight.currency,
});

export const getFavourites = () => api.get<Favourite[]>('/favourites');
export const addFavourite = (flight: FlightResponse) => api.post<Favourite>('/favourites', { body: toFavourite(flight) });
export const removeFavourite = (flightId: string) => api.delete<void>(`/favourites/${encodeURIComponent(flightId)}`);