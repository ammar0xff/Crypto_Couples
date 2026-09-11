#!/usr/bin/env python3
"""Generate the PWA icons by reusing the project's own demo renderer.

Renders the token glyph 'CC' (the core's built-in 5x7 font) onto a square
canvas with a split-frame motif, then writes PNGs via crypto_couples.png_encode.
No third-party dependencies.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crypto_couples import make_demo_image, png_encode, to_rows  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "public" / "icons"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def embed_square(glyph_black: list, size: int) -> list:
    """Place the black/white glyph into an SxS field of 0/1 rows, centered."""
    gh, gw = len(glyph_black), len(glyph_black[0])
    if gw > size or gh > size:
        raise RuntimeError("glyph larger than target canvas")
    ox, oy = (size - gw) // 2, (size - gh) // 2
    canvas = [[0] * size for _ in range(size)]
    for y in range(gh):
        for x in range(gw):
            if glyph_black[y][x]:
                canvas[oy + y][ox + x] = 1
    return canvas


def frame(bits: list, size: int, thickness: int) -> list:
    """Draw a stepped 'share edge' border so it reads as split shares."""
    out = [list(r) for r in bits]
    step = max(2, thickness * 2)
    for y in range(size):
        for x in range(size):
            in_border = (
                x < thickness or x >= size - thickness
                or y < thickness or y >= size - thickness
            )
            if in_border and (x // step) % 2 == 0:
                out[y][x] = 1
    return out


def main() -> None:
    glyph = make_demo_image("CC", scale=6, pad=6)
    for size in (192, 512):
        canvas = frame(embed_square(glyph, size), size, thickness=size // 32)
        (OUT_DIR / f"icon-{size}.png").write_bytes(png_encode(to_rows(canvas)))
        print(f"wrote icon-{size}.png")


if __name__ == "__main__":
    main()