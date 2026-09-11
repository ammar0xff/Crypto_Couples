import { useMemo } from "react";
import { Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { buttonVariants } from "../components/ui/button";
import { OperationItem } from "../components/operation-item";
import { AppShell } from "../components/layout/app-shell";
import { useCancelOperation, useOperationsList } from "../hooks/use-ops";
import { useOperationsStore } from "../store/operations";
import { cn } from "../lib/utils";
import type { OperationSummary } from "../types";

export function OperationsPage() {
  const query = useOperationsList();
  const storeOps = useOperationsStore((s) => s.ops);
  const cancel = useCancelOperation();

  const items = useMemo(() => {
    const merged = new Map<string, OperationSummary>();
    for (const op of query.data ?? []) merged.set(op.id, storeOps[op.id] ?? op);
    for (const op of Object.values(storeOps)) merged.set(op.id, op);
    return [...merged.values()].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    );
  }, [query.data, storeOps]);

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-text">
              Operations
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              Live split and reveal runs, with real-time progress where a
              socket is available.
            </p>
          </div>
          <Link
            to="/split"
            className={cn(buttonVariants({ variant: "secondary" }))}
          >
            <Plus aria-hidden />
            New split
          </Link>
        </div>

        <Card>
          <CardHeader className="flex-row items-center justify-between gap-4">
            <div>
              <CardTitle>Recent runs</CardTitle>
              <CardDescription>
                Refreshes every two seconds while something is active.
              </CardDescription>
            </div>
            {items.length > 0 && (
              <button
                onClick={clearDisplay}
                className="text-xs text-text-faint transition-colors hover:text-danger focus-visible:outline-none"
              >
                Clear display
              </button>
            )}
          </CardHeader>
          <CardContent>
            {items.length === 0 ? (
              <div className="flex items-center justify-between gap-4 rounded-lg border border-dashed border-border px-4 py-6 text-sm text-text-faint">
                <span>No operations yet</span>
                <Link
                  to="/split"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  Start one from the split page
                </Link>
              </div>
            ) : (
              <ul className="flex flex-col gap-3">
                {items.map((op) => (
                  <li key={op.id}>
                    <OperationItem
                      op={op}
                      onCancel={(oid) => cancel.mutate(oid)}
                      cancelled={cancel.isPending}
                    />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

function clearDisplay() {
  const ids = Object.keys(useOperationsStore.getState().ops);
  ids.forEach((id) => useOperationsStore.getState().remove(id));
}