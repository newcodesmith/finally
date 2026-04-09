import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatPanel from '../ChatPanel';

describe('ChatPanel', () => {
  const mockClose = jest.fn();
  const mockActionComplete = jest.fn();

  it('renders the AI assistant header', () => {
    render(<ChatPanel onClose={mockClose} onActionComplete={mockActionComplete} />);
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('renders the empty state message', () => {
    render(<ChatPanel onClose={mockClose} onActionComplete={mockActionComplete} />);
    expect(screen.getByText('FinAlly AI Assistant')).toBeInTheDocument();
  });

  it('renders the input field', () => {
    render(<ChatPanel onClose={mockClose} onActionComplete={mockActionComplete} />);
    expect(screen.getByPlaceholderText('Ask FinAlly...')).toBeInTheDocument();
  });

  it('renders the send button', () => {
    render(<ChatPanel onClose={mockClose} onActionComplete={mockActionComplete} />);
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('renders close button', () => {
    render(<ChatPanel onClose={mockClose} onActionComplete={mockActionComplete} />);
    expect(screen.getByText('x')).toBeInTheDocument();
  });
});
