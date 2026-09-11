import type { OperationStatus } from "../../types";
import { cn } from "../../lib/utils";

const STATUS_META: Record<
  OperationStatus,
  { label: string; dot: string; announcement?: boolean }
> = {
  queued: { label: "Queued", dot: "bg-text-faint" },
  uploading: { label: "Uploading", dot: "bg-info" },
  processing: {
    label: "Processing",
    dot: "bg-primary",
    announcement: true,
  },
  completed: { label: "Completed", dot: "bg-success" },
  failed: { label: "Failed", dot: "bg-danger" },
  cancelled: { label: "Cancelled", dot: "bg-text-faint" },
  expired: { label: "Expired", dot: "bg-text-faint" },
};

export function StatusPill({
  status,
  className,
}: {
  status: OperationStatus;
  className?: string;
}) {
  const meta = STATUS_META[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-sm text-text-muted",
        className,
      )}
      aria-label={meta.label}
    >
      <span
        aria-hidden
        className={cn("size-2 rounded-full", meta.dot)}
      />
      {meta.label}
    </span>
  );
}