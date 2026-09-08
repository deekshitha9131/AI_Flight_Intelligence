import type { EmailDetail } from "./email";

export interface ThreadSummary {
  id: string;
  gmail_thread_id: string;
  subject: string | null;
  snippet: string | null;
  updated_at: string;
  email_count: number;
}

export interface ThreadDetail {
  id: string;
  gmail_thread_id: string;
  subject: string | null;
  snippet: string | null;
  created_at: string;
  updated_at: string;
  emails: EmailDetail[];
}