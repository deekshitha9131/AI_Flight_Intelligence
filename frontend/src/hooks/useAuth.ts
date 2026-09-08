import { useCallback, useEffect, useState } from "react";

import { getSession, logout as apiLogout } from "@/api/auth";
import type { User } from "@/types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface UseAuthResult {
  status: AuthStatus;
  user: User | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export function useAuth(): UseAuthResult {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      const sessionUser = await getSession();
      setUser(sessionUser);
      setStatus("authenticated");
    } catch {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return { status, user, refresh, logout };
}