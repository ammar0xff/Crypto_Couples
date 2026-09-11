"""Filename sanitization, safe paths and small token helpers."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from .errors import ApiError

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str, fallback: str = "file") -> str:
    """Strip directories and shell-hostile characters from a client filename."""
    stem = Path(name or "").name
    cleaned = _UNSAFE.sub("-", stem).strip(".- ")
    return cleaned or fallback


def safe_suffix(name: str) -> str:
    """Lowercased, alnum extension with a single leading dot ('' when none)."""
    suffix = Path(name or "").suffix.lower()
    if len(suffix) > 1 and suffix[1:].isalnum():
        return suffix
    return ""


def new_token(prefix: str = "op") -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def safe_join(root: Path | str, name: str) -> Path:
    """Resolve *name* inside *root*, rejecting any path traversal."""
    base = Path(root).resolve()
    target = (Path(root) / name).resolve()
    if target != base and base not in target.parents:
        raise ApiError(code="INVALID_PARAMETER",
                       message="Unsafe file name rejected.")
    return target