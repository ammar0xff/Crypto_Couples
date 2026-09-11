import { create } from "zustand";
import type { OperationEvent, OperationSummary } from "../types";

interface OperationsState {
  ops: Record<string, OperationSummary>;
  upsert: (summary: OperationSummary) => void;
  applyEvent: (opId: string, event: OperationEvent) => void;
  remove: (opId: string) => void;
  reset: () => void;
}

function statusForEvent(
  event: OperationEvent,
  base?: OperationSummary,
): OperationSummary["status"] {
  switch (event.type) {
    case "completed":
      return "completed";
    case "cancelled":
      return "cancelled";
    case "error":
      return "failed";
    default:
      return base?.status ?? "processing";
  }
}

export const useOperationsStore = create<OperationsState>((set) => ({
  ops: {},
  upsert: (summary) =>
    set((state) => ({ ops: { ...state.ops, [summary.id]: summary } })),
  applyEvent: (opId, event) =>
    set((state) => {
      const base = state.ops[opId];
      const merged: OperationSummary = {
        id: opId,
        kind: base?.kind ?? "split",
        media: base?.media ?? "file",
        method: base?.method ?? null,
        status: statusForEvent(event, base),
        progress: event.progress ?? base?.progress ?? 0,
        message:
          event.type === "error"
            ? event.error?.message ?? event.message ?? base?.message ?? ""
            : event.message ?? event.error?.message ?? base?.message ?? "",
        created_at: base?.created_at ?? new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      return { ops: { ...state.ops, [opId]: merged } };
    }),
  remove: (opId) =>
    set((state) => {
      const ops = { ...state.ops };
      delete ops[opId];
      return { ops };
    }),
  reset: () => set({ ops: {} }),
}));