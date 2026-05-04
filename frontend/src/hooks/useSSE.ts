"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { ConnectionStatus, PriceMap } from "@/lib/types";

interface UseSSEOptions {
  url: string;
  onMessage: (data: PriceMap) => void;
}

export function useSSE({ url, onMessage }: UseSSEOptions) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const errorCount = useRef(0);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const es = new EventSource(url);

    es.onopen = () => {
      setStatus("connected");
      errorCount.current = 0;
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PriceMap;
        onMessageRef.current(data);
      } catch {
        // ignore malformed messages
      }
    };

    es.onerror = () => {
      errorCount.current += 1;
      if (errorCount.current >= 5) {
        setStatus("disconnected");
        es.close();
      } else {
        setStatus("connecting");
      }
    };

    return es;
  }, [url]);

  useEffect(() => {
    const es = connect();
    return () => es.close();
  }, [connect]);

  return status;
}
