import React, { useState } from 'react';
import { searchFlights } from '../../api/flights';
import { FlightResponse } from '../../types/flight';
import FlightCard from '../FlightCard';
import { saveSearchContext, saveSelectedFlight } from '../../utils/workspace';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { AirportOption, findAirport, suggestAirports } from '../../utils/airports';
import { addFavourite, getFavourites, removeFavourite } from '../../api/favourites';

const today = new Date().toISOString().split('T')[0];
const INITIAL_RESULT_COUNT = 12;

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
  const [visibleResultCount, setVisibleResultCount] = useState(INITIAL_RESULT_COUNT);
  const [favouriteIds, setFavouriteIds] = useState<string[]>([]);

  React.useEffect(() => { getFavourites().then((items) => setFavouriteIds(items.map((item) => item.flight_id))).catch(() => undefined); }, []);
  const toggleFavourite = async (flight: FlightResponse) => {
    if (favouriteIds.includes(flight.id)) { await removeFavourite(flight.id); setFavouriteIds((ids) => ids.filter((id) => id !== flight.id)); }
    else { await addFavourite(flight); setFavouriteIds((ids) => [...ids, flight.id]); }
  };

  const selectAirport = (setter: React.Dispatch<React.SetStateAction<string>>, airport: AirportOption) => {
    setter(airport.code);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError(null); setSelected(null);
    try {
      const resolvedOrigin = findAirport(origin);
      const resolvedDestination = findAirport(destination);
      if (!resolvedOrigin || !resolvedDestination) {
        setError('Choose an airport from the suggestions so we can use its IATA code.');
        setLoading(false);
        return;
      }
      const result = await searchFlights({ origin: resolvedOrigin.code, destination: resolvedDestination.code, departure_date: departureDate, passengers, cabin_class: cabinClass, currency: 'USD' });
      saveSearchContext(result.flightSearchId, result.flights);
      setFlights(result.flights);
      setVisibleResultCount(INITIAL_RESULT_COUNT);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401
        ? 'Your session has expired. Please sign in again to search for flights.'
        : err instanceof Error ? err.message : 'We could not load flights right now.');
    }
    finally { setLoading(false); }
  };

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Flight intelligence</span><h1 className="page-title">Search the sky with context.</h1><p className="page-subtitle">Compare available routes by the details that shape a good trip: timing, stops, duration, and price.</p></div><span className="badge">Live search</span></header>
    <section className="surface search-panel"><div style={{ marginBottom: 18 }}><h2 className="section-title">Where are you going?</h2><p className="section-note">Search by airport code, airport name, or city.</p></div><form onSubmit={handleSubmit} className="search-grid">
      <div className="field"><label htmlFor="origin">From</label><input id="origin" placeholder="Hyderabad or HYD" value={origin} onChange={(event) => setOrigin(event.target.value)} required />{suggestAirports(origin).map((airport) => <button className="airport-suggestion" type="button" key={airport.code} onClick={() => selectAirport(setOrigin, airport)}>{airport.city} ({airport.code}) <span>{airport.name}</span></button>)}</div>
      <div className="field"><label htmlFor="destination">To</label><input id="destination" placeholder="Delhi or DEL" value={destination} onChange={(event) => setDestination(event.target.value)} required />{suggestAirports(destination).map((airport) => <button className="airport-suggestion" type="button" key={airport.code} onClick={() => selectAirport(setDestination, airport)}>{airport.city} ({airport.code}) <span>{airport.name}</span></button>)}</div>
      <div className="field"><label htmlFor="departure">Departure</label><input id="departure" type="date" min={today} value={departureDate} onChange={(event) => setDepartureDate(event.target.value)} required /></div>
      <div className="field"><label htmlFor="passengers">Travelers</label><select id="passengers" value={passengers} onChange={(event) => setPassengers(Number(event.target.value))}>{[1, 2, 3, 4, 5, 6, 7, 8, 9].map((number) => <option key={number} value={number}>{number} {number === 1 ? 'traveler' : 'travelers'}</option>)}</select></div>
      <div className="field"><label htmlFor="cabin">Cabin</label><select id="cabin" value={cabinClass} onChange={(event) => setCabinClass(event.target.value)}><option value="ECONOMY">Economy</option><option value="PREMIUM_ECONOMY">Premium economy</option><option value="BUSINESS">Business</option><option value="FIRST">First</option></select></div>
      <button className="btn btn-primary search-action" type="submit" disabled={loading}>{loading ? 'Searching...' : 'Search flights'} {!loading && <span aria-hidden="true">→</span>}</button>
    </form></section>
    {loading && <section className="flight-list">{[1, 2, 3].map((item) => <div className="surface flight-card" key={item}><div><div className="skeleton" style={{ width: 180 }} /><div className="skeleton" style={{ width: 290, marginTop: 24 }} /><div className="skeleton" style={{ width: 90, marginTop: 16 }} /></div><div className="skeleton" style={{ width: 120 }} /></div>)}</section>}
    {error && <section className="surface error-state"><div className="empty-icon">!</div><h3>Something went wrong</h3><p>{error}</p><button className="btn btn-outline" type="button" onClick={handleSubmit}>Try again</button></section>}
    {!loading && !error && flights.length === 0 && <section className="surface empty-state"><div className="empty-icon">⌁</div><h3>Your next route starts here</h3><p>Enter an origin, destination, and date to see available flight options.</p></section>}
    {!loading && !error && flights.length > 0 && <section className="page-stack" style={{ gap: 14 }}><div className="results-head"><div><h2 className="section-title">{flights.length} options found</h2><p className="section-note">Showing {Math.min(visibleResultCount, flights.length)} of {flights.length}. Compare the details before you decide.</p></div><button className="btn btn-ghost" type="button" onClick={() => setFlights([])}>Clear results</button></div><div className="flight-list">{flights.slice(0, visibleResultCount).map((flight) => <FlightCard key={flight.id} flight={flight} onSelect={setSelected} isFavourite={favouriteIds.includes(flight.id)} onToggleFavourite={toggleFavourite} />)}</div>{visibleResultCount < flights.length && <button className="btn btn-outline" type="button" onClick={() => setVisibleResultCount((count) => Math.min(count + INITIAL_RESULT_COUNT, flights.length))}>Load more flights</button>}</section>}
    {selected && <section className="surface surface-pad"><div className="results-head"><div><span className="eyebrow">Flight detail</span><h2 className="section-title" style={{ marginTop: 7 }}>{selected.origin} to {selected.destination}</h2><p className="section-note">{selected.airline} {selected.flight_number} · {selected.currency} {selected.price.toFixed(2)}</p></div><button className="btn btn-ghost" type="button" onClick={() => setSelected(null)}>Close</button></div><div className="detail-grid"><div><strong>Departure</strong><span>{new Date(selected.departure_time).toLocaleString()}</span></div><div><strong>Arrival</strong><span>{new Date(selected.arrival_time).toLocaleString()}</span></div><div><strong>Duration</strong><span>{selected.duration} minutes</span></div><div><strong>Stops</strong><span>{selected.stops === 0 ? 'Nonstop' : `${selected.stops} stop${selected.stops > 1 ? 's' : ''}`}</span></div>{selected.segments && selected.segments.length > 0 && <div className="wide"><strong>Segments</strong><span>{selected.segments.map((segment) => `${segment.origin} to ${segment.destination} (${segment.flight_number})`).join(' · ')}</span></div>}{selected.return_segments && selected.return_segments.length > 0 && <div className="wide"><strong>Return</strong><span>{selected.return_segments.map((segment) => `${segment.origin} to ${segment.destination} (${segment.flight_number})`).join(' · ')}</span></div>}</div><div className="hero-actions"><button className="btn btn-primary" type="button" onClick={() => { saveSelectedFlight(selected); window.location.href = '/predictions'; }}>Analyze price</button><Link className="btn btn-outline" to="/recommendations">View recommendations</Link></div></section>}
  </div>;
};

export default FlightsPage;
