import { useCallback, useEffect, useMemo, useState } from "react";
import { FormProvider, useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Combine, RotateCcw, Wifi } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Tabs } from "../components/ui/tabs";
import { Dropzone } from "../components/ui/dropzone";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { StatusPill } from "../components/ui/status-pill";
import { Stepper } from "../components/ui/stepper";
import { AppShell } from "../components/layout/app-shell";
import { RevealOptionsPanel } from "../components/options-panel";
import { ShareList } from "../components/share-list";
import {
  useOperationDetail,
  useOperationStream,
  useSubmitWorkflow,
} from "../hooks/use-ops";
import { useOperationsStore } from "../store/operations";
import { ApiError } from "../lib/api";
import { optionsMeta, toSplitOptions, type OptionValues } from "../lib/options";
import { MEDIA_TYPES, type MediaType } from "../types";

type Step = "uploads" | "working" | "result";

const STEPS = [
  { key: "uploads", label: "Submit shares" },
  { key: "working", label: "Reconstruct" },
  { key: "result", label: "Download" },
];

const ACCEPT_HINT: Record<MediaType, string> = {
  image: "PNG shares (split or reveal sets)",
  audio: "WAV shares or ZIP bundle",
  video: "ZIP bundle of frame shares",
  file: "Shard files from a file split",
};

export function RevealPage() {
  const [media, setMedia] = useState<MediaType>("image");
  const [step, setStep] = useState<Step>("uploads");
  const [files, setFiles] = useState<File[]>([]);
  const [opId, setOpId] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const meta = useMemo(() => optionsMeta(media, "reveal"), [media]);
  const form = useForm<OptionValues>({
    resolver: zodResolver(meta.schema) as unknown as Resolver<OptionValues>,
    defaultValues: meta.defaults as OptionValues,
    mode: "onSubmit",
  });

  useEffect(() => {
    form.reset(meta.defaults as OptionValues);
  }, [form, media]);

  const submit = useSubmitWorkflow(media, "reveal");

  const detail = useOperationDetail(opId);
  const connected = useOperationStream(opId);
  const stored = useOperationsStore((s) => (opId ? s.ops[opId] : undefined));

  const status = detail.data?.status ?? stored?.status ?? "queued";
  const progress = detail.data?.progress ?? stored?.progress ?? 0;
  const message = detail.data?.message ?? stored?.message ?? "";

  const reset = useCallback(() => {
    setStep("uploads");
    setOpId(null);
    setFailure(null);
    setFiles([]);
  }, []);

  useEffect(() => {
    if (step !== "working" || !detail.data) return;
    if (detail.data.status === "completed") {
      setStep("result");
    } else if (
      detail.data.status === "failed" ||
      detail.data.status === "cancelled"
    ) {
      setFailure(detail.data.error?.message ?? detail.data.message);
    }
  }, [detail.data, step]);

  const onValid = useCallback(
    (values: OptionValues) => {
      submit.mutate(
        { files, options: toSplitOptions(values) },
        {
          onSuccess: (summary) => {
            setOpId(summary.id);
            setFailure(null);
            setStep("working");
          },
          onError: () => setStep("uploads"),
        },
      );
    },
    [submit, files],
  );

  const submitError = submit.error
    ? submit.error instanceof ApiError
      ? submit.error.message
      : "The backend rejected the request."
    : null;

  const stepIndex = STEPS.findIndex((s) => s.key === step);

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

        <Stepper steps={STEPS} current={stepIndex} />

        {step === "uploads" && (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
            <Card>
              <CardHeader>
                <CardTitle>Shares</CardTitle>
                <CardDescription>
                  Every share you captured. All of them are required to reveal.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Tabs
                  value={media}
                  onValueChange={(v) => setMedia(v as MediaType)}
                  items={MEDIA_TYPES.map((m) => ({
                    value: m,
                    label: m[0].toUpperCase() + m.slice(1),
                  }))}
                />
                <Dropzone
                  files={files}
                  onFilesChange={setFiles}
                  multiple
                  hint={ACCEPT_HINT[media]}
                  aria-label="Share files"
                />
                {submitError && (
                  <p role="alert" className="text-sm text-danger">
                    {submitError}
                  </p>
                )}
              </CardContent>
            </Card>

            <FormProvider {...form}>
              <form
                className="flex flex-col gap-6"
                onSubmit={form.handleSubmit(onValid)}
                noValidate
              >
                <Card>
                  <CardHeader>
                    <CardTitle>Reveal controls</CardTitle>
                    <CardDescription>
                      The algorithm must match how the shares were made.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <RevealOptionsPanel media={media} />
                  </CardContent>
                </Card>

                <Button
                  size="lg"
                  type="submit"
                  disabled={files.length < 2 || submit.isPending}
                >
                  <Combine aria-hidden />
                  {submit.isPending ? "Starting" : "Reconstruct"}
                </Button>
              </form>
            </FormProvider>
          </div>
        )}

        {step === "working" && (
          <Card>
            <CardHeader>
              <CardTitle>Reconstructing</CardTitle>
              <CardDescription>
                {connected ? (
                  <span className="inline-flex items-center gap-1.5 text-info">
                    <Wifi aria-hidden className="size-3.5" />
                    Live progress connected
                  </span>
                ) : (
                  "Polling the backend, no live socket."
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <StatusPill status={status} />
                <span className="font-mono text-xs text-text-faint">{opId}</span>
              </div>
              <Progress value={progress} />
              <p role="status" className="text-sm text-text-muted">
                {message}
              </p>

              {failure && (
                <div
                  role="alert"
                  className="flex flex-col items-start gap-3 rounded-lg border border-danger/40 bg-danger/5 p-4"
                >
                  <p className="text-sm text-danger">{failure}</p>
                  <Button variant="secondary" size="sm" onClick={reset}>
                    <RotateCcw aria-hidden className="size-4" />
                    Try again
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {step === "result" && opId && detail.data && (
          <Card>
            <CardHeader>
              <CardTitle>Secret restored</CardTitle>
              <CardDescription>
                The reconstructed payload is below, produced entirely on this
                run.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <ShareList
                opId={opId}
                files={detail.data.result_files}
                title="Restored files"
              />
              <Button variant="secondary" onClick={reset}>
                <RotateCcw aria-hidden className="size-4" />
                Reveal another
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}