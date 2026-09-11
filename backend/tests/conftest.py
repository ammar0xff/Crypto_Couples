"""Test session setup.

Point the backend at a throwaway temp directory before the app package is first
imported, and put the repo root on sys.path so the crypto core is importable.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

for p in (str(BACKEND), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

_TMP = Path(tempfile.mkdtemp(prefix="crypto_backend_test_"))
os.environ.setdefault("TEMP_DIRECTORY", str(_TMP / "ops"))
os.environ.setdefault("HISTORY_PATH", str(_TMP / "history.db"))
os.environ.setdefault("APP_ENV", "test")