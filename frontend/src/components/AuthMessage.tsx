import type { ReactNode } from "react";

type AuthMessageProps = { children: ReactNode; variant?: "error" | "success" | "info" };

export function AuthMessage({ children, variant = "info" }: AuthMessageProps) {
  return <div className={`message ${variant}`} role="status">{children}</div>;
}
