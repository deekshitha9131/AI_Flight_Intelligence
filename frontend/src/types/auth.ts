// Since we cannot import from backend (different project), we'll replicate the types here.
// However, we can also generate types from backend schemas if needed, but for simplicity we'll define them.

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserCreate extends Omit<UserLogin, 'password'> {
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface UserResponse {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  created_at: string; // ISO string
  updated_at?: string; // ISO string
}

export interface Token {
  access_token: string;
  token_type: string;
}
