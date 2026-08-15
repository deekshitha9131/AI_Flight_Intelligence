import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Home as HomeIcon, Loader2 } from "lucide-react";
import { register as registerRequest } from "../api/auth";
import { AuthMessage } from "../components/AuthMessage";
import { PasswordField } from "../components/PasswordField";
import type { ToastType } from "../types";

interface RegisterPayload { first_name: string; last_name: string; email: string; password: string }

export type RegisterPageProps = {
  onNotify: (message: string, type?: ToastType) => void;
};

export function RegisterPage({ onNotify }: RegisterPageProps) {
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
    mutationFn: (payload: RegisterPayload) => registerRequest(payload),
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

  const updateField = (field: keyof typeof values, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
    setTouched((current) => ({ ...current, [field]: true }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched({ first_name: true, last_name: true, email: true, password: true, confirm_password: true });
    if (!firstNameValid || !lastNameValid || !emailValid || !passwordComplete || !passwordsMatch) {
      return;
    }
    register.mutate({ first_name: values.first_name.trim(), last_name: values.last_name.trim(), email: values.email.trim().toLowerCase(), password: values.password });
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
