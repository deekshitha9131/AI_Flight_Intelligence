import { Link } from "react-router-dom";
import { MoonStar, Plane, SunMedium } from "lucide-react";
import { useState } from "react";
import { NAVIGATION_LINKS } from "../constants";
import { useAuthStore } from "../store/auth";
import type { ToastType } from "../types";

export function Header({ theme, onToggleTheme, onNotify }: { theme: "light" | "dark"; onToggleTheme: () => void; onNotify: (message: string, type?: ToastType) => void }) {
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
        {NAVIGATION_LINKS.map((link) => (
          <Link key={link.to} to={link.to} onClick={() => setMenuOpen(false)}>{link.label}</Link>
        ))}
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
