'use client';

import { useState, useEffect, useCallback } from 'react';

interface PortfolioData {
  cash_balance: number;
  total_value: number;
}

export function usePortfolio(refreshInterval = 5000) {
  const [data, setData] = useState<PortfolioData>({ cash_balance: 10000, total_value: 10000 });

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await fetch('/api/portfolio');
      if (res.ok) {
        const json = await res.json();
        setData({ cash_balance: json.cash_balance, total_value: json.total_value });
      }
    } catch {
      // Silently fail — header shows last known values
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchPortfolio, refreshInterval]);

  return data;
}
