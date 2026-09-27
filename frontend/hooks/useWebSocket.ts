"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, wsUrl } from "@/lib/api";

export type StreamMessage = {
  event: string;
  progress?: number;
  node?: string;
  status?: string;
  latest_message?: string;
  agents?: Record<string, {status:string; latest_message:string; elapsed_seconds?:number}>;
  job?: {status:string; progress:number; agents?:Record<string,{status:string;latest_message:string;elapsed_seconds?:number}>};
  message?: string;
  job_id?: string;
};

const MAX_RECONNECTS = 5;

export function useWebSocket(path: string | null) {
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    let terminal = false;
    let attempts = 0;

    const loadSnapshot = async () => {
      try {
        const snapshot = await apiFetch<StreamMessage["job"]>(path.replace(/\/stream$/, ""));
        if (!cancelled) {
          setMessages((prev) => [...prev, { event: "snapshot", job: snapshot, progress: snapshot?.progress, agents: snapshot?.agents }]);
        }
      } catch {
        // The WebSocket remains the primary stream; snapshot loading is only a fallback.
      }
    };

    const connect = () => {
      if (cancelled || terminal) return;
      try {
        const socket = new WebSocket(wsUrl(path));
        socketRef.current = socket;
        socket.onopen = () => { attempts = 0; setConnected(true); setError(""); };
        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as StreamMessage;
            setMessages((prev) => [...prev, data]);
            if (data.event === "complete" || data.event === "error") terminal = true;
          } catch {
            setError("Received an invalid analysis event");
          }
        };
        socket.onerror = () => setError("Live stream temporarily unavailable; retrying…");
        socket.onclose = () => {
          setConnected(false);
          if (cancelled || terminal) return;
          if (attempts < MAX_RECONNECTS) {
            const delay = Math.min(1000 * 2 ** attempts, 8000);
            attempts += 1;
            reconnectTimerRef.current = setTimeout(connect, delay);
          } else {
            setError("Live stream unavailable. Showing the latest server snapshot where possible.");
            void loadSnapshot();
          }
        };
      } catch {
        setConnected(false);
        setError("Unable to open the live analysis stream");
      }
    };

    setMessages([]);
    setError("");
    void loadSnapshot();
    connect();

    return () => {
      cancelled = true;
      terminal = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [path]);

  return { messages, connected, error };
}
