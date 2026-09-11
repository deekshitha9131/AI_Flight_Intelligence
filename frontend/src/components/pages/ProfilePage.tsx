import React from 'react';
import { useAuth } from '../../store/authContext';
import { useTheme } from '../../store/themeContext';

const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  if (!user) return null;
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Flight intelligence traveler';
  const memberSince = new Date(user.created_at).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  return <div className="page-stack">
    <header className="page-header"><div><span className="eyebrow">Account</span><h1 className="page-title">Your profile.</h1><p className="page-subtitle">A clear view of the account connected to your flight workspace.</p></div></header>
    <section className="settings-grid">
      <div className="surface surface-pad" style={{ background: 'var(--accent-soft)' }}><span className="avatar" style={{ width: 58, height: 58, fontSize: 22 }}>{(user.first_name?.[0] || user.email[0]).toUpperCase()}</span><h2 className="section-title" style={{ marginTop: 20 }}>{displayName}</h2><p className="section-note">{user.email}</p><span className="badge" style={{ marginTop: 18 }}>{user.is_active ? 'Active account' : 'Inactive account'}</span></div>
      <div className="surface surface-pad"><span className="eyebrow">Account details</span><div className="capability-list"><div className="capability"><span className="capability-mark">@</span><div><strong>Email address</strong><span>{user.email}</span></div></div><div className="capability"><span className="capability-mark">ID</span><div><strong>Member since</strong><span>{memberSince}</span></div></div><div className="capability"><span className="capability-mark">◐</span><div><strong>Appearance</strong><span>{theme === 'dark' ? 'Dark theme' : 'Light theme'}</span></div></div></div><div className="form-actions"><button className="btn btn-outline" type="button" onClick={toggleTheme}>Use {theme === 'dark' ? 'light' : 'dark'} theme</button><button className="btn btn-ghost btn-danger" type="button" onClick={logout}>Log out</button></div></div>
    </section>
  </div>;
};

export default ProfilePage;
