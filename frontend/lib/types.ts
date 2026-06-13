export type Market = "TW" | "US";
export type Action = "BUY" | "SELL";

export interface Holding {
  id: number;
  user_id: number;
  symbol: string;
  market: Market;
  shares: string;
  avg_cost: string;
  created_at: string;
  updated_at: string;
  current_price: number | null;
  current_value: number | null;
  cost_basis: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  weight: number | null;
  stock_name: string | null;
  currency: string | null;
  change: number | null;
  change_pct: number | null;
}

export interface PortfolioSummary {
  total_invested: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  holdings: Holding[];
  holding_count: number;
}

export interface Transaction {
  id: number;
  user_id: number;
  symbol: string;
  market: Market;
  action: Action;
  price: string;
  shares: string;
  date: string;
  note: string | null;
  created_at: string;
  total_amount: number | null;
}

export interface TransactionCreate {
  symbol: string;
  market: Market;
  action: Action;
  price: number;
  shares: number;
  date: string;
  note?: string;
}

export interface Quote {
  symbol: string;
  market: Market;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  name: string | null;
  currency: string | null;
  error: string | null;
  is_extended: boolean;
}

export type PerformanceRange = "1M" | "3M" | "6M" | "1Y" | "ALL";

export interface PerformancePoint {
  date: string;
  invested_amount: number;
  withdrawn_amount: number;
  market_value: number;
  cash: number;
  total_asset: number;
  net_profit: number;
  roi_pct: number;
  twr_pct: number;
}

export interface PerformanceHistory {
  points: PerformancePoint[];
  max_drawdown_pct: number;
  range: PerformanceRange;
}

export interface QuotesMessage {
  type: "quotes" | "error";
  data?: Record<string, Quote>;
  message?: string;
}
