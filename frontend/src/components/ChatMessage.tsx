import React from 'react';

interface ChatMessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
  };
  isLast?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isLast = false
}) => {
  const isUser = message.role === 'user';
  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 ${isLast ? 'mb-0' : ''}`}>
      <div className={`max-w-[80%] px-4 py-2 rounded-lg shadow-md ${
        isUser
          ? 'bg-primary text-white'
          : 'bg-white border border-gray-200'
      }`}>
        <div className="flex items-center mb-1">
          <span className="font-medium">{isUser ? 'You' : 'AI Assistant'}</span>
          <span className="ml-2 text-xs text-gray-500">
            {formatTime(message.timestamp)}
          </span>
        </div>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
};

export default ChatMessage;