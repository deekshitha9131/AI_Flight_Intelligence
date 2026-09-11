export interface FlightSearchRequest {
  origin: string; // IATA code, 3 letters
  destination: string; // IATA code, 3 letters
  departure_date: string; // ISO string
  return_date?: string; // ISO string, optional
  passengers: number; // 1-9
  cabin_class: string; // e.g., ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
  currency: string; // ISO 4217 currency code, 3 letters
}

export interface FlightResponse {
  id: string;
  airline: string;
  flight_number: string;
  origin: string;
  destination: string;
  departure_time: string; // ISO string
  arrival_time: string; // ISO string
  duration: number; // in minutes
  stops: number;
  price: number;
  currency: string; // ISO 4217 currency code
  itinerary_id?: string;
  segments?: FlightSegment[];
  return_segments?: FlightSegment[];
  return_departure_time?: string;
  return_arrival_time?: string;
  return_duration?: number;
  return_stops?: number;
  fare_options?: FareOption[];
}

export interface FlightSegment {
  id?: string;
  airline: string;
  flight_number: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
}

export interface FareOption {
  id: string;
  price: number;
  currency: string;
}
