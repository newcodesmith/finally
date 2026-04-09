'use client';

import { formatPercent } from '@/lib/format';

interface ChangePercentProps {
  value: number;
}

export default function ChangePercent({ value }: ChangePercentProps) {
  const colorClass =
    value > 0
      ? 'text-semantic-up'
      : value < 0
        ? 'text-semantic-down'
        : 'text-text-muted';

  return (
    <span className={`text-[11px] font-semibold tabular-nums ${colorClass}`}>
      {formatPercent(value)}
    </span>
  );
}
