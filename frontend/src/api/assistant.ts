import client from "./client";
import type { Envelope } from "../types";

export interface AssistantReply {
  conversation_id: string;
  reply: string;
  tokens_used?: number | null;
}

export async function sendAssistantMessage(message: string, conversationId?: string | null) {
  const response = await client.post<Envelope<AssistantReply>>("/assistant/chat", { message, conversation_id: conversationId ?? null });
  return response.data;
}
