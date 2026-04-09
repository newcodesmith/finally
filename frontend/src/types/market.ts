export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  session_open_price: number;
  timestamp: string;
  change: number;
  change_percent: number;
  change_direction: 'up' | 'down' | 'unchanged';
}

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';
