import { useFormContext } from "react-hook-form";

import { Checkbox, FieldError, NumberInput, Select, TextInput } from "./ui/controls";
import { cn } from "../lib/utils";
import type { OptionValues } from "../lib/options";
import type { MediaType } from "../types";

const MAX_SHARES: Record<MediaType, number> = {
  image: 8,
  audio: 16,
  video: 8,
  file: 16,
};

const METHODS: Record<MediaType, { split: string[]; reveal: string[] }> = {
  image: { split: ["stack", "xor"], reveal: ["stack", "xor"] },
  audio: {
    split: ["additive", "xor", "shamir"],
    reveal: ["additive", "xor", "shamir"],
  },
  video: { split: ["stack", "xor"], reveal: ["stack", "xor"] },
  file: { split: ["xor", "shamir"], reveal: ["xor", "shamir"] },
};

function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label className="text-sm font-medium text-text">{label}</label>
      {children}
      {hint && <p className="text-xs text-text-faint">{hint}</p>}
    </div>
  );
}

function MethodField({ name, methods }: { name: string; methods: string[] }) {
  const { register } = useFormContext<OptionValues>();
  return (
    <Field label="Method" hint="The sharing algorithm for this secret type">
      <Select {...register(name)}>
        {methods.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </Select>
    </Field>
  );
}

export function SplitOptionsPanel({ media }: { media: MediaType }) {
  const { register, watch, formState } = useFormContext<OptionValues>();
  const methods = METHODS[media].split;
  const noAudio = Boolean(watch("no_audio"));
  const audioMethod = watch("audio_method") as string;
  const audioShamir = audioMethod === "shamir";

  return (
    <div className="flex flex-col gap-4">
      <MethodField name="method" methods={methods} />

      <Field label="Shares" hint="How many pieces the secret is cut into">
        <NumberInput
          {...register("shares")}
          min={2}
          max={MAX_SHARES[media]}
          aria-invalid={Boolean(formState.errors.shares)}
        />
        <FieldError id="shares-error" message={formState.errors.shares?.message as string | undefined} />
      </Field>

      {(media === "audio" || media === "file") && (
        <Field
          label="Threshold"
          hint="Shares needed to reveal. Empty means all shares."
        >
          <NumberInput
            {...register("threshold")}
            min={2}
            max={MAX_SHARES[media]}
            placeholder="all"
            aria-invalid={Boolean(formState.errors.threshold)}
          />
          <FieldError
            id="threshold-error"
            message={formState.errors.threshold?.message as string | undefined}
          />
        </Field>
      )}

      {media === "image" && (
        <Field label="Reveal threshold" hint="Brightness cutoff when stacking shares">
          <NumberInput
            {...register("threshold")}
            min={0}
            max={255}
            aria-invalid={Boolean(formState.errors.threshold)}
          />
          <FieldError
            id="threshold-error"
            message={formState.errors.threshold?.message as string | undefined}
          />
        </Field>
      )}

      {media === "image" && (
        <Checkbox
          label="Dither against flat thresholds"
          {...register("dither")}
        />
      )}

      {media === "video" && (
        <>
          <Field label="Frame rate (fps)" hint="Empty keeps the source frame rate">
            <NumberInput
              {...register("fps")}
              min={1}
              max={240}
              placeholder="keep"
            />
          </Field>

          <Checkbox
            label="Drop audio track"
            {...register("no_audio")}
          />

          <div className={cn("flex flex-col gap-4", noAudio && "pointer-events-none opacity-40")}>
            <Field label="Audio method" hint="How the soundtrack is shared">
              <Select
                {...register("audio_method")}
                aria-disabled={noAudio}
              >
                {["additive", "xor", "shamir"].map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Audio shares" hint="Empty uses the video share count">
              <NumberInput
                {...register("audio_shares")}
                min={2}
                max={16}
                placeholder="same as shares"
              />
            </Field>

            {audioShamir && (
              <Field
                label="Audio threshold"
                hint="Shares needed to restore the soundtrack"
              >
                <NumberInput
                  {...register("audio_threshold")}
                  min={2}
                  max={16}
                  placeholder="same as audio shares"
                />
              </Field>
            )}
          </div>

          <Field label="Reveal threshold" hint="Brightness cutoff when stacking frames">
            <NumberInput
              {...register("threshold")}
              min={0}
              max={255}
              aria-invalid={Boolean(formState.errors.threshold)}
            />
          </Field>

          <Checkbox
            label="Dither against flat thresholds"
            {...register("dither")}
          />
        </>
      )}

      {(media === "image" ||
        media === "audio" ||
        media === "video" ||
        media === "file") && (
        <Field label="Seed (optional)" hint="Deterministic shuffle for reproducible shares">
          <NumberInput
            {...register("seed")}
            min={0}
            max={2 ** 32 - 1}
            placeholder="random"
          />
        </Field>
      )}
    </div>
  );
}

export function RevealOptionsPanel({ media }: { media: MediaType }) {
  const { register, formState } = useFormContext<OptionValues>();
  const methods = METHODS[media].reveal;

  return (
    <div className="flex flex-col gap-4">
      <MethodField name="method" methods={methods} />

      {(media === "image" || media === "video") && (
        <Field label="Reveal threshold" hint="Brightness cutoff when stacking shares">
          <NumberInput
            {...register("threshold")}
            min={0}
            max={255}
            aria-invalid={Boolean(formState.errors.threshold)}
          />
          <FieldError
            id="threshold-error"
            message={formState.errors.threshold?.message as string | undefined}
          />
        </Field>
      )}

      {media === "video" && (
        <>
          <Field label="Frame rate (fps)" hint="Empty uses the source frame rate">
            <NumberInput
              {...register("fps")}
              min={1}
              max={240}
              placeholder="keep"
            />
          </Field>

          <Field label="Encode preset" hint="Optional ffmpeg encode for the restored video">
            <TextInput
              {...register("encode")}
              placeholder="auto"
              aria-invalid={Boolean(formState.errors.encode)}
            />
          </Field>

          <Checkbox
            label="Drop audio track on reveal"
            {...register("no_audio")}
          />
        </>
      )}

      {(media === "image" || media === "audio" || media === "file") && (
        <p className="text-xs text-text-faint">
          Shares are combined as uploaded; no further options apply.
        </p>
      )}
    </div>
  );
}