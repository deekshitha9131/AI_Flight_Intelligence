import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <section className="page-section">
      <div className="empty-state">
        <div className="empty-icon">🔒</div>
        <h3>Access restricted</h3>
        <p>You need an active session to view this page.</p>
        <Link className="primary-button" to="/login">Sign in</Link>
      </div>
    </section>
  );
}
