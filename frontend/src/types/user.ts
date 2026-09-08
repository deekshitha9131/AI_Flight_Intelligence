export type UserStatus = "active" | "inactive";

export interface User {
  id: string;
  email: string;
  full_name: string;
  status: UserStatus;
  created_at: string;
  updated_at: string;
}