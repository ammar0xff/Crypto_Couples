import { Spline, ShieldAlert } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Row } from "./ui/controls";
import type { MediaType, OperationKind } from "../types";

const MEDIA_LABEL: Record<MediaType, string> = {
  image: "Image",
  audio: "Audio",
  video: "Video",
  file: "File bundle",
};

export function RecipeCard({
  media,
  kind,
  rows,
  note,
}: {
  media: MediaType;
  kind: OperationKind;
  rows: { label: string; value: React.ReactNode }[];
  note?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Recipe</CardTitle>
        <span className="inline-flex items-center gap-1.5 rounded bg-primary/10 px-2 py-1 font-mono text-[11px] uppercase tracking-wide text-primary">
          <Spline aria-hidden className="size-3" />
          {kind} {MEDIA_LABEL[media]}
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {rows.map((row) => (
          <Row key={row.label} {...row} />
        ))}
      </CardContent>
      {note && (
        <CardContent className="pt-0">
          <p className="flex items-start gap-2 text-xs text-text-faint">
            <ShieldAlert aria-hidden className="mt-0.5 size-3.5 shrink-0" />
            {note}
          </p>
        </CardContent>
      )}
    </Card>
  );
}