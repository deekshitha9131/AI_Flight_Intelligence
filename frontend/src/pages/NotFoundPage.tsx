import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page-section">
      <div className="empty-state">
        <div className="empty-icon">✈️</div>
        <h3>Page not found</h3>
        <p>The route you requested does not exist.</p>
        <Link className="primary-button" to="/">Back home</Link>
      </div>
    </section>
  );
}
