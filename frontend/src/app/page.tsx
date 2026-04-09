'use client';

import AppShell from '@/components/AppShell';
import { useSSE } from '@/hooks/useSSE';
import { usePortfolio } from '@/hooks/usePortfolio';
import { usePriceStore } from '@/stores/usePriceStore';

export default function Home() {
  useSSE();
  const { cash_balance, total_value } = usePortfolio();
  const connectionStatus = usePriceStore((s) => s.connectionStatus);

  return (
    <AppShell
      portfolioValue={total_value}
      cashBalance={cash_balance}
      connectionStatus={connectionStatus}
    />
  );
}
