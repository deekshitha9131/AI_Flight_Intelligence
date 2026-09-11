import { api } from './client';
import {
  FlightRecommendationRequest,
  FlightRecommendationResponse,
  FlightSearchAndRecommendRequest,
  FlightSearchAndRecommendResponse,
} from '../types/recommendations';
import { FlightSearchRequest, FlightResponse } from '../types/flight';

// Get recommendations based on a list of flights
export const getRecommendations = async (
  flights: FlightResponse[]
): Promise<FlightRecommendationResponse[]> => {
  const request: FlightRecommendationRequest = { flights };
  const response = await api.post<FlightRecommendationResponse[]>('/recommendations/', {
    body: request,
  });
  return response;
};

// Search for flights and get recommendations in one call
export const searchAndRecommend = async (
  searchRequest: FlightSearchRequest
): Promise<FlightSearchAndRecommendResponse> => {
  const response = await api.post<FlightSearchAndRecommendResponse>(
    '/recommendations/search',
    {
      body: searchRequest,
    }
  );
  return response;
};

