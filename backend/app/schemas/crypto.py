"""Crypto workflow options.

These mirror and constrain the CLI parameters. Cross-field rules (such as
``threshold <= shares`` for Shamir) are enforced with model validators so the
backend stays authoritative; the frontend mirrors the same rules in Zod for UX.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


def _bounded_seed(v: int | None) -> int | None:
    if v is None:
        return None
    return v % (2**32)


class SplitSeedMixin(BaseModel):
    seed: int | None = Field(default=None, ge=0)


class ImageSplitOptions(SplitSeedMixin):
    method: Literal["stack", "xor"] = "stack"
    shares: int = Field(default=2, ge=2, le=8)
    threshold: int = Field(default=128, ge=0, le=255)
    dither: bool = False

    @model_validator(mode="after")
    def _clamp_seed(self) -> "ImageSplitOptions":
        self.seed = _bounded_seed(self.seed)
        return self


class ImageRevealOptions(BaseModel):
    method: Literal["stack", "xor"] = "stack"
    threshold: int = Field(default=128, ge=0, le=255)


class AudioSplitOptions(SplitSeedMixin):
    method: Literal["additive", "xor", "shamir"] = "additive"
    shares: int = Field(default=2, ge=2, le=16)
    threshold: int | None = Field(default=None, ge=2, le=16)

    @model_validator(mode="after")
    def _resolve_threshold(self) -> "AudioSplitOptions":
        self.seed = _bounded_seed(self.seed)
        if self.method == "shamir":
            self.threshold = self.threshold or self.shares
            if self.threshold > self.shares:
                raise ValueError("threshold cannot exceed shares")
        else:
            self.threshold = self.shares
        return self


class AudioRevealOptions(BaseModel):
    method: Literal["additive", "xor", "shamir"] = "additive"


class FileSplitOptions(SplitSeedMixin):
    method: Literal["xor", "shamir"] = "xor"
    shares: int = Field(default=2, ge=2, le=16)
    threshold: int | None = Field(default=None, ge=2, le=16)

    @model_validator(mode="after")
    def _resolve_threshold(self) -> "FileSplitOptions":
        self.seed = _bounded_seed(self.seed)
        if self.method == "shamir":
            self.threshold = self.threshold or self.shares
            if self.threshold > self.shares:
                raise ValueError("threshold cannot exceed shares")
        else:
            self.threshold = self.shares
        return self


class FileRevealOptions(BaseModel):
    method: Literal["xor", "shamir"] = "xor"


class VideoSplitOptions(SplitSeedMixin):
    method: Literal["stack", "xor"] = "stack"
    shares: int = Field(default=2, ge=2, le=8)
    fps: float | None = Field(default=None, gt=0, le=240)
    no_audio: bool = False
    audio_method: Literal["additive", "xor", "shamir"] = "xor"
    audio_shares: int | None = Field(default=None, ge=2, le=16)
    audio_threshold: int | None = Field(default=None, ge=2, le=16)
    threshold: int = Field(default=128, ge=0, le=255)
    dither: bool = False

    @model_validator(mode="after")
    def _clamp_seed(self) -> "VideoSplitOptions":
        self.seed = _bounded_seed(self.seed)
        if self.audio_method == "shamir" and self.audio_threshold:
            if self.audio_threshold > (self.audio_shares or self.shares):
                raise ValueError("audio threshold cannot exceed audio shares")
        return self


class VideoRevealOptions(BaseModel):
    method: Literal["stack", "xor"] = "stack"
    fps: float | None = Field(default=None, gt=0, le=240)
    encode: str | None = Field(default=None, max_length=120)
    no_audio: bool = False