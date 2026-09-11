#!/usr/bin/env python3
"""Crypto_Couples - visual cryptography made from pure Python stdlib.

Splits an image into shares that look like random noise. Stack the shares
(overlay / OR) or XOR them on a computer and the secret image reappears.

No third-party dependencies: ships its own 8-bit PNG reader/writer.
"""

import argparse
import os
import random
import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
COLOR_NAMES = {0: "gray", 2: "rgb", 3: "palette", 4: "gray+alpha", 6: "rgba"}
BLACK_THRESHOLD = 128


# ---------------------------------------------------------------------------
# png io --------------------------------------------------------------------
# ---------------------------------------------------------------------------

class PngError(ValueError):
    """Raised for PNG files this reader cannot handle."""


def _chunk(type_, data):
    payload = type_ + data
    return (struct.pack(">I", len(data)) + payload +
            struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF))


def _peek_chunks(data):
    if not data.startswith(PNG_SIG):
        raise PngError("not a PNG file (bad signature)")
    view = memoryview(data)
    pos = 8
    chunks = []
    while pos + 8 <= len(view):
        (length,) = struct.unpack_from(">I", view, pos)
        type_ = bytes(view[pos + 4:pos + 8])
        body = bytes(view[pos + 8:pos + 8 + length])
        (crc,) = struct.unpack_from(">I", view, pos + 8 + length)
        if zlib.crc32(type_ + body) & 0xFFFFFFFF != crc:
            raise PngError(f"corrupt png (bad CRC on {type_})")
        chunks.append((type_, body))
        pos += 12 + length
        if type_ == b"IEND":
            break
    return chunks


def png_decode(data):
    """Decode a non-interlaced PNG into (width, height, rows of RGBA tuples)."""
    chunks = _peek_chunks(data)
    header = next((b for t, b in chunks if t == b"IHDR"), None)
    if header is None:
        raise PngError("missing IHDR")
    width, height, depth, color, _comp, _filt, interlace = struct.unpack(
        ">IIBBBBB", header)
    if interlace:
        raise PngError("interlaced PNGs are not supported")
    if color not in CHANNELS:
        raise PngError(f"unsupported color type {color}")
    if depth not in (1, 2, 4, 8, 16):
        raise PngError(f"unsupported bit depth {depth}")
    if color == 3 and depth not in (1, 2, 4, 8):
        raise PngError(f"palette color type does not allow depth {depth}")

    palette = None
    palette_alpha = None
    for type_, body in chunks:
        if type_ == b"PLTE":
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif type_ == b"tRNS" and color == 3:
            palette_alpha = list(body)

    idat = b"".join(b for t, b in chunks if t == b"IDAT")
    if not idat:
        raise PngError("missing IDAT")

    channels = CHANNELS[color]
    bpp = (channels * depth + 7) // 8
    stride = (width * channels * depth + 7) // 8
    raw = zlib.decompress(idat)

    prev = bytearray(stride)
    scanlines = []
    pos = 0
    for _ in range(height):
        if pos >= len(raw):
            raise PngError("truncated image data")
        filt = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = prev[i]
            ul = prev[i - bpp] if i >= bpp else 0
            if filt == 1:
                line[i] = (line[i] + left) & 0xFF
            elif filt == 2:
                line[i] = (line[i] + up) & 0xFF
            elif filt == 3:
                line[i] = (line[i] + (left + up) // 2) & 0xFF
            elif filt == 4:
                p = left + up - ul
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - ul)
                pred = left if (pa <= pb and pa <= pc) else \
                       up if pb <= pc else ul
                line[i] = (line[i] + pred) & 0xFF
            elif filt != 0:
                raise PngError(f"unknown per-scanline filter {filt}")
        scanlines.append(bytes(line))
        prev = line

    rows = []
    for line in scanlines:
        vals, n = _extract_values(line, channels, depth)
        row = []
        idx = 0
        for _ in range(width):
            if color == 0:
                v = vals[idx]; row.append((v, v, v, 255))
            elif color == 2:
                r, g, b = vals[idx:idx + 3]; row.append((r, g, b, 255))
            elif color == 3:
                entry = palette[vals[idx]] if palette else (255, 0, 255)
                alpha = palette_alpha[vals[idx]] if palette_alpha else 255
                row.append((entry[0], entry[1], entry[2], alpha))
            elif color == 4:
                v, a = vals[idx:idx + 2]; row.append((v, v, v, a))
            else:
                r, g, b, a = vals[idx:idx + 4]; row.append((r, g, b, a))
            idx += channels
        rows.append(row)
    return width, height, rows


def _extract_values(line, channels, depth):
    if depth in (8, 16):
        step = 2 if depth == 16 else 1
        return [line[i] for i in range(0, len(line), step)], channels
    mask = (1 << depth) - 1
    per = 8 // depth
    vals = []
    for byte in line:
        for k in range(per):
            vals.append((byte >> (8 - depth * (k + 1))) & mask)
    return vals, channels


