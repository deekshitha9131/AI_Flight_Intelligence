import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";

interface RedirectIfAuthenticatedProps {
  children: ReactNode;
}

function RedirectIfAuthenticated({ children }: RedirectIfAuthenticatedProps) {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

export default RedirectIfAuthenticated;