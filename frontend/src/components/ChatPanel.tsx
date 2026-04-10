'use client';

import { useState, useRef, useEffect } from 'react';
import { X } from 'lucide-react';
import { useChatStore } from '@/stores/useChatStore';
import ChatMessage from './ChatMessage';

export default function ChatPanel() {
  const messages = useChatStore((s) => s.messages);
  const isLoading = useChatStore((s) => s.isLoading);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const toggleOpen = useChatStore((s) => s.toggleOpen);

  const [inputText, setInputText] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading]);

  const handleSubmit = () => {
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;
    sendMessage(trimmed);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-10 shrink-0 flex items-center justify-between px-3 border-b border-border">
        <span className="text-sm font-semibold text-text-primary">
          AI Assistant
        </span>
        <button
          onClick={toggleOpen}
          className="text-text-muted hover:text-text-primary cursor-pointer"
          title="Close chat"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-text-muted text-xs italic text-center">
              Ask me about your portfolio, or tell me to execute trades.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="text-accent-blue text-sm px-3 py-2 animate-pulse">
            Thinking...
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-border p-3 flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask FinAlly..."
          className="flex-1 bg-surface text-text-primary text-sm rounded px-3 py-2 border border-border focus:border-accent-blue focus:outline-none placeholder:text-text-muted"
        />
        <button
          onClick={handleSubmit}
          disabled={!inputText.trim() || isLoading}
          className="bg-accent-purple text-white px-3 py-2 rounded text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
