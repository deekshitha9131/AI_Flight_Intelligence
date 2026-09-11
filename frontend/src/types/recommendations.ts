import { FlightResponse } from './flight';

export interface FlightRecommendationRequest {
  flights: FlightResponse[];
}

export interface FlightRecommendationResponse {
  flight: FlightResponse;
  score: number;
  explanation: string;
}

// For the search and recommend endpoint, we can reuse FlightSearchRequest
export type FlightSearchAndRecommendRequest = FlightSearchRequest;
export type FlightSearchAndRecommendResponse = FlightRecommendationResponse[];
