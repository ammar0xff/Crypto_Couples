"""Byte/Shamir file crypto adapter. Calls crypto_media primitives only."""

from __future__ import annotations

import random
from pathlib import Path

from ..core_loader import cm
from ..deps import ops
from ..schemas.crypto import FileRevealOptions, FileSplitOptions
from ..security.errors import ApiError


def _check_cancel(rec) -> None:
    if rec.cancel_event.is_set():
        raise ApiError(code="CANCELLED", message="Operation cancelled.")


def _rng_seed(seed: int | None) -> random.Random:
    base = seed if seed is not None else random.SystemRandom().randrange(2**32)
    return random.Random(base % (2**32))


def _restored_name(share_names: list[str]) -> str:
    """Reverse the '<base>.<N>.shard' naming used by split."""
    stem = Path(share_names[0]).stem  # e.g. backup.zip.1
    parts = stem.rsplit(".", 1)
    if len(parts) == 2 and parts[-1].isdigit():
        return parts[0] + ".restored"
    return f"{stem}.restored"


class FileCryptoService:
    def split(self, rec, options: FileSplitOptions) -> None:
        if len(rec.input_names) != 1:
            raise ApiError(code="INVALID_PARAMETER",
                           message="File split requires exactly one file.")
        name = rec.input_names[0]
        data = (rec.dir / "input" / name).read_bytes()
        threshold = options.threshold if options.method == "shamir" \
            else options.shares
        rng = _rng_seed(options.seed)

        stem = Path(name).stem
        out_dir = rec.dir / "out"
        if options.method == "xor":
            chunks = cm.xor_split(data, options.shares, rng)
            for i, chunk in enumerate(chunks, 1):
                _check_cancel(rec)
                (out_dir / f"{stem}.{i}.shard").write_bytes(chunk)
                ops.report(rec, int(90 * i / options.shares),
                           f"Writing XOR share {i} of {options.shares}")
        else:
            for i, chunk in cm.shamir_split(data, options.shares,
                                           threshold, rng):
                _check_cancel(rec)
                (out_dir / f"{stem}.{i}.shard").write_bytes(chunk)
                ops.report(rec, int(90 * i / options.shares),
                           f"Writing Shamir share {i} of {options.shares} "
                           f"(k={threshold})")
        ops.finish(rec)

    def reveal(self, rec, options: FileRevealOptions) -> None:
        names = sorted(rec.input_names)
        if len(names) < 2:
            raise ApiError(code="INVALID_SHARE",
                           message="At least 2 share files are required.")
        data = [(rec.dir / "input" / n).read_bytes() for n in names]
        if options.method == "xor":
            out = cm.xor_reveal(data)
        else:
            points = [(cm._share_index(n), d) for n, d in zip(names, data)]
            if len({x for x, _ in points}) != len(points):
                raise ApiError(code="INVALID_SHARE",
                               message="Duplicate share index in reconstruction.")
            out = cm.shamir_reveal(points)

        out_path = rec.dir / "out" / _restored_name(names)
        out_path.write_bytes(out)
        ops.report(rec, 90, f"Restored file from {len(names)} shares")
        ops.finish(rec)


file_crypto = FileCryptoService()