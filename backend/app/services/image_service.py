"""Image crypto adapter. Calls crypto_couples primitives only; no reimpl."""

from __future__ import annotations

import random
from pathlib import Path

from ..core_loader import cc
from ..deps import ops
from ..schemas.crypto import ImageRevealOptions, ImageSplitOptions
from ..security.errors import ApiError


def _bounded_seed(seed: int | None) -> int:
    if seed is not None:
        return seed % (2**32)
    return random.SystemRandom().randrange(2**32)


class ImageCryptoService:
    def split(self, rec, options: ImageSplitOptions) -> None:
        if len(rec.input_names) != 1:
            raise ApiError(code="INVALID_PARAMETER",
                           message="Image split requires exactly one PNG.")
        name = rec.input_names[0]
        try:
            width, height, rows = cc.png_decode(
                (rec.dir / "input" / name).read_bytes())
        except cc.PngError as exc:
            raise ApiError(code="INVALID_IMAGE",
                           message=f"Unable to read PNG: {exc}.") from None

        bits = cc.binarize(rows, options.threshold, options.dither)
        rng = random.Random(_bounded_seed(options.seed))
        shares = (cc.split_stack(bits, options.shares, rng)
                  if options.method == "stack"
                  else cc.split_xor(bits, options.shares, rng))

        stem = Path(name).stem
        out_dir = rec.dir / "out"
        for i, share in enumerate(shares, 1):
            _check_cancel(rec)
            payload = cc.png_encode(cc.to_rows(share))
            (out_dir / f"{stem}.share.{i}.png").write_bytes(payload)
            ops.report(rec, int(90 * i / options.shares),
                       f"Writing share {i} of {options.shares}")
        ops.report(rec, 95, f"Split {width}x{height} into "
                            f"{options.shares} shares")
        ops.finish(rec)

    def reveal(self, rec, options: ImageRevealOptions) -> None:
        names = sorted(rec.input_names)
        if len(names) < 2:
            raise ApiError(code="INVALID_SHARE",
                           message="At least 2 share images are required.")
        share_rows = []
        for n in names:
            _check_cancel(rec)
            try:
                _w, _h, rows = cc.png_decode((rec.dir / "input" / n).read_bytes())
            except cc.PngError as exc:
                raise ApiError(code="INVALID_SHARE",
                               message=f"Unable to read share {n}: {exc}.",
                               details={"file": n}) from None
            share_rows.append(rows)

        heights = {len(r) for r in share_rows}
        widths = {len(r[0]) if r else 0 for r in share_rows}
        if len(heights) != 1 or len(widths) != 1:
            raise ApiError(code="INVALID_SHARE",
                           message="All shares must have identical dimensions.")

        n = len(share_rows)
        bits = (cc.reveal_stack(share_rows, n)
                if options.method == "stack"
                else cc.reveal_xor(share_rows, n))
        ops.report(rec, 70, f"Revealed from {n} shares")
        out = rec.dir / "out" / f"{Path(rec.id).name}.revealed.png"
        out.write_bytes(cc.png_encode(cc.to_rows(bits)))
        ops.report(rec, 95, "Writing revealed image")
        ops.finish(rec)


def _check_cancel(rec) -> None:
    if rec.cancel_event.is_set():
        raise ApiError(code="CANCELLED", message="Operation cancelled.")


image_crypto = ImageCryptoService()