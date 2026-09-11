import { api } from './client';
import { PreferenceCreate, PreferenceInDB } from '../types/preference';

// Get current user's preferences
export const getPreferences = async (): Promise<PreferenceInDB> => {
  const response = await api.get<PreferenceInDB>('/preferences/');
  return response;
};

// Create or update current user's preferences
export const updatePreferences = async (
  preferences: PreferenceCreate
): Promise<PreferenceInDB> => {
  const response = await api.put<PreferenceInDB>('/preferences/', {
    body: preferences,
  });
  return response;
};

