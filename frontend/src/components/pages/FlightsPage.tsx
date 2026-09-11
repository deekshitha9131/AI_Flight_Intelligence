import React, { useState } from 'react';
import { searchFlights } from '../../api/flights';
import { FlightResponse } from '../../types/flight';
import FlightCard from '../FlightCard';
import { saveSearchContext, saveSelectedFlight } from '../../utils/workspace';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';

const today = new Date().toISOString().split('T')[0];

const FlightsPage: React.FC = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState('');
  const [passengers, setPassengers] = useState(1);
  const [cabinClass, setCabinClass] = useState('ECONOMY');
  const [flights, setFlights] = useState<FlightResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<FlightResponse | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError(null); setSelected(null);
    try {
      const result = await searchFlights({ origin: origin.toUpperCase(), destination: destination.toUpperCase(), departure_date: departureDate, passengers, cabin_class: cabinClass, currency: 'USD' });
      saveSearchContext(result.flightSearchId, result.flights);
      setFlights(result.flights);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401
        ? 'Your session has expired. Please sign in again to search for flights.'
        : err instanceof Error ? err.message : 'We could not load flights right now.');
    }
    finally { setLoading(false); }
  };

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Flight intelligence</span><h1 className="page-title">Search the sky with context.</h1><p className="page-subtitle">Compare available routes by the details that shape a good trip: timing, stops, duration, and price.</p></div><span className="badge">Live search</span></header>
    <section className="surface search-panel"><div style={{ marginBottom: 18 }}><h2 className="section-title">Where are you going?</h2><p className="section-note">Use three-letter airport codes to start a search.</p></div><form onSubmit={handleSubmit} className="search-grid">
      <div className="field"><label htmlFor="origin">From</label><input id="origin" maxLength={3} placeholder="HYD" value={origin} onChange={(event) => setOrigin(event.target.value.toUpperCase())} required /></div>
      <div className="field"><label htmlFor="destination">To</label><input id="destination" maxLength={3} placeholder="DEL" value={destination} onChange={(event) => setDestination(event.target.value.toUpperCase())} required /></div>
      <div className="field"><label htmlFor="departure">Departure</label><input id="departure" type="date" min={today} value={departureDate} onChange={(event) => setDepartureDate(event.target.value)} required /></div>
      <div className="field"><label htmlFor="passengers">Travelers</label><select id="passengers" value={passengers} onChange={(event) => setPassengers(Number(event.target.value))}>{[1, 2, 3, 4, 5, 6, 7, 8, 9].map((number) => <option key={number} value={number}>{number} {number === 1 ? 'traveler' : 'travelers'}</option>)}</select></div>
      <div className="field"><label htmlFor="cabin">Cabin</label><select id="cabin" value={cabinClass} onChange={(event) => setCabinClass(event.target.value)}><option value="ECONOMY">Economy</option><option value="PREMIUM_ECONOMY">Premium economy</option><option value="BUSINESS">Business</option><option value="FIRST">First</option></select></div>
      <button className="btn btn-primary search-action" type="submit" disabled={loading}>{loading ? 'Searching...' : 'Search flights'} {!loading && <span aria-hidden="true">→</span>}</button>
    </form></section>
    {loading && <section className="flight-list">{[1, 2, 3].map((item) => <div className="surface flight-card" key={item}><div><div className="skeleton" style={{ width: 180 }} /><div className="skeleton" style={{ width: 290, marginTop: 24 }} /><div className="skeleton" style={{ width: 90, marginTop: 16 }} /></div><div className="skeleton" style={{ width: 120 }} /></div>)}</section>}
    {error && <section className="surface error-state"><div className="empty-icon">!</div><h3>Something went wrong</h3><p>{error}</p><button className="btn btn-outline" type="button" onClick={handleSubmit}>Try again</button></section>}
    {!loading && !error && flights.length === 0 && <section className="surface empty-state"><div className="empty-icon">⌁</div><h3>Your next route starts here</h3><p>Enter an origin, destination, and date to see available flight options.</p></section>}
    {!loading && !error && flights.length > 0 && <section className="page-stack" style={{ gap: 14 }}><div className="results-head"><div><h2 className="section-title">{flights.length} options found</h2><p className="section-note">Compare the details before you decide.</p></div><button className="btn btn-ghost" type="button" onClick={() => setFlights([])}>Clear results</button></div><div className="flight-list">{flights.map((flight) => <FlightCard key={flight.id} flight={flight} onSelect={setSelected} />)}</div></section>}
    {selected && <section className="surface surface-pad"><div className="results-head"><div><span className="eyebrow">Flight detail</span><h2 className="section-title" style={{ marginTop: 7 }}>{selected.origin} to {selected.destination}</h2><p className="section-note">{selected.airline} {selected.flight_number} · {selected.currency} {selected.price.toFixed(2)}</p></div><button className="btn btn-ghost" type="button" onClick={() => setSelected(null)}>Close</button></div><div className="hero-actions"><button className="btn btn-primary" type="button" onClick={() => { saveSelectedFlight(selected); window.location.href = '/predictions'; }}>Analyze price</button><Link className="btn btn-outline" to="/recommendations">View recommendations</Link></div></section>}
  </div>;
};

export default FlightsPage;
