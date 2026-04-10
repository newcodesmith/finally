'use client';

import type { ChatMessage as ChatMessageType } from '@/types/chat';
import { formatPrice } from '@/lib/format';

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const hasActions =
    message.actions &&
    (message.actions.trades.length > 0 ||
      message.actions.watchlist_changes.length > 0 ||
      message.actions.errors.length > 0);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`rounded-lg px-3 py-2 max-w-[80%] text-sm ${
          isUser
            ? 'bg-accent-purple/20 text-text-primary ml-auto'
            : 'bg-surface-hover text-text-primary'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {hasActions && (
          <div className="mt-2 space-y-1">
            {message.actions!.trades.map((trade, i) => (
              <div
                key={`trade-${i}`}
                className="text-xs px-2 py-1 rounded bg-surface border border-border flex items-center gap-1"
              >
                <span
                  className={
                    trade.side === 'buy'
                      ? 'text-semantic-up font-medium'
                      : 'text-semantic-down font-medium'
                  }
                >
                  {trade.side === 'buy' ? '[BUY]' : '[SELL]'}
                </span>
                <span className="text-text-secondary">
                  {trade.quantity} {trade.ticker} @ {formatPrice(trade.price)}
                </span>
              </div>
            ))}

            {message.actions!.watchlist_changes.map((change, i) => (
              <div
                key={`wl-${i}`}
                className="text-xs px-2 py-1 rounded bg-surface border border-border"
              >
                <span
                  className={
                    change.action === 'add'
                      ? 'text-semantic-up'
                      : 'text-semantic-down'
                  }
                >
                  {change.action === 'add'
                    ? `+ Added ${change.ticker}`
                    : `- Removed ${change.ticker}`}
                </span>
              </div>
            ))}

            {message.actions!.errors.map((error, i) => (
              <div
                key={`err-${i}`}
                className="text-xs px-2 py-1 rounded bg-surface border border-border text-semantic-down"
              >
                Failed: {error}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
