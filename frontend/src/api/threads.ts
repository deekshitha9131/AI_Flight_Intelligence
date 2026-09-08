import { apiClient } from "./client";
import type { PaginatedResponse, ThreadDetail, ThreadSummary } from "@/types";

export interface ListThreadsParams {
  page?: number;
  page_size?: number;
  sort?: "newest" | "oldest";
}

export async function listThreads(
  params: ListThreadsParams = {},
): Promise<PaginatedResponse<ThreadSummary>> {
  const response = await apiClient.get<PaginatedResponse<ThreadSummary>>("/threads", { params });
  return response.data;
}

export async function getThread(threadId: string): Promise<ThreadDetail> {
  const response = await apiClient.get<ThreadDetail>(`/threads/${threadId}`);
  return response.data;
}