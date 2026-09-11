#!/usr/bin/env python3
"""Tests for crypto_media (audio / bytes / Shamir / XOR)."""
import os
import random
import struct
import subprocess
import sys
import unittest
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import crypto_media as cm  # noqa: E402

BIN = os.path.join(ROOT, "crypto_media.py")


def _sine_wav(path, freq=440, seconds=1, ch=1, sw=2, rate=44100):
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(rate)
        frames = bytearray()
        n = int(rate * seconds)
        for i in range(n):
            v = int(0.5 * 32767 * (1 if (i * freq // rate) % 2 else -1))
            frames += struct.pack("<" + ("h" if sw == 2 else "B"), v)
        w.writeframes(bytes(frames))


class GFTests(unittest.TestCase):
    def test_completeness(self):
        self.assertTrue(all(x is not None for x in cm._LOG[1:]))
        self.assertEqual(len(set(cm._EXP[:255])), 255)

    def test_mul_commutative(self):
        for _ in range(200):
            a, b = random.randrange(256), random.randrange(256)
            self.assertEqual(cm.gf_mul(a, b), cm.gf_mul(b, a))

    def test_inv_roundtrip(self):
        for a in range(1, 256):
            self.assertEqual(cm.gf_mul(a, cm.gf_inv(a)), 1)

    def test_div_as_mul_inv(self):
        a, b = random.randrange(1, 256), random.randrange(1, 256)
        self.assertEqual(cm.gf_div(a, b), cm.gf_mul(a, cm.gf_inv(b)))


class ShamirTests(unittest.TestCase):
    def test_2_of_3(self):
        data = bytes(range(256)) * 4
        shares = cm.shamir_split(data, 3, 2, random.Random(9))
        self.assertEqual(len(shares), 3)
        for i, j in ((0, 1), (0, 2), (1, 2)):
            self.assertEqual(cm.shamir_reveal([shares[i], shares[j]]), data)

    def test_3_of_4(self):
        data = b"secret!" * 100
        shares = cm.shamir_split(data, 4, 3, random.Random(7))
        self.assertEqual(cm.shamir_reveal([shares[0], shares[2], shares[3]]), data)

    def test_wrong_subset_fails(self):
        data = b"hello"
        shares = cm.shamir_split(data, 3, 2, random.Random(4))
        self.assertNotEqual(cm.shamir_reveal([shares[0], shares[1]]), b"WRONG")

    def test_empty_data(self):
        shares = cm.shamir_split(b"", 3, 2, random.Random(1))
        self.assertEqual(cm.shamir_reveal([shares[0], shares[2]]), b"")

    def test_deterministic(self):
        data = b"abc"
        a = cm.shamir_split(data, 3, 2, random.Random(11))
        b = cm.shamir_split(data, 3, 2, random.Random(11))
        self.assertEqual(a, b)


class XORTests(unittest.TestCase):
    def test_2_of_2(self):
        data = os.urandom(1000)
        shares = cm.xor_split(data, 2, random.Random(5))
        self.assertEqual(len(shares), 2)
        self.assertEqual(cm.xor_reveal(shares), data)

    def test_4_of_4(self):
        data = bytes(range(256)) * 2
        shares = cm.xor_split(data, 4, random.Random(6))
        self.assertEqual(cm.xor_reveal(shares), data)

    def test_shares_are_random(self):
        data = os.urandom(5000)
        shares = cm.xor_split(data, 3, random.Random(7))
        for s in shares:
            self.assertNotEqual(s, data)


class AdditiveTests(unittest.TestCase):
    def test_split_reveal_roundtrip(self):
        samples = [0.5 * (1 if (i % 1000) < 500 else -0.5)
                   for i in range(44100)]
        rng = random.Random(12)
        shares = cm.additive_split_audio(samples, 3, rng)
        revealed = cm.additive_reveal_audio(shares)
        err = max(abs(a - b) for a, b in zip(samples, revealed))
        self.assertLessEqual(err, 0.001)

    def test_shares_are_noise(self):
        samples = [0.9] * 1000
        shares = cm.additive_split_audio(samples, 2, random.Random(8))
        for s in shares[:1]:
            amp = max(abs(v) for v in s)
            self.assertLess(amp, 0.1)


class CLIByteTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, BIN, *args],
            capture_output=True, text=True, timeout=120)

    def test_xor_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            orig = os.path.join(d, "data.bin")
            with open(orig, "wb") as f:
                f.write(os.urandom(8000))
            self.assertEqual(self._run(
                "split-bytes", orig, "--out", os.path.join(d, "s"),
                "--method", "xor", "--shares", "3").returncode, 0)
            self.assertEqual(self._run(
                "reveal-bytes",
                *[os.path.join(d, f"s.{i}.shard") for i in range(1, 4)],
                "--out", os.path.join(d, "out.bin"),
                "--method", "xor").returncode, 0)
            with open(orig, "rb") as f, open(os.path.join(d, "out.bin"), "rb") as g:
                self.assertEqual(f.read(), g.read())

    def test_shamir_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            orig = os.path.join(d, "data.bin")
            with open(orig, "wb") as f:
                f.write(os.urandom(4000))
            self.assertEqual(self._run(
                "split-bytes", orig, "--out", os.path.join(d, "s"),
                "--method", "shamir", "--shares", "4",
                "--threshold", "3").returncode, 0)
            self.assertEqual(self._run(
                "reveal-bytes", os.path.join(d, "s.1.shard"),
                os.path.join(d, "s.3.shard"), os.path.join(d, "s.4.shard"),
                "--out", os.path.join(d, "out.bin"),
                "--method", "shamir").returncode, 0)
            with open(orig, "rb") as f, open(os.path.join(d, "out.bin"), "rb") as g:
                self.assertEqual(f.read(), g.read())


class CLIAudioTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, BIN, *args],
            capture_output=True, text=True, timeout=120)

    def test_xor_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            orig = os.path.join(d, "a.wav")
            _sine_wav(orig)
            self.assertEqual(self._run(
                "split-audio", orig, "--out", os.path.join(d, "s"),
                "--method", "xor", "--shares", "2").returncode, 0)
            self.assertEqual(self._run(
                "reveal-audio", os.path.join(d, "s.1.wav"),
                os.path.join(d, "s.2.wav"),
                "--out", os.path.join(d, "r.wav"),
                "--method", "xor").returncode, 0)
            with wave.open(orig, "rb") as a, wave.open(os.path.join(d, "r.wav"), "rb") as b:
                self.assertEqual(a.readframes(a.getnframes()),
                                 b.readframes(b.getnframes()))

    def test_additive_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            orig = os.path.join(d, "a.wav")
            _sine_wav(orig)
            self.assertEqual(self._run(
                "split-audio", orig, "--out", os.path.join(d, "s"),
                "--method", "additive", "--shares", "3",
                "--seed", "42").returncode, 0)
            self.assertEqual(self._run(
                "reveal-audio", os.path.join(d, "s.1.wav"),
                os.path.join(d, "s.2.wav"), os.path.join(d, "s.3.wav"),
                "--out", os.path.join(d, "r.wav"),
                "--method", "additive").returncode, 0)


if __name__ == "__main__":
    unittest.main()