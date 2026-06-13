"use client";

import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/lib/api";
import type { Quote, QuotesMessage } from "@/lib/types";

const RECONNECT_DELAY_MS = 5000;

/**
 * Subscribes to live quotes over WebSocket.
 * `symbolKeys` are in "SYMBOL:MARKET" format, e.g. ["2330:TW", "AAPL:US"].
 * Reconnects automatically when the connection drops.
 */
export function useQuotesWebSocket(symbolKeys: string[]) {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const symbolsRef = useRef<string[]>(symbolKeys);
  symbolsRef.current = symbolKeys;

  // Stable key so the effect only re-runs when the symbol set actually changes
  const symbolsKey = [...symbolKeys].sort().join(",");

  useEffect(() => {
    let disposed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (disposed) return;

      const ws = new WebSocket(`${WS_BASE}/ws/quotes`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        ws.send(JSON.stringify({ symbols: symbolsRef.current }));
      };

      ws.onmessage = (event) => {
        try {
          const msg: QuotesMessage = JSON.parse(event.data);
          if (msg.type === "quotes" && msg.data) {
            setQuotes((prev) => ({ ...prev, ...msg.data }));
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!disposed) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    if (symbolKeys.length > 0) {
      connect();
    }

    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolsKey]);

  // Push updated subscription list over the existing connection
  useEffect(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ symbols: symbolKeys }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolsKey]);

  return { quotes, connected };
}
