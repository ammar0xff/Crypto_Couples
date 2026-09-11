import { Download, ExternalLink, XCircle } from "lucide-react";

import { Button } from "./ui/button";
import { StatusPill } from "./ui/status-pill";
import { Progress } from "./ui/progress";
import {
  downloadAllUrl,
  TERMINAL_STATUSES,
} from "../lib/endpoints";
import { apiDownloadUrl } from "../lib/api";
import { cn, formatTime } from "../lib/utils";
import type { MediaType, OperationKind, OperationSummary } from "../types";

const MEDIA_LABEL: Record<MediaType, string> = {
  image: "Image",
  audio: "Audio",
  video: "Video",
  file: "File bundle",
};

export function OperationTitle({
  kind,
  media,
}: {
  kind: OperationKind;
  media: MediaType;
}) {
  const verb = kind === "split" ? "Split" : "Reveal";
  return (
    <span className="text-sm font-medium text-text">
      {verb} {MEDIA_LABEL[media]}
    </span>
  );
}

export function OperationItem({
  op,
  onCancel,
  onOpen,
  cancelled,
  highlighted,
}: {
  op: OperationSummary;
  onCancel?: (opId: string) => void;
  onOpen?: () => void;
  cancelled?: boolean;
  highlighted?: boolean;
}) {
  const terminal = TERMINAL_STATUSES.has(op.status);

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border border-border bg-surface p-4",
        highlighted && "border-primary/50",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <OperationTitle kind={op.kind} media={op.media} />
          {op.method && (
            <span className="rounded bg-accent px-1.5 py-0.5 font-mono text-[11px] uppercase text-text-muted">
              {op.method}
            </span>
          )}
          <StatusPill status={op.status} />
        </div>
        <span className="font-mono text-[11px] text-text-faint">
          {op.id}
        </span>
      </div>

      <p className="min-h-4 text-xs text-text-muted">{op.message}</p>

      {!terminal && <Progress value={op.progress} />}

      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-[11px] text-text-faint">
          {formatTime(op.created_at)}
        </span>
        <div className="flex items-center gap-2">
          {op.status === "completed" && (
            <a
              href={apiDownloadUrl(downloadAllUrl(op.id))}
              download
              className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-secondary px-3 text-sm font-medium text-secondary-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              <Download aria-hidden className="size-4" />
              Download all
            </a>
          )}
          {onOpen && (
            <Button variant="ghost" size="sm" onClick={onOpen}>
              <ExternalLink aria-hidden className="size-4" />
              Open
            </Button>
          )}
          {!terminal && onCancel && (
            <Button variant="danger" size="sm" disabled={cancelled} onClick={() => onCancel(op.id)}>
              <XCircle aria-hidden className="size-4" />
              {cancelled ? "Cancelling" : "Cancel"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}