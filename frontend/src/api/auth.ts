import client from "./client";
import { useAuthStore } from "../store/auth";
import type { Envelope, Tokens, User } from "../types";

export interface UpdateProfilePayload {
  first_name?: string;
  last_name?: string;
  profile_image?: string | null;
  preferred_airport?: string;
  preferred_cabin?: string;
  currency_preference?: string;
  notification_settings?: Record<string, boolean>;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}

export async function login(payload: LoginPayload): Promise<{ tokens: Tokens; user: User }> {
  const authResponse = await client.post<Envelope<Tokens>>("/auth/login", payload);
  const tokens = authResponse.data.data;

  // Immediately store tokens so request interceptors and store state have access
  useAuthStore.getState().setTokens(tokens);

  try {
    const profileResponse = await client.get<Envelope<User>>("/auth/me", {
      headers: {
        Authorization: `Bearer ${tokens.access_token}`,
      },
    });
    return {
      tokens,
      user: profileResponse.data.data,
    };
  } catch {
    const fallbackUser: User = {
      id: "authenticated",
      first_name: "User",
      last_name: "",
      email: payload.email,
      role: "user",
      is_verified: true,
    };
    return {
      tokens,
      user: fallbackUser,
    };
  }
}



export async function register(payload: RegisterPayload) {
  const response = await client.post<Envelope<{ id: string; first_name: string; last_name: string; email: string; is_verified: boolean }>>("/auth/register", payload);
  console.log("register response.status", response.status);
  console.log("register response.data", response.data);
  return response;
}

export async function getCurrentUser() {
  const response = await client.get<Envelope<User>>("/auth/me");
  return response.data;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export async function updateCurrentUser(payload: UpdateProfilePayload) {
  const response = await client.put<Envelope<User>>("/auth/me", payload);
  return response.data;
}

export async function changePassword(payload: ChangePasswordPayload) {
  const response = await client.post<Envelope<null>>("/auth/change-password", payload);
  return response.data;
}
