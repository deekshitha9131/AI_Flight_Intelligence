import { apiClient } from "./client";

export interface GmailSyncRequest {
  page_token?: string;
}

export interface GmailSyncResponse {
  // Based on the backend schema
  messages_processed: number;
  messages_saved: number;
  threads_saved: number;
  next_page_token?: string;
}

export interface GmailIncrementalSyncResponse {
  // Based on the backend schema
  messages_processed: number;
  messages_saved: number;
  threads_saved: number;
  history_id: string;
}

export interface GmailSendRequest {
  to: string[];
  subject: string;
  body_text?: string;
  body_html?: string;
  cc?: string[];
  bcc?: string[];
  thread_id?: string;
}

export interface GmailSendResponse {
  message_id: string;
  thread_id: string;
  labels: string[];
}

export async function gmailSync(
  params: GmailSyncRequest = {}
): Promise<GmailSyncResponse> {
  const response = await apiClient.post<GmailSyncResponse>("/gmail/sync", {
    params
  });
  return response.data;
}

export async function gmailIncrementalSync(): Promise<GmailIncrementalSyncResponse> {
  const response = await apiClient.post<GmailIncrementalSyncResponse>("/gmail/sync/incremental");
  return response.data;
}

export async function gmailSend(
  data: GmailSendRequest
): Promise<GmailSendResponse> {
  const response = await apiClient.post<GmailSendResponse>("/gmail/send", {
    data
  });
  return response.data;
}
