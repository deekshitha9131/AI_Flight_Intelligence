import React, { useEffect, useRef, useState } from 'react';
import { assistantChat } from '../../api/assistant';
import { createConversation, getConversation, listConversations } from '../../api/conversations';
import { ConversationResponse, MessageResponse } from '../../types/conversation';
import { AssistantResponse } from '../../types/assistant';
import { FlightResponse } from '../../types/flight';
import FlightCard from '../FlightCard';
import ErrorState from '../ui/ErrorState';
import LoadingSpinner from '../ui/LoadingSpinner';

type AssistantMessage = Pick<MessageResponse, 'id' | 'role' | 'content' | 'created_at'> & {
  flightResults?: FlightResponse[];
  clarificationQuestions?: string[];
};

const suggestedPrompts = [
  'Find cheap flights from Hyderabad to Delhi',
  'Compare my flights',
  'Which flight should I choose?',
  'Predict the best time to book',
  'Explain my recommendation',
];

const AssistantPage: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showError, setShowError] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadConversation = async (id: string) => {
    setHistoryLoading(true);
    setError(null);
    setShowError(false);
    try {
      const conversation = await getConversation(id);
      setConversationId(conversation.id);
      setMessages(conversation.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load this conversation.');
      setShowError(true);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    const loadHistory = async () => {
      try {
        const result = await listConversations();
        if (!active) return;
        setConversations(result.conversations);
        if (result.conversations[0]) {
          await loadConversation(result.conversations[0].id);
        } else {
          setHistoryLoading(false);
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Conversation history is unavailable.');
        setShowError(true);
        setHistoryLoading(false);
      }
    };
    void loadHistory();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const startConversation = async () => {
    setError(null);
    setShowError(false);
    setLoading(false);
    try {
      const conversation = await createConversation();
      setConversations((current) => [conversation, ...current]);
      setConversationId(conversation.id);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start a conversation.');
      setShowError(true);
    }
  };

  const appendAssistantResponse = (response: AssistantResponse) => {
    const hasUsefulContent = response.message || response.clarification_questions?.length || response.flight_results?.length;
    if (!hasUsefulContent) return;
    setMessages((current) => [...current, {
      id: `local-${Date.now()}-answer`,
      role: 'assistant',
      content: response.message || 'I found some information for your trip.',
      created_at: new Date().toISOString(),
      clarificationQuestions: response.clarification_questions,
      flightResults: response.flight_results,
    }]);
  };

  const sendMessage = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    setError(null);
    setShowError(false);
    setMessages((current) => [...current, {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }]);
    setInput('');
    setLoading(true);
    try {
      const response = await assistantChat({ message: content, conversation_id: conversationId });
      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
        const refreshed = await listConversations();
        setConversations(refreshed.conversations);
      }
      appendAssistantResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The assistant could not respond right now.');
      setShowError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    setShowError(false);
    setError(null);
    if (!conversationId) {
      startConversation();
    }
  };

  const formatTime = (stamp: string) => {
    try {
      return new Date(stamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">AI Flight Assistant</span>
          <h1 className="page-title">Your flight co-pilot.</h1>
          <p className="page-subtitle">Ask questions about flights, prices, predictions and recommendations.</p>
        </div>
        <span className="badge">AI assistant</span>
      </header>

      <section className="surface assistant-layout">
        <aside className="assistant-sidebar">
          <div className="results-head">
            <span className="eyebrow">Conversations</span>
            <button className="icon-button" type="button" onClick={startConversation} aria-label="Start new conversation" title="New conversation">+</button>
          </div>
          <p>Return to a previous planning session or start a fresh one.</p>

          {historyLoading ? (
            <LoadingSpinner size="sm" />
          ) : conversations.length === 0 ? (
            <p>No saved conversations yet.</p>
          ) : (
            <div className="prompt-list">
              {conversations.map((conversation) => (
                <button
                  className="prompt-chip"
                  type="button"
                  key={conversation.id}
                  onClick={() => loadConversation(conversation.id)}
                >
                  {conversation.title || 'Untitled planning session'}<br />
                  <small>{new Date(conversation.updated_at).toLocaleDateString()}</small>
                </button>
              ))}
            </div>
          )}

          <span className="eyebrow" style={{ display: 'block', marginTop: 26 }}>Try asking</span>
          <div className="prompt-list" style={{ marginTop: 10 }}>
            {suggestedPrompts.map((prompt) => (
              <button
                className="prompt-chip"
                type="button"
                key={prompt}
                onClick={() => setInput(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </aside>

        <div className="assistant-main">
          <div className="chat-head">
            <h2 className="section-title">Planning session</h2>
            <p className="section-note">
              {conversationId ? 'Conversation context is saved to your account.' : 'Start a message to create conversation context.'}
            </p>
          </div>

          <div className="chat-scroll">
            {historyLoading ? (
              <div className="empty-state">
                <div className="skeleton" style={{ width: 180, margin: '0 auto 14px' }} />
                <div className="skeleton" style={{ width: 280, margin: '0 auto' }} />
              </div>
            ) : showError ? (
              <ErrorState
                title="Something went wrong"
                description={error || 'Unable to load the assistant.'}
                retryAction={
                  <button className="btn btn-primary" type="button" onClick={handleRetry}>
                    Try again
                  </button>
                }
              />
            ) : messages.length === 0 && !loading ? (
              <div className="empty-state" style={{ padding: '54px 12px' }}>
                <div className="empty-icon">✦</div>
                <h3>What are you planning?</h3>
                <p>Include an origin, destination, and date when you want live flight options.</p>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div className={`chat-message ${message.role}`} key={message.id}>
                    {message.role === 'assistant' && <span className="avatar" style={{ width: 28, height: 28 }}>✦</span>}
                    <div className="chat-bubble">
                      <div className="chat-meta">
                        {message.role === 'user' ? 'You' : 'AI assistant'} · {formatTime(message.created_at)}
                      </div>
                      <p>{message.content}</p>
                      {message.clarificationQuestions && message.clarificationQuestions.filter(
                        (question) => !message.content.toLowerCase().includes(question.toLowerCase())
                      ).length > 0 && (
                        <div className="prompt-list" style={{ marginTop: 12 }}>
                          {message.clarificationQuestions.filter(
                            (question) => !message.content.toLowerCase().includes(question.toLowerCase())
                          ).map((question) => (
                            <button
                              className="prompt-chip"
                              type="button"
                              key={question}
                              onClick={() => setInput(question)}
                            >
                              {question}
                            </button>
                          ))}
                        </div>
                      )}
                      {message.flightResults && message.flightResults.length > 0 && (
                        <div className="flight-list" style={{ marginTop: 16 }}>
                          {message.flightResults.map((flight) => (
                            <FlightCard key={flight.id} flight={flight} />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="chat-message">
                    <span className="avatar" style={{ width: 28, height: 28 }}>✦</span>
                    <div className="chat-bubble">
                      <div className="chat-meta">AI assistant</div>
                      <div style={{ display: 'flex', gap: 5 }}>
                        <span className="skeleton" style={{ width: 7, height: 7, borderRadius: '50%', minHeight: 0 }} />
                        <span className="skeleton" style={{ width: 7, height: 7, borderRadius: '50%', minHeight: 0 }} />
                        <span className="skeleton" style={{ width: 7, height: 7, borderRadius: '50%', minHeight: 0 }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </>
            )}
          </div>

          <form className="chat-composer" onSubmit={sendMessage}>
            <div className="input-row">
              <input
                ref={inputRef}
                type="text"
                className="input"
                placeholder="Ask about your flights..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                aria-label="Message"
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || !input.trim()}
                aria-label="Send message"
              >
                {loading ? <LoadingSpinner size="sm" /> : 'Send'}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
};

export default AssistantPage;
