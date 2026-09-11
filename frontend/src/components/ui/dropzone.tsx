import * as React from "react";

import { cn } from "../../lib/utils";

export interface DropzoneProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "onChange"> {
  files: File[];
  onFilesChange: (files: File[]) => void;
  multiple?: boolean;
  hint?: string;
}

export function Dropzone({
  files,
  onFilesChange,
  multiple = true,
  hint,
  accept,
  disabled,
  className,
  ...props
}: DropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = React.useState(false);

  const addFiles = React.useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      const incoming = Array.from(list);
      onFilesChange(multiple ? [...files, ...incoming] : incoming.slice(-1));
    },
    [files, multiple, onFilesChange],
  );

  return (
    <div
      className={cn("relative", className)}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) addFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        multiple={multiple}
        accept={accept}
        disabled={disabled}
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
        {...props}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex w-full flex-col items-center justify-center gap-1 rounded-lg border border-dashed px-6 py-10 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
          dragging
            ? "border-primary bg-primary/5"
            : "border-border bg-transparent hover:border-text-faint",
          disabled && "pointer-events-none opacity-50",
        )}
      >
        <span className="text-sm font-medium text-text">
          {files.length > 0
            ? `${files.length} file${files.length === 1 ? "" : "s"} selected`
            : "Drop files here or click to browse"}
        </span>
        {hint && <span className="text-xs text-text-faint">{hint}</span>}
      </button>
    </div>
  );
}