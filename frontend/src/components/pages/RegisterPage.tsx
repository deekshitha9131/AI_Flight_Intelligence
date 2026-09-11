import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../store/authContext';
import { ApiError } from '../../api/client';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '' });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const update = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register({ email: form.email, password: form.password, first_name: form.firstName || undefined, last_name: form.lastName || undefined });
      navigate('/login', { replace: true });
    } catch (err) {
      const detail = err instanceof ApiError && err.data && typeof err.data === 'object' && 'detail' in err.data ? (err.data as { detail?: string }).detail : undefined;
      setError(detail || (err instanceof Error ? err.message : 'Unable to create your account.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <section className="auth-story"><Link className="brand" to="/login"><span className="brand-mark">✈</span><span><span className="brand-name">AI Flight Intelligence</span><span className="brand-caption">Travel decisions, upgraded</span></span></Link><div className="auth-story-content"><span className="eyebrow">A better starting point</span><h1>Plan with a clearer view.</h1><p>Create a personal flight workspace where every search is easier to understand and every question has somewhere to go.</p></div><div className="auth-statline"><div><strong>Search</strong>real options</div><div><strong>Compare</strong>with ease</div><div><strong>Ask</strong>what matters</div></div></section>
      <section className="auth-form-wrap"><div className="auth-form"><div className="auth-heading"><span className="eyebrow">Get started</span><h2>Create your account</h2><p>A few details and you are ready to explore.</p></div><form onSubmit={handleSubmit}><div className="form-grid"><div className="field"><label htmlFor="first-name">First name</label><input id="first-name" value={form.firstName} onChange={update('firstName')} autoComplete="given-name" required /></div><div className="field"><label htmlFor="last-name">Last name</label><input id="last-name" value={form.lastName} onChange={update('lastName')} autoComplete="family-name" required /></div></div><div className="field"><label htmlFor="register-email">Email address</label><input id="register-email" type="email" value={form.email} onChange={update('email')} autoComplete="email" required /></div><div className="field"><label htmlFor="register-password">Password</label><input id="register-password" type="password" minLength={8} value={form.password} onChange={update('password')} autoComplete="new-password" required /></div>{error && <div className="auth-error" role="alert">{error}</div>}<button className="btn btn-primary" type="submit" disabled={loading}>{loading ? 'Creating account...' : 'Create account'} {!loading && <span aria-hidden="true">→</span>}</button></form><p className="auth-footer">Already have an account? <Link className="auth-link" to="/login">Sign in</Link></p></div></section>
    </div>
  );
};

export default RegisterPage;
