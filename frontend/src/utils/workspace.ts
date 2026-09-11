import { FlightResponse } from '../types/flight';

const SEARCH_ID_KEY = 'flight:last-search-id';
const FLIGHTS_KEY = 'flight:last-search-results';
const SELECTED_FLIGHT_KEY = 'flight:selected';

export const saveSearchContext = (searchId: string, flights: FlightResponse[]) => {
  sessionStorage.setItem(SEARCH_ID_KEY, searchId);
  sessionStorage.setItem(FLIGHTS_KEY, JSON.stringify(flights));
};

export const getSearchId = () => sessionStorage.getItem(SEARCH_ID_KEY);

export const getSearchFlights = (): FlightResponse[] => {
  const value = sessionStorage.getItem(FLIGHTS_KEY);
  if (!value) return [];
  try {
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) ? parsed as FlightResponse[] : [];
  } catch {
    return [];
  }
};

export const saveSelectedFlight = (flight: FlightResponse) => {
  sessionStorage.setItem(SELECTED_FLIGHT_KEY, JSON.stringify(flight));
};

export const getSelectedFlight = (): FlightResponse | null => {
  const value = sessionStorage.getItem(SELECTED_FLIGHT_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value) as FlightResponse;
  } catch {
    return null;
  }
};
