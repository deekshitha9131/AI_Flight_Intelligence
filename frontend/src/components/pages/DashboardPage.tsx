import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../store/authContext';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const firstName = user?.first_name || user?.email.split('@')[0] || 'traveler';

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div className="hero-content">
          <span className="eyebrow">Your travel intelligence desk</span>
          <h1 className="hero-title">Make every flight decision with clarity.</h1>
          <p className="hero-copy">Welcome back, {firstName}. Search live options, ask the assistant for context, and tune the experience around how you travel.</p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/flights">Search flights <span aria-hidden="true">→</span></Link>
            <Link className="btn btn-outline" style={{ color: '#effcfb', borderColor: 'rgba(239,252,251,.35)' }} to="/assistant">Ask the assistant</Link>
          </div>
        </div>
      </section>

      <div className="page-header">
        <div><span className="eyebrow">Workspace</span><h2 className="page-title" style={{ fontSize: '30px' }}>A smarter way to plan</h2><p className="page-subtitle">Everything you need to move from a route idea to a confident next step.</p></div>
      </div>

      <section className="quick-grid">
        <Link className="quick-card" to="/flights"><span className="quick-icon" aria-hidden="true">⌁</span><strong>Search & compare</strong><span>Explore available flights by route, date, duration, and price.</span><span className="auth-link">Open flight search →</span></Link>
        <Link className="quick-card" to="/assistant"><span className="quick-icon" aria-hidden="true">✦</span><strong>Travel with context</strong><span>Ask for planning advice in a conversational workspace.</span><span className="auth-link">Open AI assistant →</span></Link>
        <Link className="quick-card" to="/preferences"><span className="quick-icon" aria-hidden="true">⚙</span><strong>Set your signal</strong><span>Shape recommendations with your cabin, airport, and budget preferences.</span><span className="auth-link">Tune preferences →</span></Link>
      </section>

      <section className="dashboard-grid">
        <div className="surface surface-pad">
          <span className="eyebrow">How it works</span><h2 className="section-title" style={{ marginTop: 7 }}>A focused flight workflow</h2><p className="section-note">The product keeps the useful parts of trip planning close at hand.</p>
          <div className="capability-list">
            <div className="capability"><span className="capability-mark">01</span><div><strong>Start with a route</strong><span>Use IATA airport codes and a departure date to bring live options into view.</span></div></div>
            <div className="capability"><span className="capability-mark">02</span><div><strong>Compare what matters</strong><span>See airline, timings, stops, duration, and price in one calm comparison surface.</span></div></div>
            <div className="capability"><span className="capability-mark">03</span><div><strong>Ask for a second opinion</strong><span>Use the assistant when the best choice needs more context than a price alone.</span></div></div>
          </div>
        </div>
        <div className="surface surface-pad" style={{ background: 'var(--accent-soft)' }}>
          <span className="eyebrow">Built for better decisions</span><h2 className="section-title" style={{ marginTop: 7 }}>Your preferences are part of the intelligence.</h2><p className="section-note">Keep your preferred cabin, currency, airport, timing, and budget in one place so future searches start closer to what you actually want.</p>
          <Link className="btn btn-primary" style={{ marginTop: 22 }} to="/preferences">Review preferences</Link>
        </div>
      </section>
    </div>
  );
};

export default DashboardPage;
