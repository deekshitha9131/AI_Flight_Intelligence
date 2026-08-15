import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

type PasswordFieldProps = {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  placeholder?: string;
};

export function PasswordField({ label, name, value, onChange, autoComplete, placeholder }: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <div className="password-field">
        <input
          name={name}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          type={showPassword ? "text" : "password"}
          autoComplete={autoComplete}
          placeholder={placeholder}
        />
        <button type="button" className="icon-button" onClick={() => setShowPassword((open) => !open)} aria-label={showPassword ? "Hide password" : "Show password"}>
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
    </label>
  );
}
