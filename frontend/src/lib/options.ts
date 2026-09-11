import { z } from "zod";
import type { MediaType, OperationKind } from "../types";
import { optionDefaults } from "./endpoints";

export type OptionValues = Record<string, unknown>;

export function optionsMeta(media: MediaType, kind: OperationKind) {
  return {
    schema: kind === "split" ? splitSchemas[media] : revealSchemas[media],
    defaults: kind === "split" ? splitDefaults(media) : revealDefaults(media),
  };
}

const seedField = z.preprocess(
  (v) => (v === "" || v === null || v === undefined ? null : Number(v)),
  z.number().int().min(0).lt(2 ** 32).nullable(),
);

export const imageSplitSchema = z.object({
  method: z.enum(["stack", "xor"]),
  shares: z.coerce.number().int().min(2).max(8),
  threshold: z.coerce.number().int().min(0).max(255),
  dither: z.boolean(),
  seed: seedField,
});

export const imageRevealSchema = z.object({
  method: z.enum(["stack", "xor"]),
  threshold: z.coerce.number().int().min(0).max(255),
});

export const audioSplitSchema = z
  .object({
    method: z.enum(["additive", "xor", "shamir"]),
    shares: z.coerce.number().int().min(2).max(16),
    threshold: z.coerce.number().int().min(2).max(16).nullable(),
    seed: seedField,
  })
  .refine(
    (v) => v.method !== "shamir" || (v.threshold ?? v.shares) <= v.shares,
    {
      message: "threshold cannot exceed shares",
      path: ["threshold"],
    },
  );

export const audioRevealSchema = z.object({
  method: z.enum(["additive", "xor", "shamir"]),
});

export const fileSplitSchema = z
  .object({
    method: z.enum(["xor", "shamir"]),
    shares: z.coerce.number().int().min(2).max(16),
    threshold: z.coerce.number().int().min(2).max(16).nullable(),
    seed: seedField,
  })
  .refine(
    (v) => v.method !== "shamir" || (v.threshold ?? v.shares) <= v.shares,
    {
      message: "threshold cannot exceed shares",
      path: ["threshold"],
    },
  );

export const fileRevealSchema = z.object({
  method: z.enum(["xor", "shamir"]),
});

export const videoSplitSchema = z
  .object({
    method: z.enum(["stack", "xor"]),
    shares: z.coerce.number().int().min(2).max(8),
    fps: z.preprocess(
      (v) => (v === "" || v === null || v === undefined ? null : Number(v)),
      z.number().gt(0).lte(240).nullable(),
    ),
    no_audio: z.boolean(),
    audio_method: z.enum(["additive", "xor", "shamir"]),
    audio_shares: z.coerce.number().int().min(2).max(16).nullable(),
    audio_threshold: z.coerce.number().int().min(2).max(16).nullable(),
    threshold: z.coerce.number().int().min(0).max(255),
    dither: z.boolean(),
    seed: seedField,
  })
  .refine(
    (v) =>
      v.audio_method !== "shamir" ||
      (v.audio_threshold ?? v.audio_shares ?? v.shares) <=
        (v.audio_shares ?? v.shares),
    {
      message: "audio threshold cannot exceed audio shares",
      path: ["audio_threshold"],
    },
  );

export const videoRevealSchema = z.object({
  method: z.enum(["stack", "xor"]),
  fps: z.preprocess(
    (v) => (v === "" || v === null || v === undefined ? null : Number(v)),
    z.number().gt(0).lte(240).nullable(),
  ),
  encode: z.preprocess(
    (v) => (v === "" || v === null || v === undefined ? null : String(v)),
    z.string().max(120).nullable(),
  ),
  no_audio: z.boolean(),
});

export const splitSchemas: Record<MediaType, z.ZodTypeAny> = {
  image: imageSplitSchema,
  audio: audioSplitSchema,
  video: videoSplitSchema,
  file: fileSplitSchema,
};

export const revealSchemas: Record<MediaType, z.ZodTypeAny> = {
  image: imageRevealSchema,
  audio: audioRevealSchema,
  video: videoRevealSchema,
  file: fileRevealSchema,
};

export function splitDefaults(media: MediaType) {
  const d = optionDefaults(media);
  switch (media) {
    case "image":
      return { ...d, dither: false, seed: null };
    case "audio":
      return { ...d, threshold: null, seed: null };
    case "video":
      return {
        ...d,
        fps: null,
        no_audio: false,
        audio_method: "xor",
        audio_shares: null,
        audio_threshold: null,
        dither: false,
        seed: null,
      };
    case "file":
      return { ...d, threshold: null, seed: null };
  }
}

export function revealDefaults(media: MediaType) {
  switch (media) {
    case "image":
      return { method: "stack", threshold: 128 };
    case "audio":
      return { method: "additive" };
    case "video":
      return { method: "stack", fps: null, encode: null, no_audio: false };
    case "file":
      return { method: "xor" };
  }
}

export function toSplitOptions(
  values: Record<string, unknown>,
): Record<string, unknown> {
  const opts: Record<string, unknown> = { ...values };

  if (
    values.seed !== null &&
    values.seed !== undefined &&
    values.seed !== ""
  ) {
    opts.seed = Number(values.seed);
  } else {
    delete opts.seed;
  }

  if ((opts.method as string) === "shamir") {
    const shareCount = Number(opts.shares);
    const threshold = opts.threshold;
    opts.threshold =
      threshold === null || threshold === undefined
        ? shareCount
        : Number(threshold);
  } else if ("threshold" in opts) {
    delete opts.threshold;
  }

  if ("fps" in opts && (opts.fps === null || opts.fps === "")) {
    delete opts.fps;
  }
  if ("encode" in opts && (opts.encode === null || opts.encode === "")) {
    delete opts.encode;
  }
  return opts;
}