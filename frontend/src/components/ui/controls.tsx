import * as React from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "../../lib/utils";

const inputBase =
  "h-11 w-full rounded-md border border-border bg-elevated px-3 text-sm text-text placeholder:text-text-faint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <div className="relative">
    <select
      ref={ref}
      className={cn(inputBase, "appearance-none pr-9 [&>option]:bg-elevated", className)}
      {...props}
    >
      {children}
    </select>
    <ChevronDown
      aria-hidden
      className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-text-faint"
    />
  </div>
));
Select.displayName = "Select";

export const NumberInput = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    type="number"
    className={cn(
      inputBase,
      "font-mono tabular-nums [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
      className,
    )}
    {...props}
  />
));
NumberInput.displayName = "NumberInput";

export const TextInput = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input ref={ref} type="text" className={cn(inputBase, className)} {...props} />
));
TextInput.displayName = "TextInput";

export function Checkbox({
  className,
  label,
  disabled,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-center gap-3 py-1 text-sm text-text select-none",
        disabled && "pointer-events-none opacity-50",
        className,
      )}
    >
      <input
        type="checkbox"
        className="size-4 shrink-0 rounded border-border bg-elevated accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        {...props}
      />
      <span>{label}</span>
    </label>
  );
}

export function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-text-muted">{label}</span>
      <span className="font-mono tabular-nums text-text">{value}</span>
    </div>
  );
}

export function FieldError({ id, message }: { id?: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="text-xs text-danger">
      {message}
    </p>
  );
}