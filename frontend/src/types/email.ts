export interface AttachmentSummary {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
}

export interface EmailSummary {
  id: string;
  gmail_message_id: string;
  thread_id: string;
  sender: string;
  subject: string | null;
  snippet: string;
  received_at: string;
  is_read: boolean;
  is_starred: boolean;
  has_attachments: boolean;
}

export interface EmailDetail extends EmailSummary {
  recipients: string[];
  cc: string[];
  bcc: string[];
  body_text: string | null;
  body_html: string | null;
  label_ids: string[];
  attachments: AttachmentSummary[];
}

export interface AIUnderstandingResult {
  category: string;
  intent: string;
  urgency: string;
  sentiment: string;
  entities: Array<{ type: string; value: string }>;
  summary: string;
  confidence: number;
}