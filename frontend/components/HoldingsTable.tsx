"use client";

import clsx from "clsx";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import type { Holding, Quote } from "@/lib/types";

function fmt(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("zh-TW", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function PnlCell({ value, pct }: { value: number | null; pct: number | null }) {
  if (value === null) return <span className="text-slate-500">—</span>;
  const positive = value >= 0;
  return (
    <span className={positive ? "text-emerald-400" : "text-red-400"}>
      {positive ? "+" : ""}
      {fmt(value)}
      {pct !== null && (
        <span className="ml-1 text-xs opacity-80">
          ({positive ? "+" : ""}
          {pct.toFixed(2)}%)
        </span>
      )}
    </span>
  );
}

interface Props {
  holdings: Holding[];
  liveQuotes: Record<string, Quote>;
  loading: boolean;
  onRefresh: () => void;
  onDelete: (id: number) => void;
}

export default function HoldingsTable({
  holdings,
  liveQuotes,
  loading,
  onRefresh,
  onDelete,
}: Props) {
  const headers = [
    "股票代號",
    "名稱",
    "市場",
    "持股數",
    "成本價",
    "現價",
    "市值",
    "損益",
    "報酬率",
    "佔比",
    "",
  ];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
        <h2 className="text-lg font-semibold">持股清單</h2>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
        >
          <ArrowPathIcon
            className={clsx("h-4 w-4", loading && "animate-spin")}
          />
          重新整理
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
              {headers.map((h, i) => (
                <th key={i} className="px-5 py-3 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && holdings.length === 0 ? (
              [...Array(3)].map((_, i) => (
                <tr key={i} className="border-b border-slate-800/50">
                  {headers.map((_, j) => (
                    <td key={j} className="px-5 py-4">
                      <div className="h-4 animate-pulse rounded bg-slate-800" />
                    </td>
                  ))}
                </tr>
              ))
            ) : holdings.length === 0 ? (
              <tr>
                <td
                  colSpan={headers.length}
                  className="px-5 py-12 text-center text-slate-500"
                >
                  尚無持股，點擊「新增持股」開始記錄
                </td>
              </tr>
            ) : (
              holdings.map((h) => {
                const key = `${h.symbol}:${h.market}`;
                const live = liveQuotes[key];
                const isExtended = live?.is_extended ?? false;
                const price = live?.price ?? h.current_price;
                const shares = parseFloat(h.shares);
                const avgCost = parseFloat(h.avg_cost);
                const costBasis = shares * avgCost;
                const value = price !== null ? shares * price : null;
                const pnl = value !== null ? value - costBasis : null;
                const pnlPct =
                  pnl !== null && costBasis > 0 ? (pnl / costBasis) * 100 : null;

                return (
                  <tr
                    key={h.id}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30"
                  >
                    <td className="px-5 py-4 font-mono font-medium">
                      {h.symbol}
                    </td>
                    <td className="max-w-[180px] truncate px-5 py-4 text-slate-300">
                      {h.stock_name || live?.name || "—"}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={clsx(
                          "rounded px-2 py-0.5 text-xs font-medium",
                          h.market === "TW"
                            ? "bg-blue-500/15 text-blue-400"
                            : "bg-purple-500/15 text-purple-400"
                        )}
                      >
                        {h.market === "TW" ? "台股" : "美股"}
                      </span>
                    </td>
                    <td className="px-5 py-4">{fmt(shares, 0)}</td>
                    <td className="px-5 py-4">{fmt(avgCost)}</td>
                    <td className="px-5 py-4 font-medium">
                      {fmt(price)}
                      {isExtended && price !== null && (
                        <span className="ml-1.5 rounded bg-amber-500/15 px-1 py-0.5 text-[10px] text-amber-400">
                          盤{live?.change_pct !== null && (live?.change_pct ?? 0) > 0 ? "前" : "後"}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4">{fmt(value)}</td>
                    <td className="px-5 py-4">
                      <PnlCell value={pnl} pct={null} />
                    </td>
                    <td className="px-5 py-4">
                      {pnlPct !== null ? (
                        <span
                          className={
                            pnlPct >= 0 ? "text-emerald-400" : "text-red-400"
                          }
                        >
                          {pnlPct >= 0 ? "+" : ""}
                          {pnlPct.toFixed(2)}%
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-5 py-4 text-slate-400">
                      {h.weight !== null ? `${h.weight.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-5 py-4">
                      <button
                        onClick={() => onDelete(h.id)}
                        className="text-slate-600 hover:text-red-400"
                        title="刪除持股"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </td>
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
