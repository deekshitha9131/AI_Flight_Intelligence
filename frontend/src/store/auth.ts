import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Tokens, User } from "../types";
type State = { user: User | null; tokens: Tokens | null; setTokens: (tokens: Tokens) => void; setUser: (user: User | null) => void; logout: () => void };
export const useAuthStore = create<State>()(persist((set) => ({ user: null, tokens: null, setTokens: (tokens) => set({ tokens }), setUser: (user) => set({ user }), logout: () => set({ user: null, tokens: null }) }), { name: "ai-flight-auth" }));
