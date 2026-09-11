import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../store/authContext';
import { ApiError } from '../../api/client';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status >= 500) {
        setError('The authentication service is temporarily unavailable. Please try again shortly.');
        return;
      }
      const detail = err instanceof ApiError && err.data && typeof err.data === 'object' && 'detail' in err.data
        ? (err.data as { detail?: string }).detail
        : undefined;
      setError(detail || (err instanceof Error ? err.message : 'Unable to sign in. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <section className="auth-story">
        <Link className="brand" to="/login"><span className="brand-mark">✈</span><span><span className="brand-name">AI Flight Intelligence</span><span className="brand-caption">Travel decisions, upgraded</span></span></Link>
        <div className="auth-story-content"><span className="eyebrow">Intelligence for the journey</span><h1>Find the route that feels right.</h1><p>Bring search, comparison, preferences, and conversational guidance into one considered flight workspace.</p></div>
        <div className="auth-statline"><div><strong>Live</strong>flight search</div><div><strong>AI</strong>travel context</div><div><strong>1</strong>calmer workflow</div></div>
      </section>
      <section className="auth-form-wrap"><div className="auth-form">
        <div className="auth-heading"><span className="eyebrow">Welcome back</span><h2>Sign in to continue</h2><p>Your next trip starts with better information.</p></div>
        <form onSubmit={handleSubmit}>
          <div className="field"><label htmlFor="email">Email address</label><input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></div>
          <div className="field"><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></div>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'} {!loading && <span aria-hidden="true">→</span>}</button>
        </form>
        <p className="auth-footer">New to the platform? <Link className="auth-link" to="/register">Create an account</Link></p>
      </div></section>
    </div>
  );
};

export default LoginPage;
