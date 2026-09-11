import { api } from './client';
import {
  PredictionRequest,
  PredictionResponse,
  PredictionResponseWithID,
} from '../types/prediction';

// Create a prediction for a flight
export const createPrediction = async (
  predictionRequest: PredictionRequest,
  flightSearchId: string
): Promise<PredictionResponse> => {
  const response = await api.post<PredictionResponse>(
    `/predictions/?flight_search_id=${flightSearchId}`,
    {
      body: predictionRequest,
    }
  );
  return response;
};

// Get prediction service info
export const getPredictionServiceInfo = async (): Promise<unknown> => {
  const response = await api.get<unknown>('/predictions/');
  return response;
};

// Get prediction history for the current user
export const getPredictionHistory = async (): Promise<PredictionResponseWithID[]> => {
  const response = await api.get<PredictionResponseWithID[]>('/predictions/history');
  return response;
};

