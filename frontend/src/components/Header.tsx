'use client';

import { ConnectionStatus } from '@/types/market';
import { formatPrice } from '@/lib/format';
import ConnectionDot from './ConnectionDot';

interface HeaderProps {
  portfolioValue: number;
  cashBalance: number;
  connectionStatus: ConnectionStatus;
}

export default function Header({ portfolioValue, cashBalance, connectionStatus }: HeaderProps) {
  return (
    <header className="h-12 shrink-0 w-full bg-surface-raised border-b border-border flex items-center justify-between px-6">
      {/* Left: App name */}
      <span className="text-sm font-semibold text-text-primary">
        FinAlly
      </span>

      {/* Right: Portfolio value, separator, cash, connection dot */}
      <div className="flex items-center gap-2">
        {/* Portfolio total value */}
        <span className="text-sm font-semibold text-accent-yellow tabular-nums">
          {formatPrice(portfolioValue)}
        </span>

        {/* Separator */}
        <span className="w-px h-5 bg-border" />

        {/* Cash balance */}
        <span className="text-sm text-text-secondary">Cash</span>
        <span className="text-sm text-text-primary tabular-nums">
          {formatPrice(cashBalance)}
        </span>

        {/* Connection status */}
        <ConnectionDot status={connectionStatus} />
      </div>
    </header>
  );
}
