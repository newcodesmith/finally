'use client';

import { useEffect, useRef, useState } from 'react';
import { formatPrice } from '@/lib/format';

interface PriceCellProps {
  price: number;
  changeDirection: 'up' | 'down' | 'unchanged';
}

export default function PriceCell({ price, changeDirection }: PriceCellProps) {
  const [flashClass, setFlashClass] = useState('');
  const prevDirection = useRef(changeDirection);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (changeDirection !== prevDirection.current) {
      prevDirection.current = changeDirection;

      if (changeDirection === 'up') {
        setFlashClass('flash-up');
      } else if (changeDirection === 'down') {
        setFlashClass('flash-down');
      }

      if (changeDirection !== 'unchanged') {
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          setFlashClass('');
        }, 500);
      }
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [changeDirection]);

  return (
    <span
      className={`price-cell text-[13px] text-text-primary tabular-nums rounded px-1 ${flashClass}`}
    >
      {formatPrice(price)}
    </span>
  );
}
