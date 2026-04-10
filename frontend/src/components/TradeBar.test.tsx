import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TradeBar from './TradeBar';

// Mock the portfolio store
vi.mock('@/stores/usePortfolioStore', () => {
  const store = vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({ isTrading: false })
  );
  store.getState = vi.fn(() => ({
    executeTrade: vi.fn().mockResolvedValue({
      success: true,
      price: 190.0,
      ticker: 'AAPL',
      side: 'buy',
      quantity: 10,
      cash_balance: 8100,
      position: { ticker: 'AAPL', quantity: 10, avg_cost: 190 },
    }),
  }));
  return { usePortfolioStore: store };
});

// Mock the format function
vi.mock('@/lib/format', () => ({
  formatPrice: (n: number) => `$${n.toFixed(2)}`,
}));

describe('TradeBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ticker input, quantity input, Buy and Sell buttons', () => {
    render(<TradeBar />);
    expect(screen.getByPlaceholderText('Ticker')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Qty')).toBeInTheDocument();
    expect(screen.getByText('Buy')).toBeInTheDocument();
    expect(screen.getByText('Sell')).toBeInTheDocument();
  });

  it('accepts user typing in ticker field', async () => {
    const user = userEvent.setup();
    render(<TradeBar />);
    const tickerInput = screen.getByPlaceholderText('Ticker');
    await user.type(tickerInput, 'aapl');
    expect(tickerInput).toHaveValue('AAPL');
  });

  it('accepts user typing in quantity field', async () => {
    const user = userEvent.setup();
    render(<TradeBar />);
    const qtyInput = screen.getByPlaceholderText('Qty');
    await user.type(qtyInput, '10');
    expect(qtyInput).toHaveValue(10);
  });

  it('disables buttons when inputs are empty', () => {
    render(<TradeBar />);
    expect(screen.getByText('Buy')).toBeDisabled();
    expect(screen.getByText('Sell')).toBeDisabled();
  });
});
