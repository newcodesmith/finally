import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Header from './Header';

// Mock the format function
vi.mock('@/lib/format', () => ({
  formatPrice: (n: number) => `$${n.toFixed(2)}`,
}));

// Mock the ConnectionDot component
vi.mock('./ConnectionDot', () => ({
  default: ({ status }: { status: string }) => (
    <span data-testid="connection-dot">{status}</span>
  ),
}));

describe('Header', () => {
  it('renders portfolio total value with $ sign', () => {
    render(
      <Header
        portfolioValue={12500.75}
        cashBalance={8000.0}
        connectionStatus="connected"
      />
    );
    expect(screen.getByText('$12500.75')).toBeInTheDocument();
  });

  it('renders cash balance with $ sign', () => {
    render(
      <Header
        portfolioValue={12500.75}
        cashBalance={8000.0}
        connectionStatus="connected"
      />
    );
    expect(screen.getByText('$8000.00')).toBeInTheDocument();
  });

  it('renders the Cash label', () => {
    render(
      <Header
        portfolioValue={10000}
        cashBalance={10000}
        connectionStatus="connected"
      />
    );
    expect(screen.getByText('Cash')).toBeInTheDocument();
  });

  it('renders FinAlly app name', () => {
    render(
      <Header
        portfolioValue={10000}
        cashBalance={10000}
        connectionStatus="connected"
      />
    );
    expect(screen.getByText('FinAlly')).toBeInTheDocument();
  });

  it('renders the connection status dot', () => {
    render(
      <Header
        portfolioValue={10000}
        cashBalance={10000}
        connectionStatus="connected"
      />
    );
    expect(screen.getByTestId('connection-dot')).toBeInTheDocument();
  });
});
