import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../store/authContext';
import { searchFlights } from '../../api/flights';
import { getRecommendations } from '../../api/recommendations';
import { FlightSearchRequest, FlightResponse } from '../../types/flight';
import { FlightRecommendationResponse } from '../../types/recommendations';

const FlightsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchRequest, setSearchRequest] = useState<FlightSearchRequest>({
    origin: '',
    destination: '',
    departure_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD
    return_date: undefined,
    passengers: 1,
    cabin_class: 'ECONOMY',
    currency: 'USD',
  });
  const [flights, setFlights] = useState<FlightResponse[]>([]);
  const [recommendations, setRecommendations] = useState<FlightRecommendationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRec, setLoadingRec] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorRec, setErrorRec] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value, type, checked } = e.target;
    let newValue: any = value;
    if (type === 'checkbox') {
      newValue = checked;
    } else if (name === 'passengers') {
      newValue = parseInt(value, 10);
    }
    setSearchRequest((prev) => ({
      ...prev,
      [name]: newValue,
    }));
  };

  const handleDateChange = (
    field: 'departure_date' | 'return_date',
    date: string
  ) => {
    setSearchRequest((prev) => ({
      ...prev,
      [field]: date || undefined,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await searchFlights(searchRequest);
      setFlights(result);
      // Clear previous recommendations when new search is done
      setRecommendations([]);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          'An error occurred while searching flights'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleGetRecommendations = async () => {
    if (flights.length === 0) return;
    setErrorRec(null);
    setLoadingRec(true);
    try {
      const result = await getRecommendations(flights);
      setRecommendations(result);
    } catch (err: any) {
      setErrorRec(
        err.response?.data?.detail ||
          err.message ||
          'An error occurred while getting recommendations'
      );
    } finally {
      setLoadingRec(false);
    }
  };

  return (
    <div className="flights-page">
      <header>
        <h1>Flight Search</h1>
        <p>Welcome, {user?.email ?? 'User'}!</p>
      </header>
      <div className="search-form">
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div>
              <label htmlFor="origin">Origin:</label>
              <input
                type="text"
                id="origin"
                name="origin"
                placeholder="e.g., NYC"
                value={searchRequest.origin}
                onChange={handleChange}
                maxLength={3}
              />
            </div>
            <div>
              <label htmlFor="destination">Destination:</label>
              <input
                type="text"
                id="destination"
                name="destination"
                placeholder="e.g., LON"
                value={searchRequest.destination}
                onChange={handleChange}
                maxLength={3}
              />
            </div>
          </div>
          <div className="form-row">
            <div>
              <label htmlFor="departure_date">Departure Date:</label>
              <input
                type="date"
                id="departure_date"
                name="departure_date"
                value={searchRequest.departure_date}
                onChange={(e) => handleDateChange('departure_date', e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="return_date">Return Date (optional):</label>
              <input
                type="date"
                id="return_date"
                name="return_date"
                value={searchRequest.return_date || ''}
                onChange={(e) => handleDateChange('return_date', e.target.value)}
              />
            </div>
          </div>
          <div className="form-row">
            <div>
              <label htmlFor="passengers">Passengers:</label>
              <input
                type="number"
                id="passengers"
                name="passengers"
                min="1"
                max="9"
                value={searchRequest.passengers}
                onChange={handleChange}
              />
            </div>
            <div>
              <label htmlFor="cabin_class">Cabin Class:</label>
              <select
                id="cabin_class"
                name="cabin_class"
                value={searchRequest.cabin_class}
                onChange={handleChange}
              >
                <option value="ECONOMY">Economy</option>
                <option value="PREMIUM_ECONOMY">Premium Economy</option>
                <option value="BUSINESS">Business</option>
                <option value="FIRST">First</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div>
              <label htmlFor="currency">Currency:</label>
              <input
                type="text"
                id="currency"
                name="currency"
                placeholder="e.g., USD"
                value={searchRequest.currency}
                onChange={handleChange}
                maxLength={3}
              />
            </div>
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Searching...' : 'Search Flights'}
          </button>
        </form>
      </div>

      {error && <p className="error">{error}</p>}

      {flights.length > 0 && (
        <div className="results">
          <h2>Search Results ({flights.length} flights found)</h2>
          <ul className="flights-list">
            {flights.map((flight) => (
              <li key={flight.id} className="flight-item">
                <div className="flight-info">
                  <span className="flight-number">
                    {flight.airline} {flight.flight_number}
                  </span>
                  <span className="route">
                    {flight.origin} → {flight.destination}
                  </span>
                  <span className="schedule">
                    {new Date(flight.departure_time).toLocaleString()} →
                    {new Date(flight.arrival_time).toLocaleString()}
                  </span>
                  <span className="details">
                    {flight.stops} stop(s) • {flight.duration} min
                  </span>
                  <span className="price">
                    {flight.price.toFixed(2)} {flight.currency}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          {flights.length > 0 && (
            <div className="recommendations-section">
              <button
                onClick={handleGetRecommendations}
                disabled={loadingRec}
              >
                {loadingRec ? 'Getting recommendations...' : 'Get Recommendations'}
              </button>
              {errorRec && <p className="error">{errorRec}</p>}
              {recommendations.length > 0 && (
                <div className="recommendations-results">
                  <h3>Recommendations:</h3>
                  <ul className="recommendations-list">
                    {recommendations.map((rec, idx) => (
                      <li key={idx} className="recommendation-item">
                        <pre>{JSON.stringify(rec, null, 2)}</pre>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {flights.length === 0 && loading === false && !error && (
        <p>No flights found. Try different search criteria.</p>
      )}
    </div>
  );
};

export default FlightsPage;