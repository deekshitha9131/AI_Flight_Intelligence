import { api } from './client';
import { AssistantChatRequest, AssistantResponse } from '../types/assistant';

// Chat with assistant
export const assistantChat = async (
  chatRequest: AssistantChatRequest
): Promise<AssistantResponse> => {
  const response = await api.post<AssistantResponse>('/assistant/chat', {
    body: chatRequest,
  });
  return response;
};

