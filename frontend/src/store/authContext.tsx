import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { login as apiLogin, register as apiRegister, getCurrentUser as apiGetCurrentUser } from '../api/auth';
import { setToken as setApiToken } from '../api/client';
import { UserResponse, Token } from '../types/auth';

interface AuthContextProps {
  user: UserResponse | null;
  token: string | null;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  register: (userData: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => Promise<void>;
  logout: () => void;
  getCurrentUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextProps | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setAuthToken] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const skipTokenValidation = useRef(false);

  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      setApiToken(storedToken);
      setAuthToken(storedToken);
    } else {
      setIsInitializing(false);
    }
  }, []);

  useEffect(() => {
    const handleExpiredSession = () => {
      setApiToken(null);
      setAuthToken(null);
      setUser(null);
      setIsInitializing(false);
    };

    window.addEventListener('auth:expired', handleExpiredSession);
    return () => window.removeEventListener('auth:expired', handleExpiredSession);
  }, []);

  const login = async (credentials: { email: string; password: string }) => {
    try {
      const response = await apiLogin(credentials);
      setApiToken(response.access_token);
      const userInfo = await apiGetCurrentUser();
      setUser(userInfo);
      skipTokenValidation.current = true;
      setAuthToken(response.access_token);
    } catch (error) {
      setApiToken(null);
      setAuthToken(null);
      setUser(null);
      throw error;
    }
  };

  const register = async (userData: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => {
    try {
      const response = await apiRegister(userData);
      // Optionally log in after registration
      // await login({ email: userData.email, password: userData.password });
      return response;
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    setApiToken(null);
    setAuthToken(null);
    setUser(null);
  };

  const getCurrentUser = async () => {
    if (!token) return;
    try {
      const userInfo = await apiGetCurrentUser();
      setUser(userInfo);
    } catch (error) {
      // If token is invalid, logout
      logout();
      throw error;
    }
  };

  // If we have a token, try to get the user info
  useEffect(() => {
    if (token) {
      if (skipTokenValidation.current) {
        skipTokenValidation.current = false;
        return;
      }
      getCurrentUser().catch(() => {
        logout();
      }).finally(() => setIsInitializing(false));
    }
  }, [token]);

  return (
    <AuthContext.Provider
      value={{ user, token, login, register, logout, getCurrentUser }}
    >
      {!isInitializing && children}
    </AuthContext.Provider>
  );
};
