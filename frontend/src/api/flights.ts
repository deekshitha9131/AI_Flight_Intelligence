import { api } from './client';
import { FlightSearchRequest, FlightResponse } from '../types/flight';

// Search flights
export const searchFlights = async (searchRequest: FlightSearchRequest): Promise<{ flightSearchId: string; flights: FlightResponse[] }> => {
  const response = await api.postWithResponse<FlightResponse[]>('/flights/search', {
    body: searchRequest,
  });
  const flightSearchId = response.response.headers.get('X-Flight-Search-ID');
  if (!flightSearchId) {
    throw new Error('Flight search ID not found in response headers');
  }
  return {
    flightSearchId,
    flights: response.data
  };
}