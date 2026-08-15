import { ShieldCheck, Star, UserCircle2, Info } from "lucide-react";
import { useEffect, useState, type ChangeEvent } from "react";
import { getCurrentUser, updateCurrentUser } from "../api/auth";
import { PasswordField } from "../components/PasswordField";
import { DEFAULT_CURRENCY, DEFAULT_TRAVEL_CLASS } from "../constants";
import { useAuthStore } from "../store/auth";
import type { ToastType, User } from "../types";

type ProfilePageProps = {
  theme: "light" | "dark";
  onThemeChange: (value: "light" | "dark") => void;
  onNotify: (message: string, type?: ToastType) => void;
};

export function ProfilePage({ theme, onThemeChange, onNotify }: ProfilePageProps) {
  const { user, setUser, logout } = useAuthStore();
  const [form, setForm] = useState({ first_name: user?.first_name ?? "", last_name: user?.last_name ?? "", email: user?.email ?? "" });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [preferences, setPreferences] = useState({ currency: user?.currency_preference ?? DEFAULT_CURRENCY, cabin: user?.preferred_cabin ?? DEFAULT_TRAVEL_CLASS, airport: user?.preferred_airport ?? "HYD" });
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url ?? "");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [notifications, setNotifications] = useState({
    email: user?.notification_settings?.email ?? true,
    push: user?.notification_settings?.push ?? true,
    price_alerts: user?.notification_settings?.price_alerts ?? true,
  });

  useEffect(() => {
    let active = true;
    const loadProfile = async () => {
      if (!user) return;
      setLoading(true);
      setErrorMessage(undefined);
      try {
        const response = await getCurrentUser();
        const nextUser = response.data as User;
        if (!active) return;
        setUser(nextUser);
        setForm({ first_name: nextUser.first_name ?? "", last_name: nextUser.last_name ?? "", email: nextUser.email ?? "" });
        setAvatarPreview(nextUser.avatar_url ?? "");
        setPreferences({
          currency: nextUser.currency_preference ?? DEFAULT_CURRENCY,
          cabin: nextUser.preferred_cabin ?? DEFAULT_TRAVEL_CLASS,
          airport: nextUser.preferred_airport ?? "HYD",
        });
        setNotifications({
          email: nextUser.notification_settings?.email ?? true,
          push: nextUser.notification_settings?.push ?? true,
          price_alerts: nextUser.notification_settings?.price_alerts ?? true,
        });
      } catch (error) {
        if (!active) return;
        setErrorMessage((error as { response?: { data?: { detail?: string; message?: string } } }).response?.data?.detail || (error as { message?: string }).message || "We could not load your profile right now.");
      } finally {
        if (active) setLoading(false);
      }
    };

    loadProfile();
    return () => {
      active = false;
    };
  }, [setUser, user]);

  const handleAvatarUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      const nextValue = typeof reader.result === "string" ? reader.result : "";
      setAvatarPreview(nextValue);
      onNotify("Avatar updated locally.", "success");
    };
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    setSaving(true);
    setErrorMessage(undefined);
    try {
      const payload = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        profile_image: avatarPreview || null,
        preferred_airport: preferences.airport.trim().toUpperCase(),
        preferred_cabin: preferences.cabin,
        currency_preference: preferences.currency.trim().toUpperCase(),
        notification_settings: notifications,
      };
      const response = await updateCurrentUser(payload);
      const nextUser = response.data as User;
      setUser(nextUser);
      onNotify("Profile updated successfully.", "success");
    } catch (error) {
      const message = (error as Error).message || "Unable to save profile changes.";
      setErrorMessage(message);
      onNotify(message, "error");
    } finally {
      setSaving(false);
    }
  };

  const handlePassword = () => {
    if (passwords.new_password !== passwords.confirm_password) {
      onNotify("New passwords must match.", "warning");
      return;
    }
    onNotify("Password changes are handled by the backend auth flow when that endpoint is available.", "info");
  };

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Profile</h1>
        <p>Customize your travel preferences and manage your account.</p>
      </div>
      {loading ? <div className="skeleton-list"><div className="skeleton-card" /></div> : null}
      {errorMessage ? <div className="message error">{errorMessage}</div> : null}
      <div className="dashboard-grid">
        <article className="card-panel">
          <div className="eyebrow"><UserCircle2 size={14} /> Edit profile</div>
          <div className="avatar-uploader">
            {avatarPreview ? <img className="avatar-preview" src={avatarPreview} alt="Profile avatar" /> : <div className="avatar-preview avatar-placeholder">{(form.first_name || user?.first_name || "U").charAt(0).toUpperCase()}</div>}
            <label className="ghost-button avatar-button">
              Upload avatar
              <input type="file" accept="image/*" onChange={handleAvatarUpload} />
            </label>
          </div>
          <div className="field-grid">
            <label className="field"><span className="field-label">First name</span><input value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} /></label>
            <label className="field"><span className="field-label">Last name</span><input value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} /></label>
            <label className="field"><span className="field-label">Email</span><input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} /></label>
          </div>
          <div className="cta-row">
            <button className="primary-button" type="button" onClick={handleSaveProfile} disabled={saving}>{saving ? "Saving..." : "Save profile"}</button>
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
          <button className="primary-button" type="button" onClick={handleSaveProfile} disabled={saving}>{saving ? "Saving..." : "Save preferences"}</button>
        </article>
        <article className="card-panel">
          <div className="eyebrow"><Info size={14} /> Notification settings</div>
          <div className="toggle-stack">
            <label className="checkbox-row full-width"><input type="checkbox" checked={notifications.email} onChange={(event) => setNotifications((current) => ({ ...current, email: event.target.checked }))} /><span>Email updates</span></label>
            <label className="checkbox-row full-width"><input type="checkbox" checked={notifications.push} onChange={(event) => setNotifications((current) => ({ ...current, push: event.target.checked }))} /><span>Push notifications</span></label>
            <label className="checkbox-row full-width"><input type="checkbox" checked={notifications.price_alerts} onChange={(event) => setNotifications((current) => ({ ...current, price_alerts: event.target.checked }))} /><span>Price alerts</span></label>
          </div>
          <button className="primary-button" type="button" onClick={handleSaveProfile} disabled={saving}>{saving ? "Saving..." : "Save notifications"}</button>
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
