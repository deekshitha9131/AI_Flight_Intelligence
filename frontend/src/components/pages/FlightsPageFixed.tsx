import React, { useState } from 'react';
import { searchFlights } from '../../api/flights';
import { FlightResponse } from '../../types/flight';
import FlightCard from '../../components/FlightCard';
import Button from '../ui/Button';
import Input from '../ui/Input';
import PageHeader from '../ui/PageHeader';
import LoadingSpinner from '../ui/LoadingSpinner';
import SkeletonLoader from '../ui/SkeletonLoader';
import EmptyState from '../ui/EmptyState';
import ErrorState from '../ui/ErrorState';

const FlightsPage: React.FC = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState('');
  const [flights, setFlights] = useState<FlightResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await searchFlights({
        origin: origin.toUpperCase(),
        destination: destination.toUpperCase(),
        departure_date: departureDate,
        passengers: 1,
        cabin_class: 'ECONOMY',
        currency: 'USD',
      });
      setFlights(result.flights);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search flights');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Find your next flight"
        subtitle="AI-powered flight search and intelligence"
      />

      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Input
                label="From"
                type="text"
                id="origin"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="Enter origin (e.g., JFK)"
                required
              />
            </div>
            <div>
              <Input
                label="To"
                type="text"
                id="destination"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="Enter destination (e.g., LAX)"
                required
              />
            </div>
            <div>
              <Input
                label="Departure date"
                type="date"
                id="departure-date"
                value={departureDate}
                onChange={(e) => setDepartureDate(e.target.value)}
                required
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={loading || !(origin && destination && departureDate)}
              className="px-8"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Searching...
                </>
              ) : (
                'Search Flights'
              )}
            </Button>
          </div>
        </form>
      </div>

      {loading && !error && (
        <div className="space-y-6">
          <div className="text-center py-12">
            <div className="flex justify-center space-x-4">
              <SkeletonLoader width={120} height={20} className="mb-2" />
              <SkeletonLoader width={180} height={16} />
              <SkeletonLoader width={150} height={14} className="flex-shrink-0" />
              <SkeletonLoader width={100} height={14} />
            </div>
          </div>
          <div className="grid gap-6">
            {[1, 2, 3, 4].map((_, i) => (
              <div key={i} className="card">
                <div className="p-6">
                  {'' /* Fixed the closing div tags */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <SkeletonLoader width={180} height={18} className="mb-2" />
                        <SkeletonLoader width={120} height={14} className="mb-1" />
                        <div className="flex items-center gap-2">
                          <SkeletonLoader width={60} height={10} className="mr-2" />
                          <SkeletonLoader width={60} height={10} className="mr-2" />
                          <SkeletonLoader width={40} height={10} />
                        </div>
                      </div>
                      <div className="text-right">
                        <SkeletonLoader width={80} height={18} className="mb-1" />
                        <SkeletonLoader width={60} height={14} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <ErrorState
          title="Unable to load flights"
          description={error}
          retryAction={
            <Button variant="outline" onClick={handleSubmit} className="mt-4">
              Try Again
            </Button>
          }
        />
      )}

      {!loading && !error && flights.length === 0 && (
        <EmptyState
          title="No flights found"
          description="Try adjusting your search criteria or check back later for new flight options."
          action={
            <Button variant="outline" onClick={() => {
              setOrigin('');
              setDestination('');
              setDepartureDate('');
            }} className="mt-4">
              New Search
            </Button>
          }
        />
      )}

      {!loading && !error && flights.length > 0 && (
        <>
          <div className="flex items-center justify-between px-4">
            <h2 className="text-xl font-bold text-gray-900">
              {flights.length} flights found
            </h2>
            <div className="flex items-center space-x-3">
              <Button variant="outline" size="sm" onClick={() => {
                setOrigin('');
                setDestination('');
                setDepartureDate('');
              }}>
                New Search
              </Button>
            </div>
          </div>
          <div className="grid gap-6 mt-4">
            {flights.map((flight) => {
              const stopsText = flight.stops === 0 ? 'Nonstop' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`;
              return (
                <FlightCard
                  key={flight.id}
                  flight={{
                    ...flight,
                    // Adding formatted times for display in FlightCard
                    departure_time_formatted: formatTime(flight.departure_time),
                    arrival_time_formatted: formatTime(flight.arrival_time),
                    duration_formatted: formatDuration(flight.duration)
                  }}
                />
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default FlightsPage;