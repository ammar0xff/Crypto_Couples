"""Import bridge to the existing crypto core (repository root scripts).

The core modules stay at the repository root, untouched. Backend services
import them through this loader so the API layer never ships a copy and the
CLI keeps working from the same files.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import crypto_couples as cc  # noqa: E402
import crypto_media as cm  # noqa: E402

__all__ = ["cc", "cm", "REPO_ROOT"]