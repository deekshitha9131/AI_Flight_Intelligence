// Base API client with token management
let token: string | null = null;

export const setToken = (newToken: string | null) => {
  token = newToken;
  if (newToken) {
    localStorage.setItem('access_token', newToken);
  } else {
    localStorage.removeItem('access_token');
  }
};

export const getToken = (): string | null => {
  if (token) return token;
  const stored = localStorage.getItem('access_token');
  if (stored) {
    token = stored;
    return stored;
  }
  return null;
};

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: object;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const readResponseBody = async (response: Response): Promise<unknown> => {
  if (response.status === 204) return undefined;
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
};

const getErrorMessage = (data: unknown, fallback: string) => {
  if (typeof data === 'object' && data !== null) {
    if ('detail' in data && typeof data.detail === 'string') return data.detail;
    if ('message' in data && typeof data.message === 'string') return data.message;
  }
  if (typeof data === 'string' && data.trim()) return data;
  return fallback;
};

const isPublicAuthRequest = (endpoint: string) =>
  endpoint === '/auth/login' || endpoint === '/auth/register';

const clearUnauthorizedSession = (endpoint: string, status: number) => {
  if (status !== 401 || isPublicAuthRequest(endpoint)) return;
  token = null;
  localStorage.removeItem('access_token');
  window.dispatchEvent(new Event('auth:expired'));
};

const request = async <T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> => {
  const url = `${import.meta.env.VITE_API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const authToken = isPublicAuthRequest(endpoint) ? null : getToken();
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const config: RequestInit = {
    method: options.method ?? 'GET',
    headers,
  };

  if (options.body !== undefined) {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, config);

  const data = await readResponseBody(response);

  if (!response.ok) {
    clearUnauthorizedSession(endpoint, response.status);
    throw new ApiError(
      response.status,
      getErrorMessage(data, response.statusText || 'An error occurred'),
      data
    );
  }

  return data as T;
};

const requestWithResponse = async <T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<{ data: T; response: Response }> => {
  const url = `${import.meta.env.VITE_API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const authToken = isPublicAuthRequest(endpoint) ? null : getToken();
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const config: RequestInit = {
    method: options.method ?? 'GET',
    headers,
  };

  if (options.body !== undefined) {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, config);

  const data = await readResponseBody(response);

  if (!response.ok) {
    clearUnauthorizedSession(endpoint, response.status);
    throw new ApiError(
      response.status,
      getErrorMessage(data, response.statusText || 'An error occurred'),
      data
    );
  }

  return { data: data as T, response };
};

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { method: 'GET', ...options }),
  post: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { method: 'POST', ...options }),
  put: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { method: 'PUT', ...options }),
  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { method: 'DELETE', ...options }),
  patch: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { method: 'PATCH', ...options }),
  postWithResponse: <T>(endpoint: string, options?: RequestOptions) =>
    requestWithResponse<T>(endpoint, { method: 'POST', ...options }),
};

export default api;