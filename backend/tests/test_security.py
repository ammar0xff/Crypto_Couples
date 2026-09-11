"""Filename sanitising and path-traversal guards."""

from __future__ import annotations

import pytest

from app.security.errors import ApiError
from app.security.files import new_token, safe_join, sanitize_filename


def test_sanitize_filename_keeps_good():
    assert sanitize_filename("voice.wav") == "voice.wav"
    assert sanitize_filename("backup.zip.1.shard") == "backup.zip.1.shard"


def test_sanitize_filename_strips_paths():
    assert "/" not in sanitize_filename("../../etc/passwd")
    assert "\\" not in sanitize_filename("C:\\evil\\x.png")


def test_new_token_unique_short():
    a, b = new_token("op"), new_token("op")
    assert a != b
    assert a.startswith("op_")


def test_safe_join_blocks_escape():
    with pytest.raises(ApiError):
        safe_join("/tmp/ops/abc", "../../secret")
    with pytest.raises(ApiError):
        safe_join("/tmp/ops/abc", "/absolute/path.png")


def test_safe_join_allows_normal():
    out = safe_join("/tmp/ops/abc", "sub/file.png")
    assert str(out).endswith("sub/file.png")