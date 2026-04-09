import React from 'react';
import { render, screen } from '@testing-library/react';
import PositionsTable from '../PositionsTable';

const mockPositions = [
  {
    ticker: 'AAPL',
    quantity: 10,
    avg_cost: 180.0,
    current_price: 190.0,
    unrealized_pnl: 100.0,
    pnl_percent: 5.56,
    value: 1900.0,
  },
  {
    ticker: 'TSLA',
    quantity: 5,
    avg_cost: 250.0,
    current_price: 240.0,
    unrealized_pnl: -50.0,
    pnl_percent: -4.0,
    value: 1200.0,
  },
];

describe('PositionsTable', () => {
  it('renders positions', () => {
    render(<PositionsTable positions={mockPositions} prices={{}} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('TSLA')).toBeInTheDocument();
  });

  it('shows empty state when no positions', () => {
    render(<PositionsTable positions={[]} prices={{}} />);
    expect(screen.getByText('No open positions')).toBeInTheDocument();
  });

  it('displays correct quantity', () => {
    render(<PositionsTable positions={mockPositions} prices={{}} />);
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('shows number of open positions', () => {
    render(<PositionsTable positions={mockPositions} prices={{}} />);
    expect(screen.getByText('2 open')).toBeInTheDocument();
  });

  it('shows column headers', () => {
    render(<PositionsTable positions={mockPositions} prices={{}} />);
    expect(screen.getByText('Ticker')).toBeInTheDocument();
    expect(screen.getByText('Qty')).toBeInTheDocument();
    expect(screen.getByText('Avg Cost')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
  });
});
