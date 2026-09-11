import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { AppShell } from "../components/layout/app-shell";

export function SettingsPage() {
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
            <CardContent className="space-y-2 text-sm text-text-muted">
              <p>Python engine: detected at import.</p>
              <p>ffmpeg: probe result lands with the data layer in P11.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Privacy</CardTitle>
              <CardDescription>What this service keeps.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-text-muted">
              <p>Contents: never stored, processed in memory.</p>
              <p>History: metadata only, cleared on demand.</p>
              <p>
                <Button variant="ghost" size="sm" className="h-9 px-2 text-danger hover:bg-danger/10">
                  Clear history
                </Button>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}