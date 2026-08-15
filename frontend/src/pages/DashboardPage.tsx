import { Bookmark, CalendarDays, Sparkles, TrendingUp, UserCircle2, Wind } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getFavorites } from "../api/flights";
import { SearchForm } from "../components/SearchForm";
import { useAuthStore } from "../store/auth";

type ToastType = "success" | "error" | "warning" | "info";

type DashboardProps = {
  today: string;
  airportOptions: Array<{ code: string; label: string; city: string; country: string }>;
  onNotify: (message: string, type?: ToastType) => void;
};

function readStoredNumber(key: string, fallback = 0) {
  if (typeof window === "undefined") return fallback;
  const value = Number(window.localStorage.getItem(key) ?? fallback);
  return Number.isFinite(value) ? value : fallback;
}

export function DashboardPage({ today, airportOptions, onNotify }: DashboardProps) {
  const user = useAuthStore((state) => state.user);
  const tokens = useAuthStore((state) => state.tokens);
  const favoriteQuery = useQuery({
    queryKey: ["favorites-dashboard"],
    queryFn: async () => getFavorites(1, 4),
    enabled: Boolean(tokens),
  });


  const favoriteItems = favoriteQuery.data?.data ?? [];
  const totalSearches = readStoredNumber("ai-flight-analytics-searches");
  const recentBookings = readStoredNumber("ai-flight-analytics-bookings");
  const priceAlerts = Math.max(1, Math.min(6, favoriteItems.length + 1));

  const analyticsItems = useMemo(() => [
    { label: "Total searches", value: String(totalSearches) },
    { label: "Saved flights", value: String(favoriteItems.length) },
    { label: "Recent bookings", value: String(recentBookings) },
    { label: "Price alerts", value: String(priceAlerts) },
  ], [favoriteItems.length, priceAlerts, recentBookings, totalSearches]);

  const popularDestinations = useMemo(() => {
    const counts = new Map<string, number>();
    favoriteItems.forEach((item) => {
      counts.set(item.destination, (counts.get(item.destination) ?? 0) + 1);
    });

    const entries = Array.from(counts.entries()).sort((left, right) => right[1] - left[1]).slice(0, 3);
    return entries.length > 0 ? entries.map(([code, count]) => ({
      code,
      count,
      label: airportOptions.find((item) => item.code === code)?.city ?? code,
    })) : [
      { code: "DXB", count: 2, label: "Dubai" },
      { code: "SIN", count: 1, label: "Singapore" },
      { code: "LHR", count: 1, label: "London" },
    ];
  }, [airportOptions, favoriteItems]);

  const recentActivity = [
    { label: "Searches submitted", value: `${totalSearches} tracked` },
    { label: "Saved flights", value: `${favoriteItems.length} saved` },
    { label: "Bookings prepared", value: `${recentBookings} recent` },
  ];

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Hello, {user?.first_name ?? "traveller"}</h1>
        <p>Everything you need for a calmer, smarter trip is assembled here.</p>
      </div>
      <section className="dashboard-grid">
        <article className="card-panel hero-card">
          <div className="eyebrow"><Sparkles size={16} /> Welcome back</div>
          <h2>Plan your next escape with confidence</h2>
          <p>Use quick search, saved trips, and travel insights to keep momentum without the friction.</p>
          <div className="cta-row">
            <Link className="primary-button" to="/search">Search flights</Link>
            <Link className="ghost-button" to="/assistant">Ask assistant</Link>
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><CalendarDays size={14} /> Quick search</div>
          <SearchForm compact onNotify={onNotify} today={today} airportOptions={airportOptions} />
        </article>
        <article className="card-panel">
          <div className="eyebrow"><TrendingUp size={14} /> Dashboard analytics</div>
          <div className="analytics-grid">
            {analyticsItems.map((item) => (
              <div key={item.label} className="metric">
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Bookmark size={14} /> Saved flights</div>
          <div className="list-stack">
            {favoriteItems.map((item, index) => <div key={`${item.origin}-${item.destination}-${index}`} className="list-item"><span>{item.origin} → {item.destination}</span><strong>{item.currency} {item.price.toFixed(2)}</strong></div>)}
            {favoriteItems.length === 0 ? <div className="message info">No saved flights yet.</div> : null}
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Wind size={14} /> Popular destinations</div>
          <div className="list-stack">
            {popularDestinations.map((destination) => (
              <div key={destination.code} className="list-item">
                <span>{destination.label}</span>
                <strong>{destination.count} saved</strong>
              </div>
            ))}
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><UserCircle2 size={14} /> Recent activity</div>
          <div className="list-stack">
            {recentActivity.map((item) => (
              <div key={item.label} className="list-item"><span>{item.label}</span><strong>{item.value}</strong></div>
            ))}
          </div>
        </article>
      </section>
    </section>
  );
}
