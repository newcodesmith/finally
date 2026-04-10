'use client';

import { useEffect } from 'react';
import { usePortfolioStore } from '@/stores/usePortfolioStore';

export function usePortfolio(refreshInterval = 5000) {
  const fetchPortfolio = usePortfolioStore((s) => s.fetchPortfolio);
  const fetchSnapshots = usePortfolioStore((s) => s.fetchSnapshots);
  const cashBalance = usePortfolioStore((s) => s.cashBalance);
  const totalValue = usePortfolioStore((s) => s.totalValue);

  useEffect(() => {
    fetchPortfolio();
    fetchSnapshots();
    const interval = setInterval(() => {
      fetchPortfolio();
      fetchSnapshots();
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchPortfolio, fetchSnapshots, refreshInterval]);

  return { cash_balance: cashBalance, total_value: totalValue };
}
