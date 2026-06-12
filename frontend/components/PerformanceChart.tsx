"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { backfillPerformance, getPerformance } from "@/lib/api";
import type { PerformanceHistory, PerformanceRange } from "@/lib/types";

type Metric = "net_profit" | "total_asset" | "roi_pct" | "twr_pct";

const RANGES: PerformanceRange[] = ["1M", "3M", "6M", "1Y", "ALL"];

const METRICS: {
  key: Metric;
  label: string;
  isPercent: boolean;
}[] = [
  { key: "net_profit", label: "純淨利", isPercent: false },
  { key: "total_asset", label: "總資產", isPercent: false },
  { key: "roi_pct", label: "報酬率", isPercent: true },
  { key: "twr_pct", label: "TWR", isPercent: true },
];

function fmtMoney(value: number): string {
  return value.toLocaleString("zh-TW", { maximumFractionDigits: 0 });
}

function fmtValue(value: number, isPercent: boolean): string {
  if (isPercent) return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  return `${value >= 0 ? "+" : ""}$${fmtMoney(value)}`;
}

interface Props {
  /** Bump this to force a reload (e.g. after a new transaction). */
  reloadToken: number;
}

export default function PerformanceChart({ reloadToken }: Props) {
  const [range, setRange] = useState<PerformanceRange>("ALL");
  const [metric, setMetric] = useState<Metric>("net_profit");
  const [history, setHistory] = useState<PerformanceHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [backfilling, setBackfilling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPerformance(range);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法載入績效資料");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    load();
  }, [load, reloadToken]);

  async function handleBackfill() {
    setBackfilling(true);
    setError(null);
    try {
      await backfillPerformance();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "回填歷史失敗");
    } finally {
      setBackfilling(false);
    }
  }

  const metricInfo = METRICS.find((m) => m.key === metric)!;
  const points = history?.points ?? [];
  const latest = points.length > 0 ? points[points.length - 1] : null;
  const first = points.length > 0 ? points[0] : null;

  const latestValue = latest ? latest[metric] : 0;
  const rangeChange =
    latest && first ? latest[metric] - first[metric] : 0;
  const positive = latestValue >= 0;

  const strokeColor = positive ? "#34d399" : "#f87171";
  const fillId = positive ? "perfFillUp" : "perfFillDown";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">績效走勢</h2>
            {history && points.length > 1 && (
              <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                最大回撤 {history.max_drawdown_pct.toFixed(2)}%
              </span>
            )}
          </div>
          <p
            className={clsx(
              "mt-1 text-2xl font-semibold",
              positive ? "text-emerald-400" : "text-red-400"
            )}
          >
            {latest ? fmtValue(latestValue, metricInfo.isPercent) : "—"}
          </p>
          {latest && first && points.length > 1 && (
            <p className="text-xs text-slate-500">
              {range === "ALL" ? "全期間" : `近${range}`} 變化{" "}
              <span
                className={
                  rangeChange >= 0 ? "text-emerald-400" : "text-red-400"
                }
              >
                {fmtValue(rangeChange, metricInfo.isPercent)}
              </span>
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="flex rounded-lg border border-slate-700 p-0.5">
            {METRICS.map((m) => (
              <button
                key={m.key}
                onClick={() => setMetric(m.key)}
                className={clsx(
                  "rounded-md px-3 py-1 text-xs",
                  metric === m.key
                    ? "bg-brand-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="flex rounded-lg border border-slate-700 p-0.5">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={clsx(
                  "rounded-md px-3 py-1 text-xs",
                  range === r
                    ? "bg-slate-700 text-white"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                {r === "ALL" ? "全部" : r}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="px-2 py-4">
        {error && (
          <p className="px-3 pb-3 text-sm text-red-400">{error}</p>
        )}

        {loading && points.length === 0 ? (
          <div className="flex h-64 items-center justify-center text-sm text-slate-500">
            載入中…
          </div>
        ) : points.length <= 1 ? (
          <div className="flex h-64 flex-col items-center justify-center gap-3 text-sm text-slate-500">
            <p>歷史資料不足，可從交易紀錄回填每日快照</p>
            <button
              onClick={handleBackfill}
              disabled={backfilling}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {backfilling ? "回填中…" : "重建歷史走勢"}
            </button>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart
              data={points}
              margin={{ top: 8, right: 16, bottom: 0, left: 8 }}
            >
              <defs>
                <linearGradient id="perfFillUp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#34d399" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="perfFillDown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f87171" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#f87171" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "#1e293b" }}
                minTickGap={48}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={70}
                tickFormatter={(v: number) =>
                  metricInfo.isPercent ? `${v.toFixed(1)}%` : fmtMoney(v)
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(value) => [
                  fmtValue(Number(value), metricInfo.isPercent),
                  metricInfo.label,
                ]}
              />
              <Area
                type="monotone"
                dataKey={metric}
                stroke={strokeColor}
                strokeWidth={2}
                fill={`url(#${fillId})`}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}

        {points.length > 1 && (
          <div className="flex justify-end px-3 pt-2">
            <button
              onClick={handleBackfill}
              disabled={backfilling}
              className="text-xs text-slate-500 hover:text-slate-300 disabled:opacity-50"
              title="從交易紀錄重新計算每日快照"
            >
              {backfilling ? "回填中…" : "↻ 重建歷史走勢"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
