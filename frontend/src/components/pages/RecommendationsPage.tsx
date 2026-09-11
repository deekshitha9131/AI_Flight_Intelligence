import React, { useEffect, useState } from 'react';
import { getRecommendations } from '../../api/recommendations';
import { FlightRecommendationResponse } from '../../types/recommendations';
import { getSearchFlights } from '../../utils/workspace';
import FlightCard from '../FlightCard';

const RecommendationsPage: React.FC = () => {
  const [recommendations, setRecommendations] = useState<FlightRecommendationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = async () => { const flights = getSearchFlights(); if (!flights.length) { setLoading(false); return; } setLoading(true); setError(null); try { setRecommendations(await getRecommendations(flights)); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load recommendations.'); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []);

  return <div className="page-stack"><header className="page-header"><div><span className="eyebrow">Decision support</span><h1 className="page-title">Recommendations with reasons.</h1><p className="page-subtitle">The recommendation service ranks your latest search and explains the trade-offs behind each option.</p></div><span className="badge">AI ranked</span></header>{loading && <section className="flight-list">{[1, 2, 3].map((item) => <div className="surface surface-pad" key={item}><div className="skeleton" style={{ width: 180 }} /><div className="skeleton" style={{ width: '70%', marginTop: 18 }} /><div className="skeleton" style={{ width: '45%', marginTop: 12 }} /></div>)}</section>}{error && <section className="surface error-state"><div className="empty-icon">!</div><h3>Recommendations unavailable</h3><p>{error}</p><button className="btn btn-outline" type="button" onClick={load}>Try again</button></section>}{!loading && !error && !recommendations.length && <section className="surface empty-state"><div className="empty-icon">✦</div><h3>Search before you rank</h3><p>Run a flight search first. Your latest results will become the basis for recommendations.</p><a className="btn btn-primary" href="/flights">Search flights →</a></section>}{!loading && !error && recommendations.length > 0 && <div className="flight-list">{recommendations.map((recommendation) => <article className="surface surface-pad" key={recommendation.flight.id}><div className="results-head"><div><span className="badge">Score {recommendation.score.toFixed(1)}</span><h2 className="section-title" style={{ marginTop: 10 }}>{recommendation.flight.origin} to {recommendation.flight.destination}</h2><p className="section-note">{recommendation.flight.airline} {recommendation.flight.flight_number}</p></div><strong className="price">{recommendation.flight.currency} {recommendation.flight.price.toFixed(2)}</strong></div><p style={{ margin: '18px 0', color: 'var(--muted)', fontSize: 14 }}>{recommendation.explanation}</p><FlightCard flight={recommendation.flight} /></article>)}</div>}</div>;
};

export default RecommendationsPage;
