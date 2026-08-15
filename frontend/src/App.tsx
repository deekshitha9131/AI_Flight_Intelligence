import { useEffect, useState, type ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getCurrentUser } from "./api/auth";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Header } from "./components/Header";
import { PageState } from "./components/PageState";
import { useNotifications } from "./hooks/useNotifications";
import { AssistantPage } from "./pages/AssistantPage";
import { BookingConfirmationPage } from "./pages/BookingConfirmationPage";
import { BookingPage } from "./pages/BookingPage";
import { BookingsPage } from "./pages/BookingsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FavoritesPage } from "./pages/FavoritesPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { PredictPage } from "./pages/PredictPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SearchPage } from "./pages/SearchPage";
import { useAuthStore } from "./store/auth";

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

const Protected = ({ children }: { children: ReactElement }) => {
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const tokens = useAuthStore((s) => s.tokens);

  if (!isHydrated) {
    return <PageState title="Loading" description="Authenticating..." variant="loading" />;
  }

  return tokens ? children : <Navigate to="/login" replace />;
};


export function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    const stored = window.localStorage.getItem("ai-flight-theme");
    return stored === "dark" ? "dark" : "light";
  });
  const { toasts, pushToast } = useNotifications();
  const tokens = useAuthStore((state) => state.tokens);
  const user = useAuthStore((state) => state.user);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const setAuth = useAuthStore((state) => state.setAuth);
  const logout = useAuthStore((state) => state.logout);
  const [routeLoading, setRouteLoading] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("ai-flight-theme", theme);
  }, [theme]);

  useEffect(() => {
    const handleStart = () => setRouteLoading(true);
    const handleStop = () => setRouteLoading(false);
    window.addEventListener("beforeunload", handleStart);
    window.addEventListener("load", handleStop);
    return () => {
      window.removeEventListener("beforeunload", handleStart);
      window.removeEventListener("load", handleStop);
    };
  }, []);

  useEffect(() => {
    if (!isHydrated || !tokens || user) return;

    let cancelled = false;

    getCurrentUser()
      .then((response) => {
        if (!cancelled && response?.data) {
          setAuth({ tokens, user: response.data });
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const status = (err as { response?: { status?: number } })?.response?.status;
          if (status === 401) {
            logout();
            if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/register")) {
              window.location.assign("/login");
            }
          }
        }
      });


    return () => {
      cancelled = true;
    };
  }, [isHydrated, tokens, user, setAuth, logout]);

  return (
    <>
      <Header theme={theme} onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))} onNotify={pushToast} />
      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => <div key={toast.id} className={`toast ${toast.type}`}><span>{toast.message}</span></div>)}
      </div>
      {routeLoading ? <PageState title="Loading" description="Preparing the next view for you." variant="loading" /> : null}
      <main>
        <ErrorBoundary>
        <Routes>
          <Route path="/" element={<HomePage airportOptions={airportOptions} today={today} onNotify={pushToast} />} />
          <Route path="/login" element={<LoginPage onNotify={pushToast} />} />
          <Route path="/register" element={<RegisterPage onNotify={pushToast} />} />
          <Route path="/search" element={<Protected><SearchPage airportOptions={airportOptions} today={today} onNotify={pushToast} /></Protected>} />
          <Route path="/favorites" element={<Protected><FavoritesPage onNotify={pushToast} /></Protected>} />
          <Route path="/predict" element={<Protected><PredictPage today={today} onNotify={pushToast} /></Protected>} />
          <Route path="/recommendations" element={<Protected><RecommendationsPage /></Protected>} />
          <Route path="/assistant" element={<Protected><AssistantPage onNotify={pushToast} /></Protected>} />
          <Route path="/dashboard" element={<Protected><DashboardPage today={today} airportOptions={airportOptions} onNotify={pushToast} /></Protected>} />
          <Route path="/bookings" element={<Protected><BookingsPage /></Protected>} />
          <Route path="/booking/:flightId" element={<Protected><BookingPage onNotify={pushToast} /></Protected>} />
          <Route path="/booking/:flightId/confirm" element={<Protected><BookingConfirmationPage /></Protected>} />
          <Route path="/profile" element={<Protected><ProfilePage theme={theme} onThemeChange={(nextTheme) => setTheme(nextTheme)} onNotify={pushToast} /></Protected>} />
          <Route path="/403" element={<ForbiddenPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
        </ErrorBoundary>
      </main>
      <footer>AI Flight Intelligence · Travel with confidence</footer>
    </>
  );
}
