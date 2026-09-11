export interface PredictionRequest {
  origin: string; // IATA code, 3 letters
  destination: string; // IATA code, 3 letters
  departure_date: string; // ISO string
  passengers: number; // 1-9
  cabin_class: string; // e.g., ECONOMY, BUSINESS
  currency: string; // ISO 4217 currency code, 3 letters
  airline: string; // Airline name
  flight_number: string; // Flight number
  departure_time: string; // HH:MM format
  arrival_time: string; // HH:MM format
  duration_minutes: number; // in minutes
  stops: number; // number of stops
}

export interface PredictionResponse {
  predicted_price: number;
  currency: string; // ISO 4217 currency code
  is_estimate: boolean;
  model_version: string;
}

export interface PredictionResponseWithID extends PredictionResponse {
  id: string;
  created_at: string; // ISO string
}
