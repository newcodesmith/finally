import React from 'react';
import { render, screen } from '@testing-library/react';
import Header from '../Header';

describe('Header', () => {
  it('renders portfolio value when provided', () => {
    render(
      <Header totalValue={10523.45} cashBalance={8000} connectionStatus="connected" />
    );
    expect(screen.getByText('$10,523.45')).toBeInTheDocument();
  });

  it('renders --- when totalValue is null', () => {
    render(
      <Header totalValue={null} cashBalance={null} connectionStatus="connecting" />
    );
    const dashes = screen.getAllByText('---');
    expect(dashes.length).toBe(2);
  });

  it('renders FinAlly branding', () => {
    render(
      <Header totalValue={10000} cashBalance={10000} connectionStatus="connected" />
    );
    expect(screen.getByText('Fin')).toBeInTheDocument();
    expect(screen.getByText('Ally')).toBeInTheDocument();
  });

  it('shows connection status', () => {
    render(
      <Header totalValue={10000} cashBalance={10000} connectionStatus="connected" />
    );
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('shows connecting status', () => {
    render(
      <Header totalValue={10000} cashBalance={10000} connectionStatus="connecting" />
    );
    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('shows disconnected status', () => {
    render(
      <Header totalValue={10000} cashBalance={10000} connectionStatus="disconnected" />
    );
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('displays cash balance', () => {
    render(
      <Header totalValue={10000} cashBalance={7500.50} connectionStatus="connected" />
    );
    expect(screen.getByText('$7,500.50')).toBeInTheDocument();
  });
});