def png_encode(rows):
    """Encode rows of RGBA tuples into a PNG byte string (8-bit, color 6)."""
    height = len(rows)
    width = len(rows[0]) if height else 0
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for r, g, b, a in row:
            raw += bytes((r & 0xFF, g & 0xFF, b & 0xFF, a & 0xFF))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    out = bytearray(PNG_SIG)
    out += _chunk(b"IHDR", header)
    out += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += _chunk(b"IEND", b"")
    return bytes(out)


# ---------------------------------------------------------------------------
# pixel helpers --------------------------------------------------------------
# ---------------------------------------------------------------------------

def luma(r, g, b):
    return round(0.299 * r + 0.587 * g + 0.114 * b)


def binarize(rows, threshold=BLACK_THRESHOLD, dither=False):
    """Reduce RGBA rows to rows of booleans (True = black)."""
    height = len(rows)
    width = len(rows[0]) if height else 0
    if not dither:
        out = []
        for row in rows:
            out.append([luma(*px[:3]) < threshold for px in row])
        return out

    err = [[0.0] * width for _ in range(height)]
    out = []
    for y in range(height):
        line = []
        for x in range(width):
            v = luma(*rows[y][x][:3]) + err[y][x]
            bit = v < threshold
            line.append(bit)
            qerr = v - (0.0 if bit else 255.0)
            if x + 1 < width:
                err[y][x + 1] += qerr * 7 / 16
            if y + 1 < height:
                if x > 0:
                    err[y + 1][x - 1] += qerr * 3 / 16
                err[y + 1][x] += qerr * 5 / 16
                if x + 1 < width:
                    err[y + 1][x + 1] += qerr * 1 / 16
        out.append(line)
    return out


def to_rows(bits, black=(0, 0, 0, 255), white=(255, 255, 255, 255)):
    return [[black if b else white for b in row] for row in bits]


def black_density(bits):
    total = sum(len(row) for row in bits)
    count = sum(1 for row in bits for b in row if b)
    return count / total if total else 0.0


# ---------------------------------------------------------------------------
# visual cryptography --------------------------------------------------------
# ---------------------------------------------------------------------------

def split_stack(bits, shares, rng):
    """Naor-Shamir (n,n): each original pixel -> n subpixels per share.

    White pixels put one black subpixel of the same column in every share;
    black pixels give each share a black subpixel at its own column. Stacking
    (OR) a white pixel yields 1/n darkness, a black pixel yields full black.
    """
    height = len(bits)
    width = len(bits[0]) if height else 0
    out = []
    for _ in range(shares):
        out.append([[False] * (width * shares) for _ in range(height)])
    for y in range(height):
        for x in range(width):
            base = x * shares
            if not bits[y][x]:
                col = rng.randrange(shares)
                for s in range(shares):
                    out[s][y][base + col] = True
            else:
                for s in range(shares):
                    out[s][y][base + s] = True
    return out


def split_xor(bits, shares, rng):
    """(n,n) XOR scheme: all shares random except the last, computed so the
    XOR of every share recovers the message exactly."""
    height = len(bits)
    width = len(bits[0]) if height else 0
    out = []
    for _ in range(shares - 1):
        out.append([[rng.random() < 0.5 for _ in range(width)]
                    for _ in range(height)])
    last_acc = [row[:] for row in bits]
    for s in range(shares - 1):
        for y in range(height):
            for x in range(width):
                last_acc[y][x] = last_acc[y][x] != out[s][y][x]
    out.append(last_acc)
    return out


def reveal_stack(share_rows, shares):
    """OR-stack n shares and resolve each n-subpixel block by darkness."""
    height = len(share_rows[0])
    width = len(share_rows[0][0]) if height else 0
    used = width - (width % shares)
    out = []
    for y in range(height):
        row = []
        for bx in range(0, used, shares):
            dark = 0
            for x in range(bx, bx + shares):
                if any(luma(*s[y][x][:3]) < BLACK_THRESHOLD for s in share_rows):
                    dark += 1
            row.append(dark / shares > 0.5)
        out.append(row)
    return out


def reveal_xor(share_rows, shares, threshold=BLACK_THRESHOLD):
    height = len(share_rows[0])
    width = len(share_rows[0][0]) if height else 0
    out = []
    for y in range(height):
        row = []
        for x in range(width):
            bit = False
            for s in share_rows:
                bit = bit != (luma(*s[y][x][:3]) < threshold)
            row.append(bit)
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# demo image -----------------------------------------------------------------
# ---------------------------------------------------------------------------

