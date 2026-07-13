import axios from "axios";
import { useAuthStore } from "../store/auth";
const client = axios.create({ baseURL: `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`, timeout: 20_000 });
client.interceptors.request.use((config) => { const token = useAuthStore.getState().tokens?.access_token; if (token) config.headers.Authorization = `Bearer ${token}`; return config; });
client.interceptors.response.use((response) => response, async (error) => { const original = error.config; const refresh = useAuthStore.getState().tokens?.refresh_token; if (error.response?.status === 401 && refresh && !original._retry) { original._retry = true; try { const response = await axios.post(`${client.defaults.baseURL}/auth/refresh`, { refresh_token: refresh }); useAuthStore.getState().setTokens(response.data.data); return client(original); } catch { useAuthStore.getState().logout(); } } return Promise.reject(error); });
export default client;
