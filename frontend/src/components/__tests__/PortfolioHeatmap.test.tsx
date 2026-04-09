import React from 'react';
import { render, screen } from '@testing-library/react';
import PortfolioHeatmap from '../PortfolioHeatmap';

describe('PortfolioHeatmap', () => {
  it('shows placeholder when no positions', () => {
    render(<PortfolioHeatmap positions={[]} prices={{}} />);
    expect(screen.getByText(/No positions yet/)).toBeInTheDocument();
  });

  it('renders with positions', () => {
    const positions = [
      {
        ticker: 'AAPL',
        quantity: 10,
        avg_cost: 180,
        current_price: 190,
        unrealized_pnl: 100,
        pnl_percent: 5.56,
        value: 1900,
      },
    ];
    render(<PortfolioHeatmap positions={positions} prices={{}} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });

  it('shows Portfolio Map label', () => {
    render(<PortfolioHeatmap positions={[]} prices={{}} />);
    expect(screen.getByText('Portfolio Map')).toBeInTheDocument();
  });
});
