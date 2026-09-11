import { useCallback, useEffect, useMemo, useState } from "react";
import { FormProvider, useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { SplitSquareVertical } from "lucide-react";

import { Tabs } from "../components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Dropzone } from "../components/ui/dropzone";
import { Button } from "../components/ui/button";
import { AppShell } from "../components/layout/app-shell";
import { SplitOptionsPanel } from "../components/options-panel";
import { RecipeCard } from "../components/recipe-card";
import { useSubmitWorkflow } from "../hooks/use-ops";
import { ApiError } from "../lib/api";
import { optionsMeta, toSplitOptions, type OptionValues } from "../lib/options";
import { MEDIA_TYPES, type MediaType } from "../types";

export function SplitPage() {
  const navigate = useNavigate();
  const [media, setMedia] = useState<MediaType>("image");
  const [files, setFiles] = useState<File[]>([]);

  const meta = useMemo(() => optionsMeta(media, "split"), [media]);
  const form = useForm<OptionValues>({
    resolver: zodResolver(meta.schema) as unknown as Resolver<OptionValues>,
    defaultValues: meta.defaults as OptionValues,
    mode: "onSubmit",
  });

  useEffect(() => {
    form.reset(meta.defaults as OptionValues);
  }, [form, media]);

  const submit = useSubmitWorkflow(media, "split");

  const ready = files.length > 0 && (media !== "image" || files.length === 1);

  const onValid = useCallback(
    (values: OptionValues) => {
      submit.mutate(
        { files, options: toSplitOptions(values) },
        {
          onSuccess: () => navigate("/operations"),
        },
      );
    },
    [submit, files, navigate],
  );

  const watched = form.watch();
  const errorMessage = submit.error
    ? submit.error instanceof ApiError
      ? submit.error.message
      : "The backend rejected the request."
    : null;

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">
            Split a secret
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Turn one secret into shares that must be stacked together to reveal
            it.
          </p>
        </div>

        <Tabs
          value={media}
          onValueChange={(v) => setMedia(v as MediaType)}
          items={MEDIA_TYPES.map((m) => ({
            value: m,
            label: m[0].toUpperCase() + m.slice(1),
          }))}
        />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <CardHeader>
              <CardTitle>Source</CardTitle>
              <CardDescription>
                The file holding the secret. Uploads stay on this machine only
                for the life of the operation.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Dropzone
                files={files}
                onFilesChange={setFiles}
                multiple={media === "file"}
                hint={
                  media === "file"
                    ? "Multiple files become one share set"
                    : "Exactly one source file"
                }
                aria-label="Source files"
              />
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
                  <CardTitle>Engine controls</CardTitle>
                  <CardDescription>
                    Algorithm parameters, confirmed before processing.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <SplitOptionsPanel media={media} />
                </CardContent>
              </Card>

              <RecipeCard
                media={media}
                kind="split"
                rows={recipeRows(media, watched)}
                note="For demonstration only. The CSPRNG shuffle is not for real secrets."
              />

              {errorMessage && (
                <p role="alert" className="text-sm text-danger">
                  {errorMessage}
                </p>
              )}

              <Button size="lg" type="submit" disabled={!ready || submit.isPending}>
                <SplitSquareVertical aria-hidden />
                {submit.isPending ? "Starting" : "Split into shares"}
              </Button>
              {!ready && (
                <p className="-mt-4 text-xs text-text-faint">
                  {media === "image" ? "Add one image to continue." : "Add files to continue."}
                </p>
              )}
            </form>
          </FormProvider>
        </div>
      </div>
    </AppShell>
  );
}

function recipeRows(media: MediaType, values: OptionValues) {
  const rows: { label: string; value: React.ReactNode }[] = [
    { label: "Method", value: String(values.method ?? "") },
    { label: "Shares", value: String(values.shares ?? "") },
  ];
  const method = String(values.method ?? "");
  const threshold = values.threshold;
  if (media === "image" || media === "video") {
    rows.push({
      label: media === "image" ? "Threshold" : "Frame threshold",
      value: String(threshold ?? ""),
    });
  }
  if (media === "audio" || media === "file") {
    rows.push({
      label: "Threshold",
      value: threshold == null || threshold === "" ? "all" : String(threshold),
    });
  }
  if (media === "audio" && method === "shamir") {
    rows.push({ label: "k-of-n", value: `${threshold == null || threshold === "" ? values.shares : threshold}/${values.shares}` });
  }
  if (values.seed !== null && values.seed !== undefined) {
    rows.push({ label: "Seed", value: String(values.seed) });
  }
  return rows;
}