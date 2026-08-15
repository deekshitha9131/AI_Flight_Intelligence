import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Tokens, User } from "../types";

type State = {
  user: User | null;
  tokens: Tokens | null;
  isHydrated: boolean;
  setTokens: (tokens: Tokens | null) => void;
  setUser: (user: User | null) => void;
  setAuth: (auth: { tokens: Tokens; user: User }) => void;
  logout: () => void;
  setHydrated: (value: boolean) => void;
};

export const useAuthStore = create<State>()(
  persist(
    (set) => ({
      user: null,
      tokens: null,
      isHydrated: false,
      setTokens: (tokens) => set({ tokens }),
      setUser: (user) => set({ user }),
      setAuth: ({ tokens, user }) => set({ tokens, user }),
      logout: () => set({ user: null, tokens: null }),
      setHydrated: (value) => set({ isHydrated: value }),
    }),
    {
      name: "ai-flight-auth",
      partialize: (state) => ({ user: state.user, tokens: state.tokens }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
      },
    },
  ),
);
