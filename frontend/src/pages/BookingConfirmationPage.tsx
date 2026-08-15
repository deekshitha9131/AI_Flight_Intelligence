import { Link, useParams } from "react-router-dom";

export function BookingConfirmationPage() {
  const { flightId } = useParams();

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Booking confirmed</h1>
        <p>Your flight request was received and is ready to be reviewed.</p>
      </div>
      <article className="card-panel">
        <div className="eyebrow">Reservation #{flightId?.slice(0, 6).toUpperCase() ?? "FLIGHT"}</div>
        <h2>Thanks for booking with AI Flight</h2>
        <p>Your details are stored in the booking history and you can manage them from the bookings view.</p>
        <div className="cta-row">
          <Link className="primary-button" to="/bookings">View booking history</Link>
          <Link className="ghost-button" to="/dashboard">Back to dashboard</Link>
        </div>
      </article>
    </section>
  );
}
