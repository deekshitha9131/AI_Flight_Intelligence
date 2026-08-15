export interface User {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  is_verified: boolean;
  avatar_url?: string | null;
  preferred_airport?: string;
  preferred_cabin?: string;
  currency_preference?: string;
  notification_settings?: {
    email: boolean;
    push: boolean;
    price_alerts: boolean;
  };
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
}
