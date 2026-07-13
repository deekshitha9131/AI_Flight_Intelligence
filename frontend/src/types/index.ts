export interface Envelope<T> { success: boolean; message: string; data: T; count?: number }
export interface User { id: string; first_name: string; last_name: string; email: string; role: string; is_verified: boolean }
export interface Tokens { access_token: string; refresh_token: string; token_type: string; expires_in?: number }
export interface Flight { flight_id: string; origin: string; destination: string; departure_time: string; arrival_time: string; duration: string; stops: number; travel_class: string; price: number; currency: string; airline?: string; segments: Array<{ airline: string; airline_name?: string; flight_number: string }> }
export interface Prediction { prediction_id: string; predicted_price: number; currency: string; confidence_score?: number; price_range_low: number; price_range_high: number; estimated_savings?: number; suggested_booking_window?: string; model_version: string; processing_time_ms: number; predicted_at: string }
