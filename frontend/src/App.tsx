import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './store/authContext';
import ProtectedRoutes from './components/ProtectedRoutes';
import LoginPage from './components/pages/LoginPage';
import RegisterPage from './components/pages/RegisterPage';
import FlightsPage from './components/pages/FlightsPage';
import AssistantPage from './components/pages/AssistantPage';
import PreferencesPage from './components/pages/PreferencesPage';
import DashboardPage from './components/pages/DashboardPage';
import PredictionsPage from './components/pages/PredictionsPage';
import RecommendationsPage from './components/pages/RecommendationsPage';
import ProfilePage from './components/pages/ProfilePage';
import FavouritesPage from './components/pages/FavouritesPage';
import { useAuth } from './store/authContext';
import { ThemeProvider } from './store/themeContext';

// Home route - redirect based on auth status
const Home: React.FC = () => {
  const { user } = useAuth();
  // If user is logged in, go to flights, else go to login
  if (user) {
    return <Navigate to="/dashboard" replace />;
  } else {
    return <Navigate to="/login" replace />;
  }
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboard" element={<ProtectedRoutes><DashboardPage /></ProtectedRoutes>} />
            <Route path="/flights" element={<ProtectedRoutes><FlightsPage /></ProtectedRoutes>} />
            <Route path="/predictions" element={<ProtectedRoutes><PredictionsPage /></ProtectedRoutes>} />
            <Route path="/favourites" element={<ProtectedRoutes><FavouritesPage /></ProtectedRoutes>} />
            <Route path="/recommendations" element={<ProtectedRoutes><RecommendationsPage /></ProtectedRoutes>} />
            <Route path="/assistant" element={<ProtectedRoutes><AssistantPage /></ProtectedRoutes>} />
            <Route path="/preferences" element={<ProtectedRoutes><PreferencesPage /></ProtectedRoutes>} />
            <Route path="/profile" element={<ProtectedRoutes><ProfilePage /></ProtectedRoutes>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
