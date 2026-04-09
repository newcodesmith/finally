'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { sendChatMessage } from '@/lib/api';
import type { ChatMessage } from '@/types';

interface ChatPanelProps {
  onClose: () => void;
  onActionComplete: () => void;
}

export default function ChatPanel({ onClose, onActionComplete }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const response = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.message,
          trades: response.trades,
          watchlist_changes: response.watchlist_changes,
          errors: response.errors,
        },
      ]);

      // If the AI executed trades or watchlist changes, refresh data
      if (response.trades.length > 0 || response.watchlist_changes.length > 0) {
        onActionComplete();
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I had trouble processing that. Please try again.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, onActionComplete]);

  return (
    <div className="h-full flex flex-col bg-terminal-bg">
      {/* Header */}
      <div className="px-3 py-2 border-b border-terminal-border flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent-purple" />
          <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
            AI Assistant
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-terminal-text-dim hover:text-terminal-text text-sm transition-colors"
        >
          x
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-terminal-text-dim text-xs py-8">
            <p className="mb-2">FinAlly AI Assistant</p>
            <p className="text-[10px]">Ask me to analyze your portfolio, suggest trades, or execute orders.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`${msg.role === 'user' ? 'flex justify-end' : ''}`}>
            {msg.role === 'user' ? (
              <div className="bg-accent-purple/20 border border-accent-purple/30 rounded-lg px-3 py-2 max-w-[85%]">
                <p className="text-xs text-terminal-text whitespace-pre-wrap">{msg.content}</p>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="bg-terminal-surface border border-terminal-border rounded-lg px-3 py-2">
                  <p className="text-xs text-terminal-text whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </p>
                </div>

                {/* Trade executions */}
                {msg.trades && msg.trades.length > 0 && (
                  <div className="space-y-1">
                    {msg.trades.map((trade, j) => (
                      <div
                        key={j}
                        className={`text-[10px] px-2 py-1 rounded border ${
                          trade.side === 'buy'
                            ? 'bg-price-up/10 border-price-up/20 text-price-up'
                            : 'bg-price-down/10 border-price-down/20 text-price-down'
                        }`}
                      >
                        {trade.side.toUpperCase()} {trade.quantity} {trade.ticker} @ ${trade.price.toFixed(2)}
                      </div>
                    ))}
                  </div>
                )}

                {/* Watchlist changes */}
                {msg.watchlist_changes && msg.watchlist_changes.length > 0 && (
                  <div className="space-y-1">
                    {msg.watchlist_changes.map((change, j) => (
                      <div
                        key={j}
                        className="text-[10px] px-2 py-1 rounded border bg-accent-blue/10 border-accent-blue/20 text-accent-blue"
                      >
                        {change.action === 'add' ? '+' : '-'} {change.ticker} {change.action === 'add' ? 'added to' : 'removed from'} watchlist
                      </div>
                    ))}
                  </div>
                )}

                {/* Errors */}
                {msg.errors && msg.errors.length > 0 && (
                  <div className="space-y-1">
                    {msg.errors.map((err, j) => (
                      <div
                        key={j}
                        className="text-[10px] px-2 py-1 rounded border bg-price-down/10 border-price-down/20 text-price-down"
                      >
                        {err}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center gap-2 text-terminal-text-muted">
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 bg-accent-purple rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-accent-purple rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-accent-purple rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-[10px]">Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-2 border-t border-terminal-border flex-shrink-0">
        <div className="flex gap-1.5">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask FinAlly..."
            disabled={loading}
            className="flex-1 bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-xs text-terminal-text placeholder-terminal-text-dim focus:border-accent-purple focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-3 py-2 bg-accent-purple hover:bg-accent-purple/80 text-white text-[10px] font-semibold rounded disabled:opacity-30 transition-colors uppercase"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
