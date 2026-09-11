import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Combine, Download, ShieldAlert } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Dropzone } from "../components/ui/dropzone";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { AppShell } from "../components/layout/app-shell";

type Step = "uploads" | "working" | "result";

export function RevealPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("uploads");
  const [files, setFiles] = useState<File[]>([]);

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">
            Reveal from shares
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Stack the shares back together to restore the original secret.
          </p>
        </div>

        <ol
          className="flex items-center gap-2 text-sm"
          aria-label="Reveal steps"
        >
          {(["uploads", "working", "result"] as const).map((s, i) => {
            const labels: Record<Step, string> = {
              uploads: "Submit shares",
              working: "Reconstruct",
              result: "Download",
            };
            const active = s === step;
            const done = i < (["uploads", "working", "result"] as const).indexOf(step);
            return (
              <li key={s} className="flex items-center gap-2">
                <span
                  className={done ? "text-primary" : active ? "text-text" : "text-text-faint"}
                >
                  {i + 1}. {labels[s]}
                </span>
                {i < 2 && <span className="text-text-faint" aria-hidden>|</span>}
              </li>
            );
          })}
        </ol>

        {step === "uploads" && (
          <Card>
            <CardHeader>
              <CardTitle>Shares</CardTitle>
              <CardDescription>
                Every share you captured. All of them are required to reveal.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Dropzone
                files={files}
                onFilesChange={setFiles}
                multiple
                accept=".png,.share,.zip,.shard"
                hint="PNG shares, ZIP bundles, or file shards"
                aria-label="Share files"
              />
              <Button
                size="lg"
                disabled={files.length < 2}
                onClick={() => setStep("working")}
              >
                <Combine aria-hidden />
                Reconstruct
              </Button>
            </CardContent>
          </Card>
        )}

        {step === "working" && (
          <Card>
            <CardHeader>
              <CardTitle>Reconstructing</CardTitle>
              <CardDescription>
                The backend is stacking your shares in memory.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Progress value={68} />
              <Button variant="secondary" onClick={() => setStep("result")}>
                <Download aria-hidden />
                Skip to result
              </Button>
            </CardContent>
          </Card>
        )}

        {step === "result" && (
          <Card>
            <CardHeader>
              <CardTitle>Secret restored</CardTitle>
              <CardDescription>
                The reconstructed payload is below, produced entirely on this run.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-start gap-4">
              <div className="grid w-full place-items-center rounded-lg border border-border bg-elevated p-8">
                <ShieldAlert className="size-8 text-text-faint" aria-hidden />
                <p className="mt-2 text-xs text-text-faint">
                  Preview pixel grid arrives in P13.
                </p>
              </div>
              <Button size="lg" onClick={() => navigate("/operations")}>
                <Download aria-hidden />
                Save attachment
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}