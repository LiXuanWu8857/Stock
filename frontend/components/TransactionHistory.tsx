"use client";

import clsx from "clsx";
import type { Transaction } from "@/lib/types";

function fmt(value: number, digits = 2): string {
  return value.toLocaleString("zh-TW", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

interface Props {
  transactions: Transaction[];
  loading: boolean;
}

export default function TransactionHistory({ transactions, loading }: Props) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-5 py-4">
        <h2 className="text-lg font-semibold">交易紀錄</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 font-medium">日期</th>
              <th className="px-5 py-3 font-medium">股票</th>
              <th className="px-5 py-3 font-medium">市場</th>
              <th className="px-5 py-3 font-medium">動作</th>
              <th className="px-5 py-3 font-medium">價格</th>
              <th className="px-5 py-3 font-medium">股數</th>
              <th className="px-5 py-3 font-medium">金額</th>
            </tr>
          </thead>
          <tbody>
            {loading && transactions.length === 0 ? (
              [...Array(3)].map((_, i) => (
                <tr key={i} className="border-b border-slate-800/50">
                  {[...Array(7)].map((_, j) => (
                    <td key={j} className="px-5 py-4">
                      <div className="h-4 animate-pulse rounded bg-slate-800" />
                    </td>
                  ))}
                </tr>
              ))
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-slate-500">
                  尚無交易紀錄
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const price = parseFloat(tx.price);
                const shares = parseFloat(tx.shares);
                return (
                  <tr
                    key={tx.id}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30"
                  >
                    <td className="px-5 py-4 text-slate-300">{tx.date}</td>
                    <td className="px-5 py-4 font-mono font-medium">
                      {tx.symbol}
                    </td>
                    <td className="px-5 py-4 text-slate-400">
                      {tx.market === "TW" ? "台股" : "美股"}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={clsx(
                          "rounded px-2 py-0.5 text-xs font-medium",
                          tx.action === "BUY"
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-red-500/15 text-red-400"
                        )}
                      >
                        {tx.action === "BUY" ? "買入" : "賣出"}
                      </span>
                    </td>
                    <td className="px-5 py-4">{fmt(price)}</td>
                    <td className="px-5 py-4">{fmt(shares, 0)}</td>
                    <td className="px-5 py-4">{fmt(price * shares)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