FONT = {
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ",": [".....", ".....", ".....", ".....", "..##.", "..##.", ".#..."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    "#": ["#.#.#", "#####", "#.#.#", "#####", "#.#.#", "#####", "#.#.#"],
}


def make_demo_image(text, scale=6, pad=12):
    """Render centered text: white canvas, black glyphs (True = black)."""
    chars = [FONT.get(ch.upper(), FONT["?"]) for ch in text]
    glyph_w, glyph_h = 5, 7
    gap = 1
    w = len(chars) * (glyph_w + gap) - gap + pad * 2
    h = glyph_h + pad * 2
    canvas = [[False] * (w * scale) for _ in range(h * scale)]
    ox = pad * scale
    oy = pad * scale
    for gi, glyph in enumerate(chars):
        for gy in range(glyph_h):
            for gx in range(glyph_w):
                if glyph[gy][gx] != "#":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        yy, xx = oy + gy * scale + sy, ox + gi * (glyph_w + gap) * scale + gx * scale + sx
                        if 0 <= yy < len(canvas) and 0 <= xx < len(canvas[0]):
                            canvas[yy][xx] = True
    return canvas


# ---------------------------------------------------------------------------
# cli -----------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _read_png(path):
    with open(path, "rb") as fh:
        return png_decode(fh.read())


def _write_png(path, bits):
    with open(path, "wb") as fh:
        fh.write(png_encode(to_rows(bits)))


def _print_status(message, path):
    print(f"[*] {message}: {path}")


def cmd_split(args):
    width, height, rows = _read_png(args.image)
    bits = binarize(rows, args.threshold, args.dither)
    rng = random.Random(args.seed)
    stem = os.path.splitext(args.out)[0]

    if args.method == "stack":
        shares = split_stack(bits, args.shares, rng)
    else:
        shares = split_xor(bits, args.shares, rng)

    paths = []
    for i, share in enumerate(shares, 1):
        path = f"{stem}.{i}.png"
        _write_png(path, share)
        paths.append(path)
        _print_status(f"write share {i}/{args.shares}", path)
    print(f"[*] ({args.method}, {args.shares}-of-{args.shares}) "
          f"share density: " +
          ", ".join(f"{i}={black_density(s):.2f}" for i, s in enumerate(shares, 1)))
    print("[*] keep the shares secret from each other; any "
          f"{args.shares if args.shares > 1 else 2} reveal the message.")
    return 0


def cmd_reveal(args):
    share_rows = []
    for path in args.shares_files:
        _, _, rows = _read_png(path)
        share_rows.append(rows)
    n = len(share_rows)
    heights = {len(s) for s in share_rows}
    widths = {len(s[0]) if s else 0 for s in share_rows}
    if len(heights) != 1 or len(widths) != 1:
        raise SystemExit("[!] all shares must have identical dimensions")
    if args.method == "stack":
        bits = reveal_stack(share_rows, n)
    else:
        bits = reveal_xor(share_rows, n)
    _write_png(args.out, bits)
    _print_status("write revealed image", args.out)
    print(f"[*] density (0=white .. 1=black): {black_density(bits):.2f}")
    return 0


def cmd_demo(args):
    bits = make_demo_image(args.text, args.scale)
    _write_png(args.out, bits)
    _print_status("write demo message", args.out)
    print(f"[*] {len(bits[0])}x{len(bits)} px, use it with 'split'")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="crypto-couples",
        description="Visual cryptography: split an image into noise shares "
                    "that recombine (stack or XOR) to show the secret.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  crypto_couples.py demo message.png --text 'SECRET' --scale 6\n"
               "  crypto_couples.py split message.png --shares 2 --method stack --out share\n"
               "  crypto_couples.py reveal share.1.png share.2.png --method stack --out revealed.png\n"
               "  crypto_couples.py split message.png --shares 3 --method xor --out share\n"
               "  crypto_couples.py reveal share.1.png share.2.png share.3.png --method xor --out msg.png")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("demo", help="render a text message PNG to split")
    s.add_argument("out", help="output PNG path")
    s.add_argument("--text", default="SECRET", help="message text")
    s.add_argument("--scale", type=int, default=6, help="glyph upscale factor")
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("split", help="create n-of-n shares from an image")
    s.add_argument("image", help="input PNG (grayscale/color)")
    s.add_argument("--out", required=True,
                   help="output prefix -> <out>.1.png, <out>.2.png, ...")
    s.add_argument("--shares", "-n", type=int, default=2, help="number of shares")
    s.add_argument("--method", choices=("stack", "xor"), default="stack",
                   help="stack = print shares & overlay; xor = recombine on a computer")
    s.add_argument("--dither", action="store_true",
                   help="Floyd-Steinberg dither grayscale before splitting")
    s.add_argument("--threshold", type=int, default=BLACK_THRESHOLD,
                   help="luma threshold for binarizing the input")
    s.add_argument("--seed", type=int, default=None, help="RNG seed (reproducible)")
    s.set_defaults(func=cmd_split)

    s = sub.add_parser("reveal", help="recombine shares into the message")
    s.add_argument("shares_files", nargs="+", metavar="SHARE.png",
                   help="two or more shares")
    s.add_argument("--out", required=True, help="output PNG path")
    s.add_argument("--method", choices=("stack", "xor"), default="stack")
    s.set_defaults(func=cmd_reveal)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PngError as error:
        raise SystemExit(f"[!] {error}")
    except OSError as error:
        raise SystemExit(f"[!] {error}")


if __name__ == "__main__":
    raise SystemExit(main())