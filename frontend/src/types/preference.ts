export interface PreferenceBase {
  preferred_cabin?: string | null;
  preferred_currency?: string | null;
  preferred_airport?: string | null;
  preferred_time?: string | null;
  min_price?: number | null;
  max_price?: number | null;
}

export interface PreferenceCreate extends PreferenceBase {}

export interface PreferenceUpdate extends PreferenceBase {}

export interface PreferenceInDB extends PreferenceBase {
  id: string;
  user_id: string;
  created_at: string; // ISO date string
  updated_at: string | null; // ISO date string or null
}