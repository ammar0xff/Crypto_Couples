"""Uniform API error envelope.

Every failure from the API layer is either an ApiError (mapped to a stable
code) or an unexpected exception (mapped to INTERNAL, logged, never shown to
clients verbatim). Clients map codes -> friendly messages locally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiError(Exception):
    code: str = "INTERNAL"
    message: str = "Something went wrong."
    details: dict[str, Any] = field(default_factory=dict)
    status_code: int = 400

    def envelope(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}