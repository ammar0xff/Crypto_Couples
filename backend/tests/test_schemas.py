"""Option schema validation rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.crypto import (
    AudioSplitOptions,
    FileSplitOptions,
    ImageSplitOptions,
    VideoSplitOptions,
)


def test_image_seed_clamp():
    opts = ImageSplitOptions(shares=3, seed=2**32 + 7)
    assert opts.seed == 7


def test_image_threshold_bounds():
    with pytest.raises(ValidationError):
        ImageSplitOptions(threshold=256)


def test_image_shares_bounds():
    with pytest.raises(ValidationError):
        ImageSplitOptions(shares=1)
    with pytest.raises(ValidationError):
        ImageSplitOptions(shares=9)


def test_shamir_threshold_leq_shares_audio():
    with pytest.raises(ValidationError):
        AudioSplitOptions(method="shamir", shares=3, threshold=4)


def test_audio_defaults_threshold_to_shares_for_shamir():
    opts = AudioSplitOptions(method="shamir", shares=5, threshold=None)
    assert opts.threshold == 5


def test_audio_non_shamir_threshold_forced():
    opts = AudioSplitOptions(method="xor", shares=2, threshold=4)
    assert opts.threshold == 2


def test_file_shamir_threshold():
    with pytest.raises(ValidationError):
        FileSplitOptions(method="shamir", shares=2, threshold=1)


def test_video_audio_threshold_gate():
    with pytest.raises(ValidationError):
        VideoSplitOptions(shares=2, audio_method="shamir",
                          audio_shares=2, audio_threshold=3)


def test_fps_bounds():
    with pytest.raises(ValidationError):
        VideoSplitOptions(fps=0)
    with pytest.raises(ValidationError):
        VideoSplitOptions(fps=1000)