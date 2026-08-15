import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Home as HomeIcon, Loader2 } from "lucide-react";
import { login as loginRequest } from "../api/auth";
import { AuthMessage } from "../components/AuthMessage";
import { PasswordField } from "../components/PasswordField";
import { useAuthStore } from "../store/auth";
import type { ToastType } from "../types";

export type LoginPageProps = {
  onNotify: (message: string, type?: ToastType) => void;
};

export function LoginPage({ onNotify }: LoginPageProps) {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState("");

  const login = useMutation({
    mutationFn: (values: { email: string; password: string }) => loginRequest(values),
    onSuccess: ({ tokens, user }) => {
      setAuth({ tokens, user });
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
