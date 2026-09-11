export interface AirportOption {
  code: string;
  name: string;
  city: string;
  country: string;
}

export const AIRPORTS: AirportOption[] = [
  { code: 'HYD', name: 'Rajiv Gandhi International Airport', city: 'Hyderabad', country: 'India' },
  { code: 'DEL', name: 'Indira Gandhi International Airport', city: 'New Delhi', country: 'India' },
  { code: 'BOM', name: 'Chhatrapati Shivaji Maharaj International Airport', city: 'Mumbai', country: 'India' },
  { code: 'BLR', name: 'Kempegowda International Airport', city: 'Bengaluru', country: 'India' },
  { code: 'MAA', name: 'Chennai International Airport', city: 'Chennai', country: 'India' },
  { code: 'CCU', name: 'Netaji Subhas Chandra Bose International Airport', city: 'Kolkata', country: 'India' },
  { code: 'JFK', name: 'John F. Kennedy International Airport', city: 'New York', country: 'United States' },
  { code: 'LAX', name: 'Los Angeles International Airport', city: 'Los Angeles', country: 'United States' },
  { code: 'LHR', name: 'Heathrow Airport', city: 'London', country: 'United Kingdom' },
  { code: 'CDG', name: 'Charles de Gaulle Airport', city: 'Paris', country: 'France' },
  { code: 'DXB', name: 'Dubai International Airport', city: 'Dubai', country: 'United Arab Emirates' },
  { code: 'SIN', name: 'Changi Airport', city: 'Singapore', country: 'Singapore' },
];

export const findAirport = (value: string): AirportOption | undefined => {
  const normalized = value.trim().toLowerCase();
  if (normalized === 'delhi') return AIRPORTS.find((airport) => airport.code === 'DEL');
  return AIRPORTS.find((airport) => airport.code.toLowerCase() === normalized)
    ?? AIRPORTS.find((airport) => airport.city.toLowerCase() === normalized)
    ?? AIRPORTS.find((airport) => airport.name.toLowerCase() === normalized);
};

export const suggestAirports = (value: string): AirportOption[] => {
  const normalized = value.trim().toLowerCase();
  if (!normalized) return [];
  return AIRPORTS.filter((airport) => [airport.code, airport.city, airport.name, airport.country]
    .some((field) => field.toLowerCase().includes(normalized))).slice(0, 6);
};