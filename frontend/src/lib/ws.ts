import type { OperationEvent, OperationSummary } from "../types";

const WS_BASE =
  (import.meta.env.VITE_WS_URL as string | undefined)?.replace(/\/$/, "") ??
  `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api`;

const TERMINAL = new Set(["completed", "failed", "cancelled", "expired"]);

export interface StreamHandlers {
  onEvent?: (event: OperationEvent) => void;
  onSnapshot?: (summary: OperationSummary) => void;
  onStatus?: (connected: boolean) => void;
}

export function operationStreamUrl(opId: string): string {
  return `${WS_BASE}/operations/${opId}/ws`;
}

export function subscribeOperationStream(
  opId: string,
  handlers: StreamHandlers,
): () => void {
  let socket: WebSocket | null = null;
  let closed = false;
  let attempts = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  const maxAttempts = 6;

  const stop = () => {
    closed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (socket) {
      socket.onclose = null;
      socket.close();
    }
    handlers.onStatus?.(false);
  };

  const open = () => {
    if (closed) return;
    attempts += 1;
    socket = new WebSocket(operationStreamUrl(opId));
    socket.onopen = () => {
      attempts = 0;
      handlers.onStatus?.(true);
    };
    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data as string);
        if (data.type === undefined && data.snapshot) {
          handlers.onSnapshot?.(data.snapshot as OperationSummary);
          return;
        }
        if (typeof data.type !== "string") return;
        const event: OperationEvent = data;
        handlers.onEvent?.(event);
        if (TERMINAL.has(event.type)) stop();
      } catch {
        // ignore malformed frames
      }
    };
    socket.onclose = () => {
      handlers.onStatus?.(false);
      if (closed) return;
      const delay = Math.min(400 * 2 ** attempts, 4000);
      reconnectTimer = setTimeout(open, delay);
      if (attempts >= maxAttempts) stop();
    };
    socket.onerror = () => socket?.close();
  };

  open();
  return stop;
}