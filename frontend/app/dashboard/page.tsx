"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PlusIcon } from "@heroicons/react/24/solid";
import clsx from "clsx";
import {
  getPortfolio,
  getTransactions,
  deleteHolding,
} from "@/lib/api";
import { useQuotesWebSocket } from "@/hooks/useWebSocket";
import type { PortfolioSummary as Summary, Transaction } from "@/lib/types";
import PortfolioSummary from "@/components/PortfolioSummary";
import HoldingsTable from "@/components/HoldingsTable";
import AddHoldingModal from "@/components/AddHoldingModal";
import TransactionHistory from "@/components/TransactionHistory";

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [txLoading, setTxLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPortfolio();
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法載入投資組合");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTransactions = useCallback(async () => {
    setTxLoading(true);
    try {
      const data = await getTransactions();
      setTransactions(data);
    } catch {
      // transactions are non-critical; portfolio error banner covers API issues
    } finally {
      setTxLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortfolio();
    loadTransactions();
  }, [loadPortfolio, loadTransactions]);

  const symbolKeys = useMemo(
    () => (summary?.holdings ?? []).map((h) => `${h.symbol}:${h.market}`),
    [summary]
  );
  const { quotes: liveQuotes, connected } = useQuotesWebSocket(symbolKeys);

  // Today's P&L: sum of (today's change * shares) per holding
  const todayPnl = useMemo(() => {
    if (!summary) return 0;
    return summary.holdings.reduce((acc, h) => {
      const key = `${h.symbol}:${h.market}`;
      const change = liveQuotes[key]?.change ?? h.change;
      if (change === null || change === undefined) return acc;
      return acc + change * parseFloat(h.shares);
    }, 0);
  }, [summary, liveQuotes]);

  async function handleDelete(id: number) {
    if (!window.confirm("確定要刪除這筆持股嗎？")) return;
    try {
      await deleteHolding(id);
      await loadPortfolio();
    } catch (err) {
      setError(err instanceof Error ? err.message : "刪除失敗");
    }
  }

  function handleAdded() {
    loadPortfolio();
    loadTransactions();
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">📈 股票庫存管理</h1>
            <span
              className={clsx(
                "flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs",
                connected
                  ? "bg-emerald-500/15 text-emerald-400"
                  : "bg-slate-700/50 text-slate-400"
              )}
            >
              <span
                className={clsx(
                  "h-1.5 w-1.5 rounded-full",
                  connected ? "bg-emerald-400" : "bg-slate-500"
                )}
              />
              {connected ? "即時報價連線中" : "離線"}
            </span>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            <PlusIcon className="h-4 w-4" />
            新增持股
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <PortfolioSummary summary={summary} todayPnl={todayPnl} />

        <HoldingsTable
          holdings={summary?.holdings ?? []}
          liveQuotes={liveQuotes}
          loading={loading}
          onRefresh={loadPortfolio}
          onDelete={handleDelete}
        />

        <TransactionHistory transactions={transactions} loading={txLoading} />
      </main>

      <AddHoldingModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onAdded={handleAdded}
      />
    </div>
  );
}
