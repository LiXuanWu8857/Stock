import type {
  PortfolioSummary,
  Transaction,
  TransactionCreate,
  Quote,
  Market,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const WS_BASE = API_BASE.replace(/^http/, "ws");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response body was not JSON
    }
    throw new Error(detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export function getPortfolio(): Promise<PortfolioSummary> {
  return request<PortfolioSummary>("/api/holdings");
}

export function deleteHolding(id: number): Promise<void> {
  return request<void>(`/api/holdings/${id}`, { method: "DELETE" });
}

export function getTransactions(symbol?: string): Promise<Transaction[]> {
  const qs = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  return request<Transaction[]>(`/api/transactions${qs}`);
}

export function createTransaction(tx: TransactionCreate): Promise<Transaction> {
  return request<Transaction>("/api/transactions", {
    method: "POST",
    body: JSON.stringify(tx),
  });
}

export function deleteTransaction(id: number): Promise<void> {
  return request<void>(`/api/transactions/${id}`, { method: "DELETE" });
}

export function getQuote(symbol: string, market?: Market): Promise<Quote> {
  const qs = market ? `?market=${market}` : "";
  return request<Quote>(`/api/quotes/${encodeURIComponent(symbol)}${qs}`);
}

export function detectMarket(symbol: string): Market {
  return /^\d+$/.test(symbol.trim()) ? "TW" : "US";
}
