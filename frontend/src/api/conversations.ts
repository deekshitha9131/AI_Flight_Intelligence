import { api } from './client';
import {
  ConversationCreate,
  ConversationResponse,
  ConversationListResponse,
  ConversationWithMessagesResponse,
  MessageResponse,
} from '../types/conversation';

// Create a new conversation
export const createConversation = async (): Promise<ConversationResponse> => {
  const response = await api.post<ConversationResponse>('/conversations/', {});
  return response;
};

// List conversations for the current user
export const listConversations = async (): Promise<ConversationListResponse> => {
  const response = await api.get<ConversationListResponse>('/conversations/');
  return response;
};

// Get a specific conversation by ID
export const getConversation = async (
  conversationId: string
): Promise<ConversationWithMessagesResponse> => {
  const response = await api.get<ConversationWithMessagesResponse>(
    `/conversations/${conversationId}`
  );
  return response;
};

// Delete a conversation
export const deleteConversation = async (
  conversationId: string
): Promise<void> => {
  await api.delete(`/conversations/${conversationId}`);
  // Returns 204 No Content
};

// Send a message to the assistant (this is actually the assistant chat endpoint)
// We'll keep it in assistant.ts, but we can also have a function here to send a message to a conversation?
// The backend assistant chat endpoint is separate from conversations.
// However, the assistant chat endpoint requires a conversation_id.
// We'll keep the assistant chat in assistant.ts.
// So we don't need a sendMessage function here.

