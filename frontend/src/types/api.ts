export interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
  count?: number;
}

export interface ApiErrorResponse {
  message?: string;
  error?: string;
  detail?: string;
}
