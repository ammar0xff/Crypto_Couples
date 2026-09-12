import type { MediaType, OperationKind, OperationStatus } from "../types";

const MEDIA_ROUTE: Record<MediaType, string> = {
  image: "images",
  audio: "audio",
  video: "video",
  file: "files",
};

export function workflowPath(media: MediaType, kind: OperationKind): string {
  // App-relative AND leading-slash: callers (api.ts request()) join this
  // against API_URL which already carries "/api" (and has no trailing slash),
  // so the path must start with "/" but must NOT start with "/api" — the
  // old "/api/..." here produced the /api/api double-prefix that only the
  // SPA catch-all answered -> 405 Method Not Allowed on every split/reveal.
  return `/${MEDIA_ROUTE[media]}/${kind}`;
}

export function downloadAllUrl(opId: string): string {
  return `/operations/${opId}/download-all`;
}

export function downloadFileUrl(opId: string, name: string): string {
  return `/operations/${opId}/download?name=${encodeURIComponent(name)}`;
}

export const TERMINAL_STATUSES: Set<OperationStatus> = new Set([
  "completed",
  "failed",
  "cancelled",
  "expired",
] as const);

export function optionDefaults(media: MediaType): Record<string, unknown> {
  switch (media) {
    case "image":
      return { method: "stack", shares: 2, threshold: 128, dither: false };
    case "audio":
      return { method: "additive", shares: 2 };
    case "video":
      return {
        method: "stack",
        shares: 2,
        fps: null,
        no_audio: false,
        audio_method: "xor",
        threshold: 128,
        dither: false,
      };
    case "file":
      return { method: "xor", shares: 2 };
  }
}