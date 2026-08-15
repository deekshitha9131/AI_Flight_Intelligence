import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getBookings } from "../api/bookings";

export function BookingsPage() {
  const bookingsQuery = useQuery({ queryKey: ["bookings"], queryFn: getBookings });
  const bookings = bookingsQuery.data?.data ?? [];

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Booking history</h1>
        <p>Your recent reservations and upcoming departures in one place.</p>
      </div>
      <div className="results">
        {bookings.map((booking) => (
          <article className="result-card" key={booking.id}>
            <div>
              <div className="result-title">{booking.flight_offer_id}</div>
              <div className="result-subtitle">{booking.created_at} · {booking.status}</div>
            </div>
            <div className="cta-row">
              <span className="pill">{booking.currency} {booking.amount}</span>
              <Link className="ghost-button" to="/dashboard">Details</Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
