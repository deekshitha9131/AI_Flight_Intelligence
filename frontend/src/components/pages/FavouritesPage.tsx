import React, { useEffect, useState } from 'react';
import FlightCard from '../FlightCard';
import { getFavourites, removeFavourite, Favourite } from '../../api/favourites';

const FavouritesPage: React.FC = () => {
  const [favourites, setFavourites] = useState<Favourite[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getFavourites().then(setFavourites).catch((err) => setError(err instanceof Error ? err.message : 'Unable to load favourites.')); }, []);
  const remove = async (flightId: string) => { try { await removeFavourite(flightId); setFavourites((items) => items.filter((item) => item.flight_id !== flightId)); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to remove favourite.'); } };

  return <div className="page-stack"><header className="page-header"><div><span className="eyebrow">Your shortlist</span><h1 className="page-title">Favourites.</h1><p className="page-subtitle">Keep the routes worth coming back to close at hand.</p></div><span className="badge">{favourites.length} saved</span></header>{error && <div className="auth-error" role="alert">{error}</div>}{favourites.length === 0 && !error ? <section className="surface empty-state"><div className="empty-icon">☆</div><h3>No saved flights yet</h3><p>Save a flight from search results and it will appear here.</p></section> : <div className="flight-list">{favourites.map((flight) => <FlightCard key={flight.id} flight={{ ...flight, id: flight.flight_id }} isFavourite onToggleFavourite={() => remove(flight.flight_id)} />)}</div>}</div>;
};

export default FavouritesPage;