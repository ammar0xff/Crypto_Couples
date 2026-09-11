#!/usr/bin/env python3
"""Tests for Crypto_Couples (stdlib unittest - no third-party dependencies)."""
import os
import random
import struct
import subprocess
import sys
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import crypto_couples as cc  # noqa: E402

TEXT_IMAGE = (
    ".....#.....###.##.##.#####",
    ".....#.....#...#.#.#.#...#",
    ".....#.....#...#.#.#.####.",
    ".....#.....#####.#.#.#...#",
    ".....#.....#...#.#.#.#...#",
    ".....#.....#...#.#.#.#...#",
    "##########.#...#.#.#.#####",
)


def make_bits(rows, white=True):
    return [[ch == "#" for ch in row] for row in rows]


def rgba_from_bits(bits):
    return cc.to_rows(bits)


class PngIOTests(unittest.TestCase):
    def test_roundtrip_rgba(self):
        rows = cc.to_rows(make_bits(TEXT_IMAGE))
        data = cc.png_encode(rows)
        w, h, back = cc.png_decode(data)
        self.assertEqual((w, h), (len(rows[0]), len(rows)))
        self.assertEqual(rows, back)

    def test_png_signature_guard(self):
        with self.assertRaises(cc.PngError):
            cc.png_decode(b"not a png at all")

    def test_decodes_external_gray_png(self):
        gray = self._gray_png([[0, 255]])
        w, h, rows = cc.png_decode(gray)
        self.assertEqual((w, h), (2, 1))
        self.assertEqual(rows, [[(0, 0, 0, 255), (255, 255, 255, 255)]])

    def _gray_png(self, pixels):
        """pixels: list of rows of gray ints (one filter byte per row)."""
        width = len(pixels[0])
        height = len(pixels)
        raw = bytearray()
        for row in pixels:
            raw.append(0)
            raw += bytes(row)
        header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
        return (cc.PNG_SIG + cc._chunk(b"IHDR", header) +
                cc._chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
                cc._chunk(b"IEND", b""))


class SplitRevealTests(unittest.TestCase):
    def reveal_stack(self, bits, shares, seed=7, dither=False):
        rng = random.Random(seed)
        share_bits = cc.split_stack(bits, shares, rng)
        share_rows = [rgba_from_bits(s) for s in share_bits]
        return cc.reveal_stack(share_rows, shares)

    def test_stack_2of2_recovers_message(self):
        bits = make_bits(TEXT_IMAGE)
        got = self.reveal_stack(bits, 2)
        self.assertEqual(bits, got)

    def test_stack_3of3_recovers_message(self):
        bits = make_bits(TEXT_IMAGE)
        got = self.reveal_stack(bits, 3)
        self.assertEqual(bits, got)

    def test_shares_look_like_noise(self):
        bits = make_bits(TEXT_IMAGE)
        rng = random.Random(11)
        for s in cc.split_stack(bits, 2, rng):
            d = cc.black_density(s)
            self.assertGreater(d, 0.35)
            self.assertLess(d, 0.85)

    def test_deterministic_with_seed(self):
        bits = make_bits(TEXT_IMAGE)
        a = cc.split_stack(bits, 3, random.Random(99))
        b = cc.split_stack(bits, 3, random.Random(99))
        self.assertEqual(a, b)
        c = cc.split_stack(bits, 3, random.Random(100))
        self.assertNotEqual(a, c)

    def test_xor_2of2_exact(self):
        bits = make_bits(TEXT_IMAGE)
        shares = cc.split_xor(bits, 2, random.Random(3))
        got = cc.reveal_xor([cc.to_rows(s) for s in shares], 2)
        self.assertEqual(bits, got)

    def test_xor_4of4_exact(self):
        bits = make_bits(TEXT_IMAGE)
        shares = cc.split_xor(bits, 4, random.Random(5))
        got = cc.reveal_xor([cc.to_rows(s) for s in shares], 4)
        self.assertEqual(bits, got)

    def test_xor_shares_are_random(self):
        bits = make_bits(TEXT_IMAGE)
        shares = cc.split_xor(bits, 2, random.Random(8))
        d1 = cc.black_density(shares[0])
        d2 = cc.black_density(shares[1])
        self.assertAlmostEqual(d1, 0.5, delta=0.25)
        self.assertAlmostEqual(d2, 0.5, delta=0.25)


class BinarizeTests(unittest.TestCase):
    def test_threshold_black_and_white(self):
        rows = [(255, 255, 255, 255)] * 3 + [(0, 0, 0, 255)] * 3
        row = [rows]
        bits = cc.binarize(row)
        self.assertEqual(bits[0], [False, False, False, True, True, True])

    def test_dither_gradient(self):
        row = [[(int(255 - i * 40), int(255 - i * 40), 255 - i * 40, 255)
                for i in range(9)]]
        bits = cc.binarize(row, dither=True)
        self.assertEqual(len(bits[0]), 9)
        self.assertTrue(any(bits[0]))
        self.assertFalse(all(bits[0]))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "crypto_couples.py"), *argv],
            capture_output=True, text=True, timeout=120)
        return proc

    def test_demo_split_reveal_end_to_end(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            msg = os.path.join(tmp, "message.png")
            demos = self.run_cli("demo", msg, "--text", "HELLO", "--scale", "4")
            self.assertEqual(demos.returncode, 0, demos.stderr)

            pfx = os.path.join(tmp, "share")
            split = self.run_cli("split", msg, "--out", pfx,
                                 "--shares", "2", "--method", "stack",
                                 "--seed", "42")
            self.assertEqual(split.returncode, 0, split.stderr)
            s1, s2 = f"{pfx}.1.png", f"{pfx}.2.png"
            self.assertTrue(os.path.exists(s1) and os.path.exists(s2))

            out = os.path.join(tmp, "revealed.png")
            rev = self.run_cli("reveal", s1, s2, "--out", out, "--method", "stack")
            self.assertEqual(rev.returncode, 0, rev.stderr)

            with open(msg, "rb") as fh:
                w1, h1, msg_rows = cc.png_decode(fh.read())
            with open(out, "rb") as fh:
                w2, h2, rev_rows = cc.png_decode(fh.read())
            self.assertEqual((w1, h1), (w2, h2))
            self.assertEqual(cc.binarize(msg_rows), cc.binarize(rev_rows))

    def test_cli_missing_files_errors(self):
        proc = self.run_cli("reveal", "/nonexistent.1.png", "/nonexistent.2.png",
                            "--out", "/tmp/x.png", "--method", "stack")
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()