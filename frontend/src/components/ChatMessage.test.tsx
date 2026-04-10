import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChatMessage from './ChatMessage';
import type { ChatMessage as ChatMessageType } from '@/types/chat';

// Mock the format function
vi.mock('@/lib/format', () => ({
  formatPrice: (n: number) => `$${n.toFixed(2)}`,
}));

const makeMessage = (
  overrides: Partial<ChatMessageType> = {}
): ChatMessageType => ({
  id: 'msg-1',
  role: 'user',
  content: 'Hello',
  timestamp: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('ChatMessage', () => {
  it('renders user message content', () => {
    render(<ChatMessage message={makeMessage({ content: 'Buy AAPL' })} />);
    expect(screen.getByText('Buy AAPL')).toBeInTheDocument();
  });

  it('renders assistant message content', () => {
    render(
      <ChatMessage
        message={makeMessage({ role: 'assistant', content: 'I bought 10 AAPL.' })}
      />
    );
    expect(screen.getByText('I bought 10 AAPL.')).toBeInTheDocument();
  });

  it('applies different styles for user vs assistant messages', () => {
    const { container: userContainer } = render(
      <ChatMessage message={makeMessage({ role: 'user' })} />
    );
    const userInner = userContainer.querySelector('.bg-accent-purple\\/20');

    const { container: assistantContainer } = render(
      <ChatMessage message={makeMessage({ role: 'assistant' })} />
    );
    const assistantInner = assistantContainer.querySelector('.bg-surface-hover');

    expect(userInner).toBeInTheDocument();
    expect(assistantInner).toBeInTheDocument();
  });

  it('renders trade action confirmations', () => {
    const message = makeMessage({
      role: 'assistant',
      content: 'Done!',
      actions: {
        trades: [{ ticker: 'AAPL', side: 'buy', quantity: 10, price: 190 }],
        watchlist_changes: [],
        errors: [],
      },
    });
    render(<ChatMessage message={message} />);
    expect(screen.getByText('[BUY]')).toBeInTheDocument();
    expect(screen.getByText(/10 AAPL/)).toBeInTheDocument();
  });

  it('renders watchlist change confirmations', () => {
    const message = makeMessage({
      role: 'assistant',
      content: 'Added!',
      actions: {
        trades: [],
        watchlist_changes: [
          { ticker: 'PYPL', action: 'add', success: true },
        ],
        errors: [],
      },
    });
    render(<ChatMessage message={message} />);
    expect(screen.getByText('+ Added PYPL')).toBeInTheDocument();
  });

  it('renders error messages in actions', () => {
    const message = makeMessage({
      role: 'assistant',
      content: 'Oops',
      actions: {
        trades: [],
        watchlist_changes: [],
        errors: ['Insufficient cash'],
      },
    });
    render(<ChatMessage message={message} />);
    expect(screen.getByText(/Insufficient cash/)).toBeInTheDocument();
  });

  it('does not render actions section when no actions', () => {
    const { container } = render(
      <ChatMessage message={makeMessage({ role: 'assistant', content: 'Hi' })} />
    );
    // No trade tags should exist
    expect(container.querySelector('[class*="trade"]')).toBeNull();
  });
});
