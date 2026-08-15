import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { createBooking } from "../api/bookings";
import type { Flight, ToastType } from "../types";

export function BookingPage({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { flightId } = useParams();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", travelers: "1" });

  const selectedFlight = (location.state as { flight?: Flight } | undefined)?.flight;
  const flight = selectedFlight ?? {
    flight_id: flightId ?? "",
    origin: "",
    destination: "",
    departure_time: "",
    arrival_time: "",
    duration: "",
    stops: 0,
    travel_class: "",
    price: 0,
    currency: "USD",
    airline: "",
    segments: [],
  };
  const bookingMutation = useMutation({
    mutationFn: () => createBooking({
      flight_offer_id: flight.flight_id,
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      travelers: Number(form.travelers || 1),
    }),
    onSuccess: () => {
      if (typeof window !== "undefined") {
        const current = Number(window.localStorage.getItem("ai-flight-analytics-bookings") ?? "0");
        window.localStorage.setItem("ai-flight-analytics-bookings", String(current + 1));
      }
      onNotify("Booking request prepared", "success");
      navigate(`/booking/${flight.flight_id}/confirm`);
    },
    onError: () => onNotify("We could not place the booking right now. Please retry.", "error"),
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    bookingMutation.mutate();
  };

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Passenger details</h1>
        <p>Complete the traveler details for your selected flight.</p>
      </div>
      <div className="dashboard-grid">
        <article className="card-panel">
          <div className="eyebrow">Selected flight</div>
          <h3>{flight.origin} → {flight.destination}</h3>
          <p>{flight.airline} · {flight.currency} {flight.price.toFixed(2)} · {flight.travel_class}</p>
        </article>
        <article className="card-panel">
          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field-label">First name</span>
              <input required value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} />
            </label>
            <label className="field">
              <span className="field-label">Last name</span>
              <input required value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} />
            </label>
            <label className="field">
              <span className="field-label">Email</span>
              <input type="email" required value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
            </label>
            <label className="field">
              <span className="field-label">Travelers</span>
              <input type="number" min="1" max="6" value={form.travelers} onChange={(event) => setForm((current) => ({ ...current, travelers: event.target.value }))} />
            </label>
            <div className="cta-row">
              <button className="primary-button" type="submit" disabled={bookingMutation.isPending}>Continue to confirmation</button>
              <Link className="ghost-button" to="/bookings">View bookings</Link>
            </div>
          </form>
        </article>
      </div>
    </section>
  );
}
