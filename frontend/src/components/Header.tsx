'use client';

import { formatUSD } from '@/lib/format';
import type { ConnectionStatus } from '@/types';

interface HeaderProps {
  totalValue: number | null;
  cashBalance: number | null;
  connectionStatus: ConnectionStatus;
}

const statusColors: Record<ConnectionStatus, string> = {
  connected: 'bg-price-up',
  connecting: 'bg-accent-yellow',
  disconnected: 'bg-price-down',
};

const statusLabels: Record<ConnectionStatus, string> = {
  connected: 'Live',
  connecting: 'Connecting...',
  disconnected: 'Disconnected',
};

export default function Header({ totalValue, cashBalance, connectionStatus }: HeaderProps) {
  return (
    <header className="h-12 flex-shrink-0 bg-terminal-surface border-b border-terminal-border flex items-center justify-between px-4">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold tracking-tight">
          <span className="text-accent-yellow">Fin</span>
          <span className="text-terminal-text">Ally</span>
        </h1>
        <span className="text-[10px] text-terminal-text-dim uppercase tracking-widest">
          AI Trading Workstation
        </span>
      </div>

      {/* Center: Portfolio value */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-terminal-text-muted uppercase">Portfolio</span>
          <span className="text-base font-semibold text-accent-yellow">
            {totalValue !== null ? formatUSD(totalValue) : '---'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-terminal-text-muted uppercase">Cash</span>
          <span className="text-sm text-terminal-text">
            {cashBalance !== null ? formatUSD(cashBalance) : '---'}
          </span>
        </div>
      </div>

      {/* Right: Connection status */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${statusColors[connectionStatus]}`} />
        <span className="text-[10px] text-terminal-text-muted">
          {statusLabels[connectionStatus]}
        </span>
      </div>
    </header>
  );
}
