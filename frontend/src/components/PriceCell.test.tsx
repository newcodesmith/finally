import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PriceCell from './PriceCell';

describe('PriceCell', () => {
  it('renders the formatted price', () => {
    render(<PriceCell price={190.5} changeDirection="unchanged" />);
    expect(screen.getByText('$190.50')).toBeInTheDocument();
  });

  it('applies flash-up class when direction is up', () => {
    const { rerender } = render(
      <PriceCell price={190.0} changeDirection="unchanged" />
    );
    rerender(<PriceCell price={191.0} changeDirection="up" />);
    const el = screen.getByText('$191.00');
    expect(el.className).toContain('flash-up');
  });

  it('applies flash-down class when direction is down', () => {
    const { rerender } = render(
      <PriceCell price={190.0} changeDirection="unchanged" />
    );
    rerender(<PriceCell price={189.0} changeDirection="down" />);
    const el = screen.getByText('$189.00');
    expect(el.className).toContain('flash-down');
  });

  it('does not apply flash class when direction is unchanged', () => {
    render(<PriceCell price={190.0} changeDirection="unchanged" />);
    const el = screen.getByText('$190.00');
    expect(el.className).not.toContain('flash-up');
    expect(el.className).not.toContain('flash-down');
  });
});
