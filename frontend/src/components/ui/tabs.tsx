import * as React from "react";

import { cn } from "../../lib/utils";

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  items: { value: string; label: string; icon?: React.ReactNode }[];
  className?: string;
}

export function Tabs({ value, onValueChange, items, className }: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn("flex items-center gap-1 border-b border-border", className)}
    >
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            aria-selected={selected}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "relative -mb-px inline-flex h-11 items-center gap-2 px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
              selected
                ? "text-text after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary"
                : "text-text-muted hover:text-text",
            )}
          >
            {item.icon}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}