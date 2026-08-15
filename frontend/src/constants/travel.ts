export const TRAVEL_CLASSES = [
  { value: "ECONOMY", label: "Economy" },
  { value: "PREMIUM_ECONOMY", label: "Premium economy" },
  { value: "BUSINESS", label: "Business" },
  { value: "FIRST", label: "First" },
] as const;

export const DEFAULT_TRAVEL_CLASS = "ECONOMY";
export const DEFAULT_CURRENCY = "USD";
export const DEFAULT_MAX_RESULTS = 10;
export const DEFAULT_PASSENGERS = { adults: 1, children: 0, infants: 0 };
export const MAX_PASSENGERS = 9;
export const AIRPORT_SUGGESTION_LIMIT = 4;
