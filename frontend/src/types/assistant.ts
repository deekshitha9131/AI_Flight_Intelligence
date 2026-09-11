import { FlightResponse } from './flight';

export interface AssistantChatRequest {
  message: string;
  conversation_id?: string;
}

export interface FlightIntent {
  intent: string;
  origin?: string;
  destination?: string;
  departure_date?: string;
  return_date?: string;
  passengers?: number;
  cabin?: string;
  time_preference?: string;
  price_preference?: string;
}

export interface AssistantResponse {
  message: string;
  conversation_id: string;
  flight_results?: FlightResponse[];
  requires_clarification: boolean;
  clarification_questions?: string[];
}
