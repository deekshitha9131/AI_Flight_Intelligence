import axios from "axios";
import { useAuthStore } from "../store/auth";

const apiBaseUrl = import.meta.env.VITE_API_URL?.trim();
const resolvedBaseUrl = apiBaseUrl && apiBaseUrl !== "/"
  ? apiBaseUrl.replace(/\/$/, "")
  : "";
const client = axios.create({ baseURL: resolvedBaseUrl ? `${resolvedBaseUrl}/api/v1` : "/api/v1", timeout: 20_000 });

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().tokens?.access_token;
  if (token) {
    if (config.headers && typeof config.headers.set === "function") {
      config.headers.set("Authorization", `Bearer ${token}`);
    } else {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});


client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const refreshToken = useAuthStore.getState().tokens?.refresh_token;

    // Attempt token refresh on 401 for authenticated requests with a refresh token
    if (error.response?.status === 401 && refreshToken && !original._retry) {
      original._retry = true;
      try {
        const response = await axios.post(`${client.defaults.baseURL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const nextTokens = response.data.data;
        useAuthStore.getState().setTokens(nextTokens);
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${nextTokens.access_token}`;
        return client(original);
      } catch (refreshErr) {
        useAuthStore.getState().logout();
        if (
          typeof window !== "undefined" &&
          !window.location.pathname.startsWith("/login") &&
          !window.location.pathname.startsWith("/register")
        ) {
          window.location.assign("/login");
        }
        return Promise.reject(refreshErr);
      }
    }

    // Only force logout redirect for non-auth-flow routes when an authenticated request is unhandleable
    const requestUrl = original?.url || "";
    const isAuthRoute = requestUrl.includes("/auth/login") || requestUrl.includes("/auth/register");

    if (error.response?.status === 401 && !isAuthRoute && original._retry) {
      useAuthStore.getState().logout();
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/login") &&
        !window.location.pathname.startsWith("/register")
      ) {
        window.location.assign("/login");
      }
    }

    return Promise.reject(error);
  },
);


export default client;
