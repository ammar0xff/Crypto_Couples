import { useEffect, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
} from "@tanstack/react-query";

import { apiDelete, apiGet, apiPost, apiUpload, ApiError } from "../lib/api";
import {
  workflowPath,
  TERMINAL_STATUSES,
} from "../lib/endpoints";
import { useOperationsStore } from "../store/operations";
import { subscribeOperationStream } from "../lib/ws";
import type {
  FfmpegStatus,
  HealthResponse,
  HistoryEntry,
  MediaType,
  OperationDetail,
  OperationKind,
  OperationListResponse,
  OperationSummary,
} from "../types";

export function useSystemInfo() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/health"),
    staleTime: 60_000,
    retry: 1,
  });
  const ffmpeg = useQuery({
    queryKey: ["system", "ffmpeg"],
    queryFn: () => apiGet<FfmpegStatus>("/system/ffmpeg"),
    staleTime: 60_000,
    retry: 1,
  });
  return { health, ffmpeg };
}

export function useOperationsList() {
  const upsert = useOperationsStore((s) => s.upsert);
  return useQuery({
    queryKey: ["operations"],
    queryFn: async () => {
      const data = await apiGet<OperationListResponse>("/operations");
      for (const item of data.operations) upsert(item);
      return data.operations;
    },
    refetchInterval: (query) =>
      query.state.data?.some((op) => !TERMINAL_STATUSES.has(op.status))
        ? 2000
        : false,
  });
}

export function useOperationDetail(opId: string | null) {
  return useQuery({
    queryKey: ["operations", opId],
    queryFn: () => apiGet<OperationDetail>(`/operations/${opId}`),
    enabled: Boolean(opId),
    refetchInterval: (query) =>
      query.state.data && !TERMINAL_STATUSES.has(query.state.data.status)
        ? 2000
        : false,
  });
}

export function useCancelOperation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (opId: string) =>
      apiPost<OperationSummary>(`/operations/${opId}/cancel`),
    onSuccess: (summary) => {
      useOperationsStore.getState().upsert(summary);
      void queryClient.invalidateQueries({ queryKey: ["operations"] });
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });
}

export function useClearHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiDelete("/history"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });
}

export function useDeleteHistoryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (opId: string) => apiDelete(`/history/${opId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });
}

export function useHistory() {
  return useQuery({
    queryKey: ["history"],
    queryFn: async () => {
      const data = await apiGet<{ history: HistoryEntry[] }>("/history");
      return data.history;
    },
  });
}

export function useSubmitWorkflow(media: MediaType, kind: OperationKind) {
  const upsert = useOperationsStore((s) => s.upsert);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      files,
      options,
    }: {
      files: File[];
      options: Record<string, unknown>;
    }) => {
      const summary = await apiUpload<OperationSummary>(
        workflowPath(media, kind),
        files,
        options,
      );
      return summary;
    },
    onSuccess: (summary) => {
      upsert(summary);
      void queryClient.invalidateQueries({ queryKey: ["operations"] });
    },
  });
}

export function useOperationStream(opId: string | null) {
  const applyEvent = useOperationsStore((s) => s.applyEvent);
  const upsert = useOperationsStore((s) => s.upsert);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!opId) return;
    let unsubscribe: (() => void) | undefined;
    let poll: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;

    const stopPolling = () => {
      if (poll) clearInterval(poll);
    };

    const startPolling = () => {
      if (poll) return;
      poll = setInterval(async () => {
        try {
          const detail = await apiGet<OperationDetail>(`/operations/${opId}`);
          if (cancelled) return;
          upsert({
            id: detail.id,
            kind: detail.kind,
            media: detail.media,
            method: detail.method,
            status: detail.status,
            progress: detail.progress,
            message: detail.message,
            created_at: detail.created_at,
            updated_at: detail.updated_at,
          });
          if (TERMINAL_STATUSES.has(detail.status)) stopPolling();
        } catch (error) {
          if (error instanceof ApiError && error.status === 404) stopPolling();
        }
      }, 2500);
    };

    unsubscribe = subscribeOperationStream(opId, {
      onSnapshot: (summary) =>
        cancelled ? undefined : void upsert(summary),
      onEvent: (event) =>
        cancelled ? undefined : applyEvent(opId, event),
      onStatus: (isConnected) => {
        if (cancelled) return;
        setConnected(isConnected);
        if (!isConnected) startPolling();
        else stopPolling();
      },
    });

    return () => {
      cancelled = true;
      unsubscribe?.();
      stopPolling();
    };
  }, [opId, upsert, applyEvent]);

  return connected;
}

export type { UseMutationResult };