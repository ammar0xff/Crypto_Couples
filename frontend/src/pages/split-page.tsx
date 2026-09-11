import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SplitSquareVertical } from "lucide-react";

import { Tabs } from "../components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Dropzone } from "../components/ui/dropzone";
import { Button } from "../components/ui/button";
import { AppShell } from "../components/layout/app-shell";
import { MEDIA_TYPES, type MediaType } from "../types";

export function SplitPage() {
  const navigate = useNavigate();
  const [media, setMedia] = useState<MediaType>("image");
  const [files, setFiles] = useState<File[]>([]);

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
                The file holding the secret. Dropped files stay local and are
                processed in memory.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Dropzone
                files={files}
                onFilesChange={setFiles}
                multiple={media === "file"}
                hint={media === "file" ? "Multiple files become one share set" : "One image"}
                aria-label="Source files"
              />
            </CardContent>
          </Card>

          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Recipe</CardTitle>
                <CardDescription>
                  Options and engine parameters, confirmed before processing.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-text-muted">Engine controls arrive in P12.</p>
                <p className="text-text-faint">Method, share count, and threshold are chosen here.</p>
              </CardContent>
            </Card>

            <Button
              size="lg"
              className="w-full"
              onClick={() => navigate("/operations")}
            >
              <SplitSquareVertical aria-hidden />
              Continue to processing
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}