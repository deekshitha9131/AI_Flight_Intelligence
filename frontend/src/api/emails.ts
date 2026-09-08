import type { AIUnderstandingResult, EmailDetail, EmailSummary, PaginatedResponse } from "@/types";

import { apiClient } from "./client";

export interface ListEmailsParams {
  page?: number;
  page_size?: number;
  sort?: "newest" | "oldest";
  unread?: boolean;
  starred?: boolean;
  has_attachments?: boolean;
}

export async function listEmails(
  params: ListEmailsParams = {},
): Promise<PaginatedResponse<EmailSummary>> {
  const response = await apiClient.get<PaginatedResponse<EmailSummary>>("/emails", { params });
  return response.data;
}

export interface SearchEmailsParams {
  q: string;
  page?: number;
  page_size?: number;
}

export async function searchEmails(
  params: SearchEmailsParams,
): Promise<PaginatedResponse<EmailSummary>> {
  const response = await apiClient.get<PaginatedResponse<EmailSummary>>("/emails/search", { params });
  return response.data;
}

export async function getEmail(emailId: string): Promise<EmailDetail> {
  const response = await apiClient.get<EmailDetail>(`/emails/${emailId}`);
  return response.data;
}

export async function analyzeEmail(emailId: string): Promise<AIUnderstandingResult> {
  const response = await apiClient.post<AIUnderstandingResult>(`/emails/${emailId}/analyze`);
  return response.data;
}

export interface GenerateEmailContentRequest {
  to: string;
  subject: string;
  body: string;
  instructions: string;
}

export interface GeneratedEmailContent {
  subject: string;
  body: string;
}

export async function generateEmailContent(
  params: GenerateEmailContentRequest,
): Promise<GeneratedEmailContent> {
  const response = await apiClient.post<GeneratedEmailContent>("/emails/generate", null, { params });
  return response.data;
}