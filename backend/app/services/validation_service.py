"""Backend-authoritative validation.

Pydantic schemas enforce ranges and cross-field rules; this service enforces
file-level rules (counts, suffixes, media expectations) and converts user JSON
into validated option models. The frontend's Zod schemas mirror these rules for
UX only — never trusted on their own.
"""

from __future__ import annotations

import json
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..security.errors import ApiError

T = TypeVar("T", bound=BaseModel)

SUFFIX_RULES: dict[str, tuple[str, ...]] = {
    "image": (".png",),
    "audio": (".wav",),
    "video_split": (".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".zip"),
    "video_reveal": (".zip",),
    "files_split": (),  # any file type
    "files_reveal": (".shard",),
}


class ValidationService:
    def parse_options(self, raw: str | None, model_cls: Type[T]) -> T:
        if raw is None or not raw.strip():
            return model_cls()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise ApiError(
                code="INVALID_PARAMETER",
                message="The options must be valid JSON.",
            )
        try:
            return model_cls.model_validate(data)
        except ValidationError as exc:
            raise ApiError(
                code="INVALID_PARAMETER",
                message="One or more options are invalid.",
                details={".".join(map(str, e["loc"])): e.get("msg", "")
                         for e in exc.errors()},
            ) from None

    def check_count(self, media: str, actual: int, minimum: int,
                    maximum: int | None = None) -> None:
        if actual < minimum or (maximum is not None and actual > maximum):
            raise ApiError(
                code="INVALID_PARAMETER",
                message=f"Expected between {minimum} and "
                        f"{maximum if maximum is not None else 'unlimited'} "
                        f"files, got {actual}.",
            )

    def check_uploads(self, media_rule: str, names: list[str]) -> None:
        allowed = SUFFIX_RULES[media_rule]
        if not allowed:
            return
        for name in names:
            if not any(name.lower().endswith(s) for s in allowed):
                raise ApiError(
                    code="INVALID_FILE_TYPE",
                    message=f"Unsupported file type for {name}.",
                    details={"file": name},
                )


validation = ValidationService()