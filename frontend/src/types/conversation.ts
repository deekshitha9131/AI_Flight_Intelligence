export interface ConversationCreate {
  title?: string;
}

export interface ConversationResponse {
  id: string;
  user_id: string;
  title?: string;
  created_at: string; // ISO string
  updated_at: string; // ISO string
}

export interface ConversationListResponse {
  conversations: ConversationResponse[];
}

export interface ConversationWithMessagesResponse {
  id: string;
  user_id: string;
  title?: string;
  created_at: string; // ISO string
  updated_at: string; // ISO string
  messages: MessageResponse[];
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string; // ISO string
}
