import client from "./client";
import type { Envelope } from "../types";

export interface BookingPayload {
  flight_offer_id: string;
  first_name: string;
  last_name: string;
  email: string;
  travelers: number;
}

export interface BookingRecord {
  id: string;
  flight_offer_id: string;
  status: string;
  amount: number;
  currency: string;
  created_at: string;
}

export async function getBookings() {
  const response = await client.get<Envelope<BookingRecord[]>>("/bookings");
  return response.data;
}

export async function createBooking(payload: BookingPayload) {
  const response = await client.post<Envelope<BookingRecord>>("/bookings", payload);
  return response.data;
}
