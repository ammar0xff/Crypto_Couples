import { Trash2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { StatusPill } from "../components/ui/status-pill";
import { AppShell } from "../components/layout/app-shell";
import { OperationTitle } from "../components/operation-item";
import {
  useClearHistory,
  useDeleteHistoryEntry,
  useHistory,
  useSystemInfo,
} from "../hooks/use-ops";
import { formatTime } from "../lib/utils";
import type { HistoryEntry } from "../types";

export function SettingsPage() {
  const { health, ffmpeg } = useSystemInfo();
  const history = useHistory();
  const clearHistory = useClearHistory();
  const deleteEntry = useDeleteHistoryEntry();

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">
            Settings
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Backend health, engine availability, and privacy defaults.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Engine</CardTitle>
              <CardDescription>Local backend status.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-text-muted">
              <div className="flex items-center justify-between gap-4">
                <span>API</span>
                {health.isLoading ? (
                  <span className="font-mono text-xs text-text-faint">
                    probing
                  </span>
                ) : health.isError ? (
                  <span className="text-danger">unreachable</span>
                ) : (
                  <StatusPill status="completed" />
                )}
              </div>
              {health.data && (
                <div className="space-y-1 border-t border-border pt-3 font-mono text-xs text-text-faint">
                  <p className="break-all">{health.data.engine}</p>
                  <p>version {health.data.version}</p>
                </div>
              )}

              <div className="flex items-center justify-between gap-4 border-t border-border pt-3">
                <span>ffmpeg</span>
                {ffmpeg.isLoading ? (
                  <span className="font-mono text-xs text-text-faint">
                    probing
                  </span>
                ) : ffmpeg.data?.available ? (
                  <StatusPill status="completed" />
                ) : (
                  <span className="text-text-faint">not available</span>
                )}
              </div>
              {ffmpeg.data?.available && (
                <p className="break-all font-mono text-xs text-text-faint">
                  {ffmpeg.data.path} · {ffmpeg.data.version ?? "unknown"}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Privacy</CardTitle>
              <CardDescription>What this service keeps.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-text-muted">
              <p>Contents: never persisted, processed in memory.</p>
              <p>History: metadata only, cleared on demand.</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex-row items-center justify-between gap-4">
            <div>
              <CardTitle>History</CardTitle>
              <CardDescription>
                Metadata for past runs stored on this machine.
              </CardDescription>
            </div>
            <Button
              variant="danger"
              size="sm"
              disabled={history.data?.length === 0 || clearHistory.isPending}
              onClick={() => clearHistory.mutate()}
            >
              <Trash2 aria-hidden className="size-4" />
              Clear all
            </Button>
          </CardHeader>
          <CardContent>
            {history.isLoading ? (
              <p className="text-sm text-text-faint">Loading history</p>
            ) : history.data?.length === 0 ? (
              <p className="text-sm text-text-faint">
                Nothing recorded yet. History is written when an operation
                reaches a terminal state.
              </p>
            ) : (
              <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
                {history.data?.map((entry) => (
                  <HistoryRow
                    key={entry.id}
                    entry={entry}
                    onDelete={() => deleteEntry.mutate(entry.id)}
                  />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

function HistoryRow({
  entry,
  onDelete,
}: {
  entry: HistoryEntry;
  onDelete: () => void;
}) {
  return (
    <li className="flex items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <OperationTitle kind={entry.kind} media={entry.media} />
          {entry.method && (
            <span className="rounded bg-accent px-1.5 py-0.5 font-mono text-[11px] uppercase text-text-muted">
              {entry.method}
            </span>
          )}
          <StatusPill status={entry.status} />
        </div>
        <p className="truncate font-mono text-[11px] text-text-faint">
          {entry.file_name ?? entry.id} · {formatTime(entry.created_at)}
          {entry.duration_ms != null
            ? ` · ${Math.round(entry.duration_ms / 100) / 10}s`
            : ""}{" "}
          {entry.result_count != null ? ` · ${entry.result_count} file${entry.result_count === 1 ? "" : "s"}` : ""}
        </p>
      </div>
      <button
        onClick={onDelete}
        aria-label={`Delete history entry ${entry.id}`}
        className="inline-flex size-10 shrink-0 items-center justify-center rounded-md text-text-faint transition-colors hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      >
        <Trash2 aria-hidden className="size-4" />
      </button>
    </li>
  );
}