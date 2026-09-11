import { describe, expect, it } from "vitest";
import {
  toSplitOptions,
  splitDefaults,
  revealDefaults,
} from "../lib/options";

describe("splitDefaults", () => {
  it("image defaults include dither false, seed null", () => {
    const d = splitDefaults("image");
    expect(d).toEqual(
      expect.objectContaining({ method: "stack", shares: 2, threshold: 128, dither: false, seed: null }),
    );
  });

  it("video defaults include audio_method, no_audio, audio_shares null", () => {
    const d = splitDefaults("video");
    expect(d).toEqual(
      expect.objectContaining({
        method: "stack",
        shares: 2,
        threshold: 128,
        fps: null,
        no_audio: false,
        audio_method: "xor",
        audio_shares: null,
        audio_threshold: null,
        dither: false,
        seed: null,
      }),
    );
  });

  it("audio defaults inherit from optionDefaults", () => {
    const d = splitDefaults("audio") as Record<string, unknown>;
    expect(d.method).toBe("additive");
    expect(d).toEqual(
      expect.objectContaining({ threshold: null, seed: null }),
    );
  });
});

describe("revealDefaults", () => {
  it("image reveal defaults method=stack, threshold=128", () => {
    expect(revealDefaults("image")).toEqual({ method: "stack", threshold: 128 });
  });
  it("video reveal defaults include encode null, no_audio false", () => {
    expect(revealDefaults("video")).toEqual({
      method: "stack",
      fps: null,
      encode: null,
      no_audio: false,
    });
  });
});

describe("toSplitOptions", () => {
  it("keeps seed number when provided", () => {
    const out = toSplitOptions({ method: "stack", shares: 2, seed: 1234 });
    expect(out.seed).toBe(1234);
  });

  it("deletes seed when null/undefined/empty string", () => {
    for (const v of [null, undefined, ""]) {
      const out = toSplitOptions({ method: "stack", shares: 2, seed: v });
      expect(out).not.toHaveProperty("seed");
    }
  });

  it("sets threshold = shares when shamir method and threshold is null", () => {
    const out = toSplitOptions({
      method: "shamir",
      shares: 5,
      threshold: null,
    });
    expect(out.threshold).toBe(5);
  });

  it("preserves explicit shamir threshold", () => {
    const out = toSplitOptions({
      method: "shamir",
      shares: 8,
      threshold: 3,
    });
    expect(out.threshold).toBe(3);
  });

  it("deletes threshold when method is not shamir", () => {
    const out = toSplitOptions({ method: "stack", shares: 2, threshold: 128 });
    expect(out).not.toHaveProperty("threshold");
  });

  it("deletes fps and encode when null/empty", () => {
    const out = toSplitOptions({
      method: "stack",
      shares: 2,
      fps: null,
      encode: "",
    });
    expect(out).not.toHaveProperty("fps");
    expect(out).not.toHaveProperty("encode");
  });

  it("keeps fps when numeric", () => {
    const out = toSplitOptions({
      method: "stack",
      shares: 2,
      fps: 24,
      encode: "h264",
    });
    expect(out.fps).toBe(24);
    expect(out.encode).toBe("h264");
  });

  it("converts string seed to number", () => {
    const out = toSplitOptions({ method: "stack", shares: 2, seed: "42" });
    expect(out.seed).toBe(42);
  });
});
