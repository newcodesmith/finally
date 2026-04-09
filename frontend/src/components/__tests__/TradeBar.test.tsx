import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TradeBar from '../TradeBar';

describe('TradeBar', () => {
  const mockOnComplete = jest.fn();

  it('renders trade inputs and buttons', () => {
    render(<TradeBar watchlist={[]} onTradeComplete={mockOnComplete} />);
    expect(screen.getByPlaceholderText('AAPL')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Qty')).toBeInTheDocument();
    expect(screen.getByText('Buy')).toBeInTheDocument();
    expect(screen.getByText('Sell')).toBeInTheDocument();
  });

  it('shows error for empty ticker', () => {
    render(<TradeBar watchlist={[]} onTradeComplete={mockOnComplete} />);
    fireEvent.click(screen.getByText('Buy'));
    expect(screen.getByText('Enter a ticker')).toBeInTheDocument();
  });

  it('shows error for invalid quantity', () => {
    render(<TradeBar watchlist={[]} onTradeComplete={mockOnComplete} />);
    const tickerInput = screen.getByPlaceholderText('AAPL');
    fireEvent.change(tickerInput, { target: { value: 'AAPL' } });
    fireEvent.click(screen.getByText('Buy'));
    expect(screen.getByText('Enter a valid quantity')).toBeInTheDocument();
  });

  it('shows error when ticker not in watchlist', () => {
    render(<TradeBar watchlist={[]} onTradeComplete={mockOnComplete} />);
    const tickerInput = screen.getByPlaceholderText('AAPL');
    const qtyInput = screen.getByPlaceholderText('Qty');
    fireEvent.change(tickerInput, { target: { value: 'AAPL' } });
    fireEvent.change(qtyInput, { target: { value: '10' } });
    fireEvent.click(screen.getByText('Buy'));
    expect(screen.getByText('AAPL not in watchlist. Add it first.')).toBeInTheDocument();
  });

  it('shows Trade label', () => {
    render(<TradeBar watchlist={[]} onTradeComplete={mockOnComplete} />);
    expect(screen.getByText('Trade')).toBeInTheDocument();
  });
});
