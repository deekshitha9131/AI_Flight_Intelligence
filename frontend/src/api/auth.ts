import { api } from './client';
import { setToken } from './client';
import { UserLogin, UserCreate, UserResponse, Token } from '../types/auth';

// Login user
export const login = async (credentials: UserLogin): Promise<Token> => {
  const response = await api.post<Token>('/auth/login', {
    body: credentials,
  });
  setToken(response.access_token);
  return response;
};

// Register user
export const register = async (userData: UserCreate): Promise<UserResponse> => {
  const response = await api.post<UserResponse>('/auth/register', {
    body: userData,
  });
  return response;
};

// Get current user info
export const getCurrentUser = async (): Promise<UserResponse> => {
  const response = await api.get<UserResponse>('/auth/me');
  return response;
};

// Logout (client-side only)
export const logout = () => {
  setToken(null);
};