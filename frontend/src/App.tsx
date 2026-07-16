import {
  Bookmark,
  CalendarDays,
  Clock3,
  Compass,
  Eye,
  EyeOff,
  Heart,
  HeartOff,
  Home as HomeIcon,
  Info,
  Loader2,
  MoonStar,
  Plane,
  SendHorizonal,
  ShieldCheck,
  Sparkles,
  Star,
  SunMedium,
  TrendingUp,
  UserCircle2,
  Wallet,
  Wind,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import client from "./api/client";
import { useAuthStore } from "./store/auth";
import type { Envelope, Flight, Prediction, Tokens, User } from "./types";

const today = new Date().toISOString().slice(0, 10);
const airportOptions = [
  { code: "HYD", label: "Hyderabad (HYD)", city: "Hyderabad", country: "India" },
  { code: "DEL", label: "Delhi (DEL)", city: "Delhi", country: "India" },
  { code: "BOM", label: "Mumbai (BOM)", city: "Mumbai", country: "India" },
  { code: "BLR", label: "Bengaluru (BLR)", city: "Bengaluru", country: "India" },
  { code: "DXB", label: "Dubai (DXB)", city: "Dubai", country: "UAE" },
  { code: "LHR", label: "London Heathrow (LHR)", city: "London", country: "United Kingdom" },
  { code: "JFK", label: "New York JFK (JFK)", city: "New York", country: "USA" },
  { code: "SIN", label: "Singapore (SIN)", city: "Singapore", country: "Singapore" },
  { code: "BKK", label: "Bangkok (BKK)", city: "Bangkok", country: "Thailand" },
  { code: "SFO", label: "San Francisco (SFO)", city: "San Francisco", country: "USA" },
  { code: "FRA", label: "Frankfurt (FRA)", city: "Frankfurt", country: "Germany" },
  { code: "AMS", label: "Amsterdam (AMS)", city: "Amsterdam", country: "Netherlands" },
];

type RegisterPayload = { first_name: string; last_name: string; email: string; password: string };
type Recommendation = { origin: string; destination: string; estimated_price: number; currency: string; reason: string };
type AuthMessageProps = { children: ReactNode; variant?: "error" | "success" | "info" };
type PasswordFieldProps = {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  placeholder?: string;
};
type ToastType = "success" | "error" | "warning" | "info";
type ToastItem = { id: number; type: ToastType; message: string };

type FlightSearchCardProps = {
  flight: Flight;
  onFavorite: (flight: Flight) => void;
  isFavorited?: boolean;
  onNotify: (message: string, type?: ToastType) => void;
};

const Protected = ({ children }: { children: JSX.Element }) => (useAuthStore((s) => s.tokens) ? children : <Navigate to="/login" replace />);

function Header({ theme, onToggleTheme, onNotify }: { theme: "light" | "dark"; onToggleTheme: () => void; onNotify: (message: string, type?: ToastType) => void }) {
  const { user, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="topbar">
      <Link to="/" className="brand" onClick={() => setMenuOpen(false)}>
        <span className="brand-mark"><Plane size={18} /></span>
        <span>AI Flight</span>
      </Link>
      <button className="nav-toggle" type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-label="Toggle navigation">
        ☰
      </button>
      <nav className={`nav-links ${menuOpen ? "open" : ""}`}>
        <Link to="/dashboard" onClick={() => setMenuOpen(false)}>Dashboard</Link>
        <Link to="/search" onClick={() => setMenuOpen(false)}>Search</Link>
        <Link to="/favorites" onClick={() => setMenuOpen(false)}>Favorites</Link>
        <Link to="/predict" onClick={() => setMenuOpen(false)}>Price AI</Link>
        <Link to="/recommendations" onClick={() => setMenuOpen(false)}>Discover</Link>
        <Link to="/assistant" onClick={() => setMenuOpen(false)}>Assistant</Link>
        <Link to="/profile" onClick={() => setMenuOpen(false)}>Profile</Link>
        <button className="theme-toggle" type="button" onClick={() => { onToggleTheme(); onNotify("Theme updated", "info"); }} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
          {theme === "dark" ? <SunMedium size={18} /> : <MoonStar size={18} />}
        </button>
        {user ? (
          <button className="ghost-button" onClick={() => { logout(); setMenuOpen(false); onNotify("Signed out", "info"); }} type="button">
            Sign out
          </button>
        ) : (
          <Link className="ghost-button" to="/login" onClick={() => setMenuOpen(false)}>
            Sign in
          </Link>
        )}
      </nav>
    </header>
  );
}

function AuthMessage({ children, variant = "info" }: AuthMessageProps) {
  return <div className={`message ${variant}`} role="status">{children}</div>;
}

function PasswordField({ label, name, value, onChange, autoComplete, placeholder }: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <div className="password-field">
        <input
          name={name}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          type={showPassword ? "text" : "password"}
          autoComplete={autoComplete}
          placeholder={placeholder}
        />
        <button type="button" className="icon-button" onClick={() => setShowPassword((open) => !open)} aria-label={showPassword ? "Hide password" : "Show password"}>
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
    </label>
  );
}

function AirportInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (next: string) => void; placeholder: string }) {
  const normalizedValue = value.toUpperCase();
  const popular = [...airportOptions.filter((item) => ["HYD", "DXB", "DEL", "BOM", "LHR", "SIN", "BKK"].includes(item.code)), ...airportOptions.filter((item) => !["HYD", "DXB", "DEL", "BOM", "LHR", "SIN", "BKK"].includes(item.code))];

  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input aria-label={label} list={`airports-${label.toLowerCase().replace(/\s+/g, "-")}`} value={normalizedValue} placeholder={placeholder} maxLength={3} onChange={(event) => onChange(event.target.value.toUpperCase())} />
      <datalist id={`airports-${label.toLowerCase().replace(/\s+/g, "-")}`}>
        {airportOptions.map((item) => <option key={item.code} value={item.code} label={item.label} />)}
      </datalist>
      <small className="field-hint">Airport, city, country, or IATA code</small>
      <div className="suggestion-row">{popular.slice(0, 4).map((item) => <button key={item.code} className="suggestion-chip" type="button" onClick={() => onChange(item.code)}>{item.code} · {item.city}</button>)}</div>
    </label>
  );
}

function SearchForm({ compact = false, onNotify }: { compact?: boolean; onNotify?: (message: string, type?: ToastType) => void }) {
  const navigate = useNavigate();
  const [origin, setOrigin] = useState("HYD");
  const [destination, setDestination] = useState("DXB");
  const [departure, setDeparture] = useState(today);
  const [travelClass, setTravelClass] = useState("ECONOMY");
  const [adults, setAdults] = useState("1");
  const [children, setChildren] = useState("0");
  const [infants, setInfants] = useState("0");
  const [nonStop, setNonStop] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const originOption = airportOptions.find((item) => item.code === origin.toUpperCase());
    const destinationOption = airportOptions.find((item) => item.code === destination.toUpperCase());
    if (!originOption || !destinationOption) {
      onNotify?.("Please pick a known airport from the suggestions.", "warning");
      return;
    }
    if (origin.toUpperCase() === destination.toUpperCase()) {
      onNotify?.("Origin and destination must be different.", "warning");
      return;
    }
    const params = new URLSearchParams({
      origin: origin.toUpperCase(),
      destination: destination.toUpperCase(),
      departure_date: departure,
      travel_class: travelClass,
      adults,
      children,
      infants,
      non_stop: String(nonStop),
      max_results: "10",
    });
    navigate(`/search?${params.toString()}`);
    onNotify?.("Search submitted", "info");
  };

  return (
    <form className={compact ? "search compact" : "search"} onSubmit={submit}>
      <AirportInput label="From" value={origin} onChange={setOrigin} placeholder="e.g. HYD" />
      <AirportInput label="To" value={destination} onChange={setDestination} placeholder="e.g. DXB" />
      <label className="field">
        <span className="field-label">Departure</span>
        <input aria-label="Departure date" type="date" min={today} value={departure} onChange={(event) => setDeparture(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Travel class</span>
        <select value={travelClass} onChange={(event) => setTravelClass(event.target.value)}>
          <option value="ECONOMY">Economy</option>
          <option value="PREMIUM_ECONOMY">Premium economy</option>
          <option value="BUSINESS">Business</option>
          <option value="FIRST">First</option>
        </select>
      </label>
      <label className="field">
        <span className="field-label">Adults</span>
        <input aria-label="Adults" type="number" min="1" max="9" value={adults} onChange={(event) => setAdults(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Children</span>
        <input aria-label="Children" type="number" min="0" max="9" value={children} onChange={(event) => setChildren(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Infants</span>
        <input aria-label="Infants" type="number" min="0" max="9" value={infants} onChange={(event) => setInfants(event.target.value)} />
      </label>
      <label className="checkbox-row compact">
        <input type="checkbox" checked={nonStop} onChange={(event) => setNonStop(event.target.checked)} />
        <span>Non-stop only</span>
      </label>
      <button className="primary-button" type="submit">Search flights</button>
    </form>
  );
}

function Home({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><Sparkles size={16} /> Predict. Compare. Fly smarter.</p>
          <h1>Every journey starts with a better fare.</h1>
          <p>Search modern routes, compare polished offers, and let the assistant help with the details.</p>
          <SearchForm onNotify={onNotify} />
          <div className="stats">
            <span>AI price forecasts</span>
            <span>Personalised trips</span>
            <span>24/7 travel assistant</span>
          </div>
        </div>
      </section>
      <section className="page-section">
        <div className="section-header">
          <h2>Designed around your next destination</h2>
        </div>
        <div className="grid">
          <article className="card-panel"><h3>Price prediction</h3><small>Know the likely fare before you book.</small></article>
          <article className="card-panel"><h3>Smart recommendations</h3><small>Routes shaped by your history and budget.</small></article>
          <article className="card-panel"><h3>Travel assistant</h3><small>Helpful guidance whenever you need it.</small></article>
        </div>
      </section>
    </>
  );
}

function Login({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState("");

  const login = useMutation({
    mutationFn: (values: { email: string; password: string }) => client.post<Envelope<Tokens>>("/auth/login", values),
    onSuccess: async ({ data }) => {
      setTokens(data.data);
      const me = await client.get<Envelope<User>>("/auth/me");
      setUser(me.data.data);
      onNotify("Signed in successfully", "success");
      navigate("/dashboard");
    },
    onError: (err: unknown) => {
      const responseData = (err as { response?: { data?: { message?: string; error?: string; detail?: string } } }).response?.data;
      const message = responseData?.message || responseData?.error || responseData?.detail || (err instanceof Error ? err.message : "We could not sign you in right now.");
      const normalized = `${message}`.toLowerCase();
      if (normalized.includes("network") || normalized.includes("timeout") || normalized.includes("connect")) {
        setError("We could not reach the server. Please try again in a moment.");
      } else if (normalized.includes("unauthorized") || normalized.includes("invalid email") || normalized.includes("password")) {
        setError("The email or password you entered is incorrect.");
      } else if (normalized.includes("inactive") || normalized.includes("disabled")) {
        setError("This account is currently inactive. Please contact support.");
      } else {
        setError("We could not sign you in right now. Please try again.");
      }
      onNotify("Unable to sign in. Please check your details.", "error");
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    login.mutate({ email: email.trim().toLowerCase(), password });
  };

  return (
    <section className="auth-shell">
      <div className="auth-card">
        <div className="auth-header">
          <div>
            <p className="eyebrow">Welcome back</p>
            <h1>Sign in to continue</h1>
          </div>
          <Link className="inline-link" to="/">
            <HomeIcon size={16} /> Back to home
          </Link>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span className="field-label">Email</span>
            <input name="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" placeholder="name@example.com" />
          </label>
          <PasswordField label="Password" name="password" value={password} onChange={setPassword} autoComplete="current-password" placeholder="Enter your password" />
          <div className="auth-meta">
            <label className="checkbox-row">
              <input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} />
              <span>Remember me</span>
            </label>
            <button type="button" className="inline-link disabled" aria-disabled="true" disabled>
              Forgot password
            </button>
          </div>
          {error ? <AuthMessage variant="error">{error}</AuthMessage> : null}
          <button className="primary-button" type="submit" disabled={login.isPending}>
            {login.isPending ? <><Loader2 size={16} className="spin" /> Signing in…</> : "Sign in"}
          </button>
        </form>
        <div className="auth-footer">
          <span>New here?</span>
          <Link className="inline-link" to="/register">Create an account</Link>
        </div>
      </div>
    </section>
  );
}

function Register({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const navigate = useNavigate();
  const [values, setValues] = useState({ first_name: "", last_name: "", email: "", password: "", confirm_password: "" });
  const [touched, setTouched] = useState({ first_name: false, last_name: false, email: false, password: false, confirm_password: false });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const passwordRequirements = [
    { label: "At least 8 characters", valid: values.password.length >= 8 },
    { label: "One uppercase letter", valid: /[A-Z]/.test(values.password) },
    { label: "One lowercase letter", valid: /[a-z]/.test(values.password) },
    { label: "One number", valid: /\d/.test(values.password) },
    { label: "One special character", valid: /[^A-Za-z0-9]/.test(values.password) },
  ];
  const passwordComplete = passwordRequirements.every((rule) => rule.valid);
  const emailValid = /\S+@\S+\.\S+/.test(values.email);
  const firstNameValid = values.first_name.trim().length >= 2;
  const lastNameValid = values.last_name.trim().length >= 2;
  const passwordsMatch = values.confirm_password.length > 0 && values.password === values.confirm_password;

  const register = useMutation({
    mutationFn: (payload: RegisterPayload) => client.post<Envelope<{ id: string; first_name: string; last_name: string; email: string; is_verified: boolean }>>("/auth/register", payload),
    onSuccess: () => {
      setError("");
      setSuccess("Account created. You can sign in now.");
      onNotify("Account created. You can sign in now.", "success");
      window.setTimeout(() => navigate("/login"), 700);
    },
    onError: (err: unknown) => {
      const responseData = (err as { response?: { data?: { message?: string; error?: string; detail?: string } } }).response?.data;
      const message = responseData?.message || responseData?.error || responseData?.detail || (err instanceof Error ? err.message : "We could not create your account right now.");
      const normalized = `${message}`.toLowerCase();
      if (normalized.includes("already") || normalized.includes("duplicate") || normalized.includes("exists")) {
        setError("An account with this email already exists. Please sign in or use a different email.");
      } else if (normalized.includes("weak") || normalized.includes("password")) {
        setError("Please choose a stronger password that meets all of the requirements below.");
      } else if (normalized.includes("email") || normalized.includes("format")) {
        setError("Please enter a valid email address.");
      } else if (normalized.includes("network") || normalized.includes("timeout") || normalized.includes("connect")) {
        setError("We could not reach the server. Please try again shortly.");
      } else {
        setError("We could not create your account right now. Please try again.");
      }
      setSuccess("");
      onNotify("Registration could not be completed.", "error");
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched({ first_name: true, last_name: true, email: true, password: true, confirm_password: true });
    setError("");
    if (!firstNameValid || !lastNameValid || !emailValid || !passwordComplete) {
      setError("Please complete every required field and satisfy the password requirements.");
      return;
    }
    if (!passwordsMatch) {
      setError("Passwords do not match. Please make sure both entries are identical.");
      return;
    }
    register.mutate({ first_name: values.first_name.trim(), last_name: values.last_name.trim(), email: values.email.trim().toLowerCase(), password: values.password });
  };

  const updateField = (field: keyof typeof values, nextValue: string) => {
    setValues((current) => ({ ...current, [field]: nextValue }));
    setTouched((current) => ({ ...current, [field]: true }));
  };

  return (
    <section className="auth-shell">
      <div className="auth-card">
        <div className="auth-header">
          <div>
            <p className="eyebrow">Create your account</p>
            <h1>Join AI Flight</h1>
          </div>
          <Link className="inline-link" to="/login">
            <HomeIcon size={16} /> Back to login
          </Link>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span className="field-label">First name</span>
            <input name="first_name" required value={values.first_name} onChange={(event) => updateField("first_name", event.target.value)} placeholder="Alex" />
            {touched.first_name && !firstNameValid ? <span className="field-hint error">Please enter at least 2 letters.</span> : null}
          </label>
          <label className="field">
            <span className="field-label">Last name</span>
            <input name="last_name" required value={values.last_name} onChange={(event) => updateField("last_name", event.target.value)} placeholder="Morgan" />
            {touched.last_name && !lastNameValid ? <span className="field-hint error">Please enter at least 2 letters.</span> : null}
          </label>
          <label className="field">
            <span className="field-label">Email</span>
            <input name="email" type="email" required value={values.email} onChange={(event) => updateField("email", event.target.value)} placeholder="name@example.com" autoComplete="email" />
            {touched.email && !emailValid ? <span className="field-hint error">Please enter a valid email address.</span> : null}
          </label>
          <PasswordField label="Password" name="password" value={values.password} onChange={(nextValue) => updateField("password", nextValue)} autoComplete="new-password" placeholder="Create a strong password" />
          <div className="password-rules" aria-live="polite">
            {passwordRequirements.map((rule) => (
              <div key={rule.label} className={`password-rule ${rule.valid ? "valid" : "invalid"}`}>
                <span>{rule.valid ? "✓" : "•"}</span>
                <span>{rule.label}</span>
              </div>
            ))}
          </div>
          <PasswordField label="Confirm password" name="confirm_password" value={values.confirm_password} onChange={(nextValue) => updateField("confirm_password", nextValue)} autoComplete="new-password" placeholder="Repeat your password" />
          {touched.confirm_password && values.confirm_password && !passwordsMatch ? <span className="field-hint error">Passwords do not match.</span> : null}
          {error ? <AuthMessage variant="error">{error}</AuthMessage> : null}
          {success ? <AuthMessage variant="success">{success}</AuthMessage> : null}
          <button className="primary-button" type="submit" disabled={register.isPending}>
            {register.isPending ? <><Loader2 size={16} className="spin" /> Creating account…</> : "Create account"}
          </button>
        </form>
        <div className="auth-footer">
          <span>Already have an account?</span>
          <Link className="inline-link" to="/login">Sign in</Link>
        </div>
      </div>
    </section>
  );
}

function FlightResultCard({ flight, onFavorite, isFavorited = false, onNotify }: FlightSearchCardProps) {
  const airlineName = flight.segments[0]?.airline_name ?? flight.segments[0]?.airline ?? "Airline";
  const airlineCode = flight.segments[0]?.airline ?? "AIR";
  const departureDate = new Date(flight.departure_time);
  const arrivalDate = new Date(flight.arrival_time);
  const durationLabel = flight.duration.replace(/^PT/, "").replace(/H/g, "h ").replace(/M/g, "m");

  return (
    <article className="result-card">
      <div className="result-card-main">
        <div className="result-card-head">
          <div className="airline-badge" aria-hidden="true">{airlineCode.slice(0, 2).toUpperCase()}</div>
          <div>
            <div className="result-title">{airlineName}</div>
            <div className="result-subtitle">{flight.origin} → {flight.destination}</div>
          </div>
          <button className="icon-button" type="button" aria-label="Save flight" onClick={() => onFavorite(flight)}>
            {isFavorited ? <Heart size={18} /> : <HeartOff size={18} />}
          </button>
        </div>
        <div className="route-grid">
          <div className="route-block">
            <span className="route-label">Departure</span>
            <strong>{departureDate.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</strong>
            <small>{flight.origin}</small>
          </div>
          <div className="route-block">
            <span className="route-label">Arrival</span>
            <strong>{arrivalDate.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</strong>
            <small>{flight.destination}</small>
          </div>
        </div>
        <div className="meta-row">
          <span><Clock3 size={14} /> {durationLabel}</span>
          <span><Compass size={14} /> {flight.stops ? `${flight.stops} stop${flight.stops > 1 ? "s" : ""}` : "Non-stop"}</span>
          <span><Wallet size={14} /> {flight.currency} {flight.price.toFixed(2)}</span>
        </div>
        <div className="meta-row compact">
          <span className="pill">{flight.travel_class}</span>
          <span className="pill">{flight.segments[0]?.flight_number ?? "Flight"}</span>
          <span className="pill">Seats available</span>
        </div>
      </div>
      <div className="price-panel">
        <div className="price">{flight.currency} {flight.price.toFixed(2)}</div>
        <div className="price-caption">Per traveler</div>
        <button className="primary-button small" type="button" onClick={() => onNotify("Booking flow will be available in the next sprint.", "info")}>Book</button>
      </div>
    </article>
  );
}

function Search({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const enabled = Boolean(params.get("origin") && params.get("destination") && params.get("departure_date"));
  const query = useQuery({
    queryKey: ["flights", location.search],
    enabled,
    queryFn: async () => {
      const response = await client.get<Envelope<Flight[]> & { count: number; message?: string }>("/flights/search", {
        params: {
          origin: params.get("origin") || undefined,
          destination: params.get("destination") || undefined,
          departure_date: params.get("departure_date") || undefined,
          travel_class: params.get("travel_class") || "ECONOMY",
          adults: Number(params.get("adults") || 1),
          children: Number(params.get("children") || 0),
          infants: Number(params.get("infants") || 0),
          non_stop: params.get("non_stop") === "true" ? true : false,
          currency: "USD",
          max_results: 10,
        },
      });
      return response.data;
    },
  });

  const flights = Array.isArray(query.data?.data) ? query.data.data : [];
  const errorMessage = query.error instanceof Error && "response" in (query.error as { response?: { data?: { message?: string } } })
    ? (query.error as { response?: { data?: { message?: string } } }).response?.data?.message
    : undefined;

  const saveFavorite = useMutation({
    mutationFn: (flight: Flight) => client.post("/flights/favorites", {
      flight_offer_id: flight.flight_id,
      airline: flight.segments[0]?.airline ?? "AIR",
      origin: flight.origin,
      destination: flight.destination,
      departure: flight.departure_time,
      arrival: flight.arrival_time,
      price: flight.price,
      currency: flight.currency,
    }),
    onSuccess: () => {
      onNotify("Saved to your favorites list.", "success");
    },
    onError: () => {
      onNotify("That trip is already in your favorites.", "warning");
    },
  });

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Find a flight</h1>
        <p>Validated airport suggestions, polished cards, and easier booking actions.</p>
      </div>
      <SearchForm compact onNotify={onNotify} />
      {query.isLoading ? (
        <div className="skeleton-list">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      ) : null}
      {query.isError ? <AuthMessage variant="error">{errorMessage ?? "We could not retrieve flights. Please retry."}</AuthMessage> : null}
      {!enabled ? (
        <div className="empty-state">
          <div className="empty-icon"><Compass size={32} /></div>
          <h3>Choose a route to begin</h3>
          <p>Use the quick search above to explore flights from popular airports and curated destinations.</p>
        </div>
      ) : null}
      {!query.isLoading && !query.isError && enabled && flights.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Info size={32} /></div>
          <h3>No results yet</h3>
          <p>Try broadening the search window or switching to another airport.</p>
        </div>
      ) : null}
      <div className="results">
        {flights.map((flight) => (
          <FlightResultCard key={flight.flight_id} flight={flight} onFavorite={() => saveFavorite.mutate(flight)} isFavorited={false} onNotify={onNotify} />
        ))}
      </div>
    </section>
  );
}

function Predict({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const mutation = useMutation({ mutationFn: async (values: object) => (await client.post<Envelope<Prediction>>("/ai/predict-price", values)).data });
  return (
    <section className="page-section">
      <div className="section-header">
        <h1>AI price prediction</h1>
        <p>Estimate fare movement before you finalize your itinerary.</p>
      </div>
      <form className="predict" onSubmit={(event) => {
        event.preventDefault();
        const f = Object.fromEntries(new FormData(event.currentTarget));
        mutation.mutate({ ...f, adults: Number(f.adults), trip_type: "ONE_WAY", cabin_class: "ECONOMY", currency: "USD" });
        onNotify("Prediction requested", "info");
      }}>
        <label className="field">Origin<input name="origin" defaultValue="HYD" maxLength={3} /></label>
        <label className="field">Destination<input name="destination" defaultValue="DXB" maxLength={3} /></label>
        <label className="field">Departure<input name="departure_date" type="date" min={today} defaultValue={today} /></label>
        <label className="field">Adults<input name="adults" type="number" min="1" defaultValue="1" /></label>
        <button className="primary-button" type="submit">Forecast fare</button>
      </form>
      {mutation.data ? <article className="forecast card-panel"><p className="eyebrow">Likely fare</p><h2>{mutation.data.data.currency} {mutation.data.data.predicted_price.toFixed(2)}</h2><p>Range: {mutation.data.data.price_range_low}–{mutation.data.data.price_range_high}</p><p>{mutation.data.data.suggested_booking_window}</p></article> : null}
    </section>
  );
}

function Recommendations() {
  const query = useQuery({
    queryKey: ["recommendations"],
    queryFn: async () => {
      const response = await client.get<Envelope<Recommendation[]>>("/recommendations");
      return response.data;
    },
  });

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Recommended for you</h1>
        <p>Routes shaped by your travel history and preferences.</p>
      </div>
      <div className="grid">
        {(query.data?.data ?? []).map((item, index) => (
          <article className="card-panel" key={index}>
            <h3>{item.origin} → {item.destination}</h3>
            <b>{item.currency} {item.estimated_price.toFixed(2)}</b>
            <p>{item.reason}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Assistant({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  const send = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const text = String(new FormData(form).get("message") || "").trim();
    if (!text) return;
    setMessages((current) => [...current, { role: "user", content: text }]);
    form.reset();
    setLoading(true);
    try {
      const response = await client.post<Envelope<{ reply: string }>>("/assistant/chat", { message: text });
      const reply = response.data.data.reply;
      setDemoMode(reply.toLowerCase().includes("demo mode"));
      setMessages((current) => [...current, { role: "assistant", content: reply }]);
      onNotify("Assistant responded", "info");
    } catch {
      const fallback = "I can help with route ideas, baggage questions, airport guidance, and travel tips. For now I’m running in demo mode so you still get practical guidance without exposing backend errors.";
      setDemoMode(true);
      setMessages((current) => [...current, { role: "assistant", content: fallback }]);
      onNotify("The assistant is using demo guidance.", "warning");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Travel assistant</h1>
        <p>Ask about routes, fares, baggage, or airport guidance.</p>
      </div>
      <div className="assistant-toolbar">
        <span className="pill">24/7 support</span>
        {demoMode ? <span className="pill accent">Demo Mode</span> : null}
      </div>
      <div className="chat">
        {messages.length === 0 ? <p className="chat-empty">Try: “When is the cheapest time to fly to Dubai?”</p> : null}
        {messages.map((message, index) => (
          <p className={message.role} key={index}>{message.content}</p>
        ))}
        {loading ? <p className="chat-loading">Thinking…</p> : null}
      </div>
      <form className="chat-form" onSubmit={send}>
        <input name="message" aria-label="Message" placeholder="Ask about routes, fares, or baggage" required />
        <button className="primary-button" type="submit">{loading ? <Loader2 size={16} className="spin" /> : <SendHorizonal size={16} />}</button>
      </form>
    </section>
  );
}

function Dashboard({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const user = useAuthStore((state) => state.user);
  const favoriteQuery = useQuery({
    queryKey: ["favorites-dashboard"],
    queryFn: async () => {
      const response = await client.get<Envelope<Array<{ origin: string; destination: string; price: number; currency: string }>>>("/flights/favorites", { params: { page: 1, page_size: 4 } });
      return response.data;
    },
  });

  const stats = [
    { label: "Saved trips", value: String(favoriteQuery.data?.data.length ?? 0) },
    { label: "Preferred cabin", value: "Economy" },
    { label: "Smart tip", value: "Book early" },
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
          <SearchForm compact onNotify={onNotify} />
        </article>
        <article className="card-panel">
          <div className="eyebrow"><TrendingUp size={14} /> Price trend</div>
          <div className="metric-list">
            {stats.map((item) => <div key={item.label} className="metric"><strong>{item.value}</strong><span>{item.label}</span></div>)}
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Bookmark size={14} /> Saved flights</div>
          <div className="list-stack">
            {(favoriteQuery.data?.data ?? []).map((item, index) => <div key={index} className="list-item"><span>{item.origin} → {item.destination}</span><strong>{item.currency} {item.price.toFixed(2)}</strong></div>)}
            {favoriteQuery.data?.data.length === 0 ? <div className="message info">No saved flights yet.</div> : null}
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Wind size={14} /> Weather placeholder</div>
          <p>Clear skies and smooth departures for your next trip.</p>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><UserCircle2 size={14} /> Recent activity</div>
          <div className="list-stack">
            <div className="list-item"><span>Airport suggestions used</span><strong>3</strong></div>
            <div className="list-item"><span>AI recommendations viewed</span><strong>2</strong></div>
          </div>
        </article>
      </section>
    </section>
  );
}

function Favorites({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const [query, setQuery] = useState("");
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["favorites"],
    queryFn: async () => {
      const response = await client.get<Envelope<Array<{ id: string; airline: string; origin: string; destination: string; departure: string; arrival: string; price: number; currency: string }>>>("/flights/favorites", { params: { page: 1, page_size: 20 } });
      return response.data;
    },
  });
  const removeFavorite = useMutation({
    mutationFn: async (id: string) => client.delete(`/flights/favorites/${id}`),
    onSuccess: () => {
      refetch();
      onNotify("Favorite removed.", "success");
    },
    onError: () => onNotify("Unable to remove that favorite right now.", "error"),
  });

  const visible = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search) return data?.data ?? [];
    return (data?.data ?? []).filter((item) => `${item.airline} ${item.origin} ${item.destination}`.toLowerCase().includes(search));
  }, [data?.data, query]);

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Favorites</h1>
        <p>Keep the best routes and bargains in one place.</p>
      </div>
      <label className="field search-filter">
        <span className="field-label">Search favorites</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by airline or route" />
      </label>
      {isLoading ? <div className="skeleton-list"><div className="skeleton-card" /></div> : null}
      {!isLoading && visible.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Heart size={32} /></div>
          <h3>No favorites yet</h3>
          <p>Save a flight card from search results to keep it handy.</p>
        </div>
      ) : null}
      <div className="results">
        {visible.map((item) => (
          <article className="result-card" key={item.id}>
            <div className="result-card-main">
              <div className="result-card-head">
                <div className="airline-badge">{item.airline.slice(0, 2).toUpperCase()}</div>
                <div>
                  <div className="result-title">{item.origin} → {item.destination}</div>
                  <div className="result-subtitle">{item.departure} · {item.arrival}</div>
                </div>
              </div>
              <div className="meta-row compact">
                <span className="pill">{item.currency} {item.price.toFixed(2)}</span>
              </div>
            </div>
            <button className="ghost-button" type="button" onClick={() => removeFavorite.mutate(item.id)}>Remove</button>
          </article>
        ))}
      </div>
    </section>
  );
}

function Profile({ theme, onThemeChange, onNotify }: { theme: "light" | "dark"; onThemeChange: (value: "light" | "dark") => void; onNotify: (message: string, type?: ToastType) => void }) {
  const { user, setUser, logout } = useAuthStore();
  const [form, setForm] = useState({ first_name: user?.first_name ?? "", last_name: user?.last_name ?? "", email: user?.email ?? "" });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [preferences, setPreferences] = useState({ currency: "USD", cabin: "ECONOMY", airport: "HYD", theme });

  useEffect(() => {
    setForm({ first_name: user?.first_name ?? "", last_name: user?.last_name ?? "", email: user?.email ?? "" });
  }, [user]);

  const handleSaveProfile = () => {
    if (!user) return;
    setUser({ ...user, first_name: form.first_name, last_name: form.last_name, email: form.email });
    onNotify("Profile updated locally.", "success");
  };

  const handlePassword = () => {
    if (passwords.new_password !== passwords.confirm_password) {
      onNotify("New passwords must match.", "warning");
      return;
    }
    onNotify("Password changes are ready for the next backend endpoint integration.", "info");
  };

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Profile</h1>
        <p>Customize your travel preferences and manage your account.</p>
      </div>
      <div className="dashboard-grid">
        <article className="card-panel">
          <div className="eyebrow"><UserCircle2 size={14} /> User information</div>
          <div className="field-grid">
            <label className="field"><span className="field-label">First name</span><input value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} /></label>
            <label className="field"><span className="field-label">Last name</span><input value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} /></label>
            <label className="field"><span className="field-label">Email</span><input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} /></label>
          </div>
          <div className="cta-row">
            <button className="primary-button" type="button" onClick={handleSaveProfile}>Save profile</button>
            <button className="ghost-button" type="button" onClick={() => { logout(); onNotify("Signed out", "info"); }}>Logout</button>
          </div>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><ShieldCheck size={14} /> Change password</div>
          <div className="field-grid">
            <PasswordField label="Current password" name="current_password" value={passwords.current_password} onChange={(value) => setPasswords((current) => ({ ...current, current_password: value }))} autoComplete="current-password" placeholder="Current password" />
            <PasswordField label="New password" name="new_password" value={passwords.new_password} onChange={(value) => setPasswords((current) => ({ ...current, new_password: value }))} autoComplete="new-password" placeholder="New password" />
            <PasswordField label="Confirm password" name="confirm_password" value={passwords.confirm_password} onChange={(value) => setPasswords((current) => ({ ...current, confirm_password: value }))} autoComplete="new-password" placeholder="Confirm password" />
          </div>
          <button className="primary-button" type="button" onClick={handlePassword}>Update password</button>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Star size={14} /> Travel preferences</div>
          <div className="field-grid">
            <label className="field"><span className="field-label">Preferred currency</span><input value={preferences.currency} onChange={(event) => setPreferences((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} maxLength={3} /></label>
            <label className="field"><span className="field-label">Preferred cabin</span><select value={preferences.cabin} onChange={(event) => setPreferences((current) => ({ ...current, cabin: event.target.value }))}><option value="ECONOMY">Economy</option><option value="BUSINESS">Business</option><option value="FIRST">First</option></select></label>
            <label className="field"><span className="field-label">Preferred airport</span><input value={preferences.airport} onChange={(event) => setPreferences((current) => ({ ...current, airport: event.target.value.toUpperCase() }))} maxLength={3} /></label>
            <label className="field"><span className="field-label">Theme</span><select value={theme} onChange={(event) => onThemeChange(event.target.value as "light" | "dark")}> <option value="light">Light</option><option value="dark">Dark</option></select></label>
          </div>
          <button className="primary-button" type="button" onClick={() => onNotify("Preferences saved locally.", "success")}>Save preferences</button>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Info size={14} /> Account stats</div>
          <div className="metric-list">
            <div className="metric"><strong>{user?.is_verified ? "Verified" : "Pending"}</strong><span>Account status</span></div>
            <div className="metric"><strong>{user?.role ?? "traveller"}</strong><span>Role</span></div>
            <div className="metric"><strong>3</strong><span>Saved trips</span></div>
          </div>
        </article>
      </div>
    </section>
  );
}

export function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    const stored = window.localStorage.getItem("ai-flight-theme");
    return stored === "dark" ? "dark" : "light";
  });
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("ai-flight-theme", theme);
  }, [theme]);

  const pushToast = (message: string, type: ToastType = "info") => {
    const timer = window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== timer));
    }, 3000);
    setToasts((current) => [...current, { id: timer, type, message }]);
  };

  return (
    <>
      <Header theme={theme} onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))} onNotify={pushToast} />
      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => <div key={toast.id} className={`toast ${toast.type}`}><span>{toast.message}</span></div>)}
      </div>
      <main>
        <Routes>
          <Route path="/" element={<Home onNotify={pushToast} />} />
          <Route path="/login" element={<Login onNotify={pushToast} />} />
          <Route path="/register" element={<Register onNotify={pushToast} />} />
          <Route path="/search" element={<Protected><Search onNotify={pushToast} /></Protected>} />
          <Route path="/favorites" element={<Protected><Favorites onNotify={pushToast} /></Protected>} />
          <Route path="/predict" element={<Protected><Predict onNotify={pushToast} /></Protected>} />
          <Route path="/recommendations" element={<Protected><Recommendations /></Protected>} />
          <Route path="/assistant" element={<Protected><Assistant onNotify={pushToast} /></Protected>} />
          <Route path="/dashboard" element={<Protected><Dashboard onNotify={pushToast} /></Protected>} />
          <Route path="/profile" element={<Protected><Profile theme={theme} onThemeChange={(nextTheme) => setTheme(nextTheme)} onNotify={pushToast} /></Protected>} />
        </Routes>
      </main>
      <footer>AI Flight Intelligence · Travel with confidence</footer>
    </>
  );
}
