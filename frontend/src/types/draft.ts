export type DraftStatus = "generated" | "approved" | "rejected" | "sent";

export interface Draft {
  id: string;
  email_id: string;
  body: string;
  status: DraftStatus;
  created_at: string;
  updated_at: string;
}

export interface DraftCreateRequest {
  email_id: string;
  instructions?: string | null;
}

export interface DraftUpdateRequest {
  body: string;
}