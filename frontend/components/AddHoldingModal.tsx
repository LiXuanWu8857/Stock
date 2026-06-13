"use client";

import { useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { createTransaction, detectMarket } from "@/lib/api";
import type { Market } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
}

export default function AddHoldingModal({ open, onClose, onAdded }: Props) {
  const [symbol, setSymbol] = useState("");
  const [market, setMarket] = useState<Market>("TW");
  const [marketTouched, setMarketTouched] = useState(false);
  const [date, setDate] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [price, setPrice] = useState("");
  const [shares, setShares] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  function handleSymbolChange(value: string) {
    setSymbol(value);
    if (!marketTouched && value.trim()) {
      setMarket(detectMarket(value));
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const priceNum = parseFloat(price);
    const sharesNum = parseFloat(shares);
    if (!symbol.trim() || !priceNum || priceNum <= 0 || !sharesNum || sharesNum <= 0) {
      setError("請填寫正確的代號、價格與股數");
      return;
    }

    setSubmitting(true);
    try {
      await createTransaction({
        symbol: symbol.trim().toUpperCase(),
        market,
        action: "BUY",
        price: priceNum,
        shares: sharesNum,
        date,
      });
      setSymbol("");
      setPrice("");
      setShares("");
      setMarketTouched(false);
      onAdded();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "新增失敗");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-brand-500 focus:outline-none";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-semibold">新增持股</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm text-slate-400">
              股票代號
            </label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => handleSymbolChange(e.target.value)}
              placeholder="例如：2330 或 AAPL"
              className={inputClass}
              autoFocus
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-slate-400">市場</label>
            <select
              value={market}
              onChange={(e) => {
                setMarket(e.target.value as Market);
                setMarketTouched(true);
              }}
              className={inputClass}
            >
              <option value="TW">台股 (TWSE)</option>
              <option value="US">美股 (US)</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-slate-400">
              買入日期
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">
                買入價格
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="920"
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">
                買入股數
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                placeholder="10"
                className={inputClass}
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {submitting ? "新增中…" : "確認新增"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
