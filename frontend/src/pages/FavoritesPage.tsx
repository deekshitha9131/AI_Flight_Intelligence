import { Heart } from "lucide-react";
import { AuthMessage } from "../components/AuthMessage";
import { useFavorites } from "../hooks/useFavorites";
import { formatFavoriteDateTime } from "../hooks/favoritesUtils";
import type { ToastType } from "../types";

type FavoritesPageProps = {
  onNotify: (message: string, type?: ToastType) => void;
};

export function FavoritesPage({ onNotify }: FavoritesPageProps) {
  const {
    favoritesQuery,
    removeFavorite,
    filter,
    setFilter,
    sortBy,
    setSortBy,
    filteredFavorites,
  } = useFavorites(onNotify);

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Favorites</h1>
        <p>Keep the best routes and bargains in one place.</p>
      </div>

      <div className="dashboard-grid">
        <label className="field search-filter">
          <span className="field-label">Search favorites</span>
          <input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search by airline or route"
          />
        </label>
        <label className="field search-filter">
          <span className="field-label">Sort by</span>
          <select
            value={sortBy}
            onChange={(event) =>
              setSortBy(event.target.value as "recent" | "price" | "route")
            }
          >
            <option value="recent">Recently added</option>
            <option value="price">Price</option>
            <option value="route">Route</option>
          </select>
        </label>
      </div>

      {favoritesQuery.isLoading ? (
        <div className="skeleton-list">
          <div className="skeleton-card" />
        </div>
      ) : null}

      {favoritesQuery.isError ? (
        <AuthMessage variant="error">
          We could not load your favorites. Please sign in again if needed.
        </AuthMessage>
      ) : null}

      {!favoritesQuery.isLoading &&
      !favoritesQuery.isError &&
      filteredFavorites.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Heart size={32} />
          </div>
          <h3>No favorites yet</h3>
          <p>Save a flight card from search results to keep it handy.</p>
        </div>
      ) : null}

      <div className="results">
        {filteredFavorites.map((item) => (
          <article className="result-card" key={item.id}>
            <div className="result-card-main">
              <div className="result-card-head">
                <div className="airline-badge">
                  {item.airline.slice(0, 3).toUpperCase()}
                </div>
                <div>
                  <div className="result-title">
                    {item.origin} → {item.destination}
                  </div>
                  <div className="result-subtitle">Saved Flight</div>
                </div>
              </div>

              <div className="route-grid">
                <div className="route-block">
                  <span className="route-label">Departure</span>
                  <strong>{formatFavoriteDateTime(item.departure)}</strong>
                  <small>{item.origin}</small>
                </div>
                <div className="route-block">
                  <span className="route-label">Arrival</span>
                  <strong>{formatFavoriteDateTime(item.arrival)}</strong>
                  <small>{item.destination}</small>
                </div>
              </div>

              <div className="meta-row compact">
                <span className="pill">{item.airline}</span>
                <span className="pill">
                  {item.currency} {item.price.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="price-panel">
              <div className="price">
                {item.currency} {item.price.toFixed(2)}
              </div>
              <button
                className="ghost-button"
                type="button"
                onClick={() => removeFavorite.mutate(item.id)}
              >
                Remove
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
