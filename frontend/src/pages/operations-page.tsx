import { Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { buttonVariants } from "../components/ui/button";
import { AppShell } from "../components/layout/app-shell";
import { cn } from "../lib/utils";

export function OperationsPage() {
  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-text">
              Operations
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              Live split and reveal runs on this backend, with real-time progress.
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
          <CardHeader>
            <CardTitle>Recent runs</CardTitle>
            <CardDescription>
              Operation pool wiring lands in P11, fed by REST and WebSocket.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-text-faint">
              <EmptyRow />
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

function EmptyRow() {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-dashed border-border px-4 py-6">
      <span>No operations yet</span>
      <span
        role="status"
        aria-hidden
        className="h-2 w-10 rounded-full bg-accent"
      />
    </div>
  );
}