import { FormEvent, useState } from "react";
import { Loader2, SendHorizonal, Trash2 } from "lucide-react";
import { sendAssistantMessage } from "../api/assistant";
import { AuthMessage } from "../components/AuthMessage";
import { MarkdownMessage } from "../components/MarkdownMessage";
import { getAssistantErrorMessage } from "../hooks/assistantUtils";

type ToastType = "success" | "error" | "warning" | "info";

export function AssistantPage({ onNotify }: { onNotify: (message: string, type?: ToastType) => void }) {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const suggestedPrompts = [
    "Best value route to Dubai",
    "Carry-on rules for long-haul travel",
    "How early should I arrive for an international flight?",
  ];
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [inputVal, setInputVal] = useState("");

  const handleSendText = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setInputVal("");
    setErrorMessage(undefined);
    setLoading(true);

    try {
      const response = await sendAssistantMessage(trimmed, conversationId);
      const dataPayload = response?.data || response;
      const reply = dataPayload?.reply || "I am available to help with your flight queries.";
      const nextConversationId = dataPayload?.conversation_id || conversationId;

      if (nextConversationId) {
        setConversationId(nextConversationId);
      }
      setMessages((current) => [...current, { role: "assistant", content: reply }]);
      onNotify("Assistant responded", "info");
    } catch (error) {
      console.error("Assistant API Error:", error);
      const fallback = getAssistantErrorMessage(error) ?? "The assistant is temporarily unavailable. Please try again in a moment.";
      setErrorMessage(fallback);
      onNotify(fallback, "warning");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleSendText(inputVal);
  };

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Travel assistant</h1>
        <p>Ask about routes, fares, baggage, or airport guidance.</p>
      </div>
      <div className="assistant-toolbar">
        <span className="pill">24/7 support</span>
        <button
          className="ghost-button"
          type="button"
          onClick={() => {
            setMessages([]);
            setConversationId(null);
            setErrorMessage(undefined);
          }}
        >
          <Trash2 size={14} /> Clear chat
        </button>
      </div>
      <div className="meta-row compact">
        {suggestedPrompts.map((prompt) => (
          <button
            key={prompt}
            className="pill"
            type="button"
            disabled={loading}
            onClick={() => handleSendText(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
      <div className="chat">
        {messages.length === 0 ? (
          <p className="chat-empty">Try: “When is the cheapest time to fly to Dubai?”</p>
        ) : null}
        {errorMessage ? <AuthMessage variant="error">{errorMessage}</AuthMessage> : null}
        {messages.map((message, index) => (
          <div className={`assistant-message ${message.role}`} key={index}>
            {message.role === "assistant" ? (
              <MarkdownMessage content={message.content} />
            ) : (
              <p>{message.content}</p>
            )}
          </div>
        ))}
        {loading ? <p className="chat-loading">Thinking…</p> : null}
      </div>
      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          name="message"
          aria-label="Message"
          placeholder="Ask about routes, fares, or baggage"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          required
        />
        <button className="primary-button" type="submit" disabled={loading || !inputVal.trim()}>
          {loading ? <Loader2 size={16} className="spin" /> : <SendHorizonal size={16} />}
        </button>
      </form>
    </section>
  );
}
