"use client";

import clsx from "clsx";
import type { PortfolioSummary as Summary } from "@/lib/types";

function formatMoney(value: number): string {
  return value.toLocaleString("zh-TW", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

interface Props {
  summary: Summary | null;
  todayPnl: number;
}

export default function PortfolioSummary({ summary, todayPnl }: Props) {
  const cards = [
    {
      label: "總資產",
      value: summary ? `$${formatMoney(summary.total_value)}` : "—",
      sub: summary ? `投入成本 $${formatMoney(summary.total_invested)}` : "",
      color: "text-slate-100",
    },
    {
      label: "今日損益",
      value: summary
        ? `${todayPnl >= 0 ? "+" : ""}$${formatMoney(todayPnl)}`
        : "—",
      sub: "依各股當日漲跌計算",
      color: todayPnl >= 0 ? "text-emerald-400" : "text-red-400",
    },
    {
      label: "總損益",
      value: summary
        ? `${summary.total_pnl >= 0 ? "+" : ""}$${formatMoney(summary.total_pnl)}`
        : "—",
      sub: summary
        ? `報酬率 ${summary.total_pnl_pct >= 0 ? "+" : ""}${summary.total_pnl_pct.toFixed(2)}%`
        : "",
      color:
        summary && summary.total_pnl >= 0 ? "text-emerald-400" : "text-red-400",
    },
    {
      label: "持股數量",
      value: summary ? `${summary.holding_count} 檔` : "—",
      sub: "台股 + 美股",
      color: "text-slate-100",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl border border-slate-800 bg-slate-900 p-5"
        >
          <p className="text-sm text-slate-400">{card.label}</p>
          <p className={clsx("mt-2 text-2xl font-semibold", card.color)}>
            {card.value}
          </p>
          {card.sub && <p className="mt-1 text-xs text-slate-500">{card.sub}</p>}
        </div>
      ))}
    </div>
  );
}
