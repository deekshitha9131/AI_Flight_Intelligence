import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../store/authContext';
import { useTheme } from '../store/themeContext';
import { useState } from 'react';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) {
    return null;
  }

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <NavLink to="/dashboard" className="brand">
          <span className="brand-mark" aria-hidden="true">✈</span>
          <span><span className="brand-name">AI Flight Intelligence</span><span className="brand-caption">Travel decisions, upgraded</span></span>
        </NavLink>
        <div className={`nav-links ${menuOpen ? 'open' : ''}`}>
          <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>Dashboard</NavLink>
          <NavLink to="/flights" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>Flights</NavLink>
          <NavLink to="/predictions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>Predictions</NavLink>
          <NavLink to="/favourites" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>Favourites</NavLink>
          <NavLink to="/recommendations" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>Recommendations</NavLink>
          <NavLink to="/assistant" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>AI Assistant</NavLink>
          <NavLink to="/preferences" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setMenuOpen(false)}>Preferences</NavLink>
        </div>
        <div className="nav-actions">
          <button className="icon-button" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`} title="Toggle theme">{theme === 'light' ? '☾' : '☀'}</button>
          <button className="menu-button" type="button" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle navigation">☰</button>
          <NavLink to="/profile" className="profile-chip" aria-label="Open profile"><span className="avatar">{(user.first_name?.[0] || user.email[0]).toUpperCase()}</span><span className="profile-email">{user.first_name || user.email}</span></NavLink>
          <button className="icon-button" type="button" onClick={logout} aria-label="Log out" title="Log out">↗</button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
