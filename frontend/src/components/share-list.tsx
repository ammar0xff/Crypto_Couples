import { Download, Package } from "lucide-react";
import { apiDownloadUrl } from "../lib/api";
import { downloadAllUrl, downloadFileUrl } from "../lib/endpoints";
import { formatBytes } from "../lib/utils";
import type { ResultFile } from "../types";

export function ShareList({
  opId,
  files,
  title,
}: {
  opId: string;
  files: ResultFile[];
  title?: string;
}) {
  if (files.length === 0) {
    return (
      <div className="grid place-items-center rounded-lg border border-dashed border-border py-10 text-sm text-text-faint">
        No output files
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-text">
          {title ?? `${files.length} output file${files.length === 1 ? "" : "s"}`}
        </p>
        <a
          href={apiDownloadUrl(downloadAllUrl(opId))}
          download
          className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-secondary px-3 text-sm font-medium text-secondary-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          <Package aria-hidden className="size-4" />
          Download all
        </a>
      </div>

      <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
        {files.map((file) => (
          <li
            key={file.name}
            className="flex items-center justify-between gap-3 px-4 py-3"
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="truncate font-mono text-xs text-text">
                {file.name}
              </span>
              <span className="font-mono text-[11px] text-text-faint">
                {formatBytes(file.size)}
              </span>
            </div>
            <a
              href={apiDownloadUrl(downloadFileUrl(opId, file.name))}
              download={file.name}
              className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium text-text transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              <Download aria-hidden className="size-4" />
              Save
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}