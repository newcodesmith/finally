'use client';

import { ConnectionStatus } from '@/types/market';

interface ConnectionDotProps {
  status: ConnectionStatus;
}

const statusConfig: Record<ConnectionStatus, { className: string; label: string }> = {
  connected: { className: 'bg-semantic-up', label: 'Connected' },
  reconnecting: { className: 'bg-accent-yellow', label: 'Reconnecting...' },
  disconnected: { className: 'bg-semantic-down', label: 'Disconnected' },
};

export default function ConnectionDot({ status }: ConnectionDotProps) {
  const config = statusConfig[status];

  return (
    <span title={config.label} className="inline-flex items-center">
      <span
        className={`w-2 h-2 rounded-full transition-colors duration-300 ${config.className}`}
      />
    </span>
  );
}
