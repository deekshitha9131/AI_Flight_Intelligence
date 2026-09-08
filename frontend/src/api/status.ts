import { apiClient } from "./client";

export interface ServiceStatus {
  gmail: "connected" | "disconnected" | "expired" | "error";
  ai: "available" | "unavailable" | "error";
  draft: "ready" | "not-ready" | "error";
  user: {
    id: string;
    email: string;
    full_name: string;
  } | null;
}

export async function getServiceStatus(): Promise<ServiceStatus> {
  const response = await apiClient.get<ServiceStatus>("/status");
  return response.data;
}

export async function getGmailStatus(): Promise<{ status: "connected" | "disconnected" }> {
  const response = await apiClient.get<{ status: "connected" | "disconnected" }>("/status/gmail");
  return response.data;
}

export async function getAIStatus(): Promise<{ status: "available" | "unavailable" | "error" }> {
  const response = await apiClient.get<{ status: "available" | "unavailable" | "error" }>("/status/ai");
  return response.data;
}

export async function getDraftStatus(): Promise<{ status: "ready" | "not-ready" | "error" }> {
  const response = await apiClient.get<{ status: "ready" | "not-ready" | "error" }>("/status/draft");
  return response.data;
}
