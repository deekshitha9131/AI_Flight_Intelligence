export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiFieldError {
  field: string;
  issue: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    request_id: string;
    fields?: ApiFieldError[];
  };
}