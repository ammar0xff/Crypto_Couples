#!/usr/bin/env python3
"""Crypto_Couples media & byte extensions: secret sharing for audio, video,
and arbitrary files, on top of the image tool's (n,n) visual cryptography.

Audio  : additive (superposition - play every share at once and hear the
         message), exact XOR, or k-of-n Shamir over GF(2**8).
Video  : per-frame visual cryptography (stack or XOR) with fresh randomness
         per frame; audio track split alongside; shares are PNG-frame dirs
         (optionally baked into a lossless movie with ffmpeg if present).
Bytes  : any file into n XOR shares or k-of-n Shamir shares.

Pure stdlib except the optional ffmpeg bridge (Video split/reveal).
"""

import argparse
import json
import os
import random
import subprocess
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto_couples import (binarize, png_decode,  # noqa: E402
                            png_encode, reveal_stack, reveal_xor,
                            split_stack, split_xor, to_rows)

# ---------------------------------------------------------------------------
# GF(2**8) arithmetic (primitive polynomial 0x11B) for Shamir shares ----------
# ---------------------------------------------------------------------------

_GF_POLY = 0x11B
_GEN = 0x03
_EXP = [0] * 512
_LOG = [None] * 256


def _gf_mul_ref(a, b):
    """Reference field multiplication (right-to-left shift-and-xor)."""
    out = 0
    while b:
        if b & 1:
            out ^= a
        a <<= 1
        if a & 0x100:
            a ^= _GF_POLY
        b >>= 1
    return out & 0xFF


def _init_gf():
    """exp/log tables with primitive root 3 (standard AES polynomial)."""
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x = _gf_mul_ref(x, _GEN)
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_init_gf()


def gf_add(a, b):
    return a ^ b


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def gf_div(a, b):
    if b == 0:
        raise ZeroDivisionError("division by zero in GF(2**8)")
    if a == 0:
        return 0
    return _EXP[(_LOG[a] - _LOG[b]) % 255]


def gf_pow(a, e):
    out = 1
    while e:
        if e & 1:
            out = gf_mul(out, a)
        a = gf_mul(a, a)
        e >>= 1
    return out


def gf_inv(a):
    if a == 0:
        raise ZeroDivisionError("zero has no inverse in GF(2**8)")
    return gf_pow(a, 254)


# ---------------------------------------------------------------------------
# byte-level schemes (shared by audio data & the bytes tool) -------------------
# ---------------------------------------------------------------------------

def _xor_bytes(a, b):
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(
        len(a), "big")


def xor_split(data, n, rng):
    """n-of-n XOR shares of a byte string. Last share is the running XOR."""
    shares = [rng.randbytes(len(data)) for _ in range(n - 1)]
    running = bytearray(data)
    for s in shares:
        running = bytearray(_xor_bytes(bytes(running), s))
    return shares + [bytes(running)]


def xor_reveal(chunks):
    out = chunks[0]
    for c in chunks[1:]:
        out = _xor_bytes(out, c)
    return out


def shamir_split(data, n, k, rng):
    """Split data into n shares, any k of which reconstruct exactly (k-of-n).

    Each byte b lives on the polynomial f(x) = b + a1*x + ... + a{k-1}*x^{k-1}
    with fresh random coefficients per byte; share i stores f(i). f(0) = b.
    """
    if not 1 <= k <= n:
        raise ValueError("require 1 <= threshold <= shares")
    length = len(data)
    if length == 0:
        return [(i + 1, b"") for i in range(n)]
    if k == 1:
        return [(i + 1, bytes(data)) for i in range(n)]

    coeffs = [rng.randbytes(length) for _ in range(k - 1)]
    powers = []
    for xi in range(1, n + 1):
        pows = [xi]
        for _ in range(k - 2):
            pows.append(gf_mul(pows[-1], xi))
        powers.append(pows)

    shares = [bytearray(length) for _ in range(n)]
    for t in range(length):
        b = data[t]
        for si in range(n):
            val = b
            pows = powers[si]
            for j in range(k - 1):
                val ^= gf_mul(coeffs[j][t], pows[j])
            shares[si][t] = val
    return [(si + 1, bytes(shares[si])) for si in range(n)]


def shamir_reveal(points):
    """points: list of (x_index, data). Uses all points given (>= k)."""
    if len(points) < 1:
        raise ValueError("no shares")
    xs = [p[0] for p in points]
    if len(set(xs)) != len(xs):
        raise ValueError("duplicate share index in reconstruction")
    k = len(xs)
    basis = []
    for i in range(k):
        num, den = 1, 1
        for m in range(k):
            if m == i:
                continue
            num = gf_mul(num, xs[m])
            den = gf_mul(den, gf_add(xs[m], xs[i]))
        basis.append(gf_div(num, den))
    length = min(len(p[1]) for p in points)
    out = bytearray(length)
    for t in range(length):
        val = 0
        for i in range(k):
            val ^= gf_mul(basis[i], points[i][1][t])
        out[t] = val
    return bytes(out)


_SHAMIR_SOFT_CAP = 8 * 1024 * 1024


def _shamir_memory_warn(length):
    if length > _SHAMIR_SOFT_CAP:
        print(f"[!] shamir: {length / 1e6:.1f} MB - pure-python GF loop is "
              f"slow for large payloads; consider XOR (n-of-n) instead")


# ---------------------------------------------------------------------------
# wave (PCM) io ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def wav_params(path):
    with wave.open(path, "rb") as w:
        if w.getcomptype() != "NONE":
            raise ValueError("only uncompressed PCM WAV is supported")
        return (w.getnchannels(), w.getsampwidth(), w.getframerate())


def wav_read_data(path):
    with wave.open(path, "rb") as w:
        return w.readframes(w.getnframes())


def wav_read_floats(path):
    """Read samples as floats in [-1, 1]; 8-bit unsigned / 16-bit signed."""
    paren = wav_params(path)
    _, sampwidth, _rate = paren
    data = wav_read_data(path)
    if sampwidth == 2:
        arr = __import__("array").array("h")
        arr.frombytes(data)
        if sys.byteorder != "little":
            arr.byteswap()
        return [v / 32768.0 for v in arr], paren
    if sampwidth == 1:
        return [(b / 128.0) - 1.0 for b in data], paren
    raise ValueError("additive mode supports 8-bit or 16-bit PCM only")


def wav_write(path, paren, data_bytes):
    nch, sw, fr = paren
    with wave.open(path, "wb") as w:
        w.setnchannels(nch)
        w.setsampwidth(sw)
        w.setframerate(fr)
        w.writeframes(data_bytes)


def floats_to_int16(samples):
    a = __import__("array").array("h")
    for v in samples:
        a.append(max(-32768, min(32767, round(v * 32768.0))))
    if sys.byteorder != "little":
        a.byteswap()
    return a.tobytes()


# ---------------------------------------------------------------------------
# audio schemes -----------------------------------------------------------------
# ---------------------------------------------------------------------------

def additive_split_audio(samples, n, rng):
    """Superposition shares: sum of every share equals the message exactly
    in continuous time; playback through speakers adds in the air."""
    peak = max((abs(v) for v in samples), default=0.0)
    amp = max(0.0, (0.95 - min(peak, 0.95))) / (n - 1) if n > 1 else 0.0
    if n > 1 and amp <= 0.0:
        print("[!] message already near full scale; shares cannot hide it "
              "additively without clipping")
    noise = [[rng.uniform(-amp, amp) for _ in samples] for _ in range(n - 1)]
    last = [samples[i] - sum(nn[i] for nn in noise)
            for i in range(len(samples))]
    return noise + [last]


def additive_reveal_audio(share_list):
    length = len(share_list[0])
    return [sum(s[i] for s in share_list) for i in range(length)]


# ---------------------------------------------------------------------------
# video helpers (ffmpeg bridge, optional) --------------------------------------
# ---------------------------------------------------------------------------

_FRAME_GLOB = "frame_%04d.png"


def _has_ffmpeg():
    return subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0


def ffmpeg_dump_frames(video, outdir):
    os.makedirs(outdir, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", video, "-start_number", "0001",
         os.path.join(outdir, _FRAME_GLOB)],
        check=True, capture_output=True)


def ffmpeg_extract_audio(video, wavpath):
    subprocess.run(
        ["ffmpeg", "-y", "-i", video, "-vn", "-acodec", "pcm_s16le",
         "-ar", "44100", "-ac", "2", wavpath],
        check=True, capture_output=True)


def ffmpeg_probe_fps(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True)
    parts = out.stdout.strip().split("/")
    try:
        num, den = float(parts[0]), float(parts[1])
        return num / den if den else 24.0
    except (ValueError, IndexError):
        return 24.0


def ffmpeg_has_audio(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True)
    return bool(out.stdout.strip())


def pick_lossless_encoder():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    if "ffv1" in out:
        return "ffv1"
    if "libx264" in out:
        return "libx264"
    if "png" in out:
        return "png"
    raise RuntimeError("no lossless video encoder available in ffmpeg")


def ffmpeg_encode_frames(frames_dir, fps, out_path, audio=None):
    enc = pick_lossless_encoder()
    cmd = ["ffmpeg", "-y", "-framerate", str(fps),
           "-i", os.path.join(frames_dir, _FRAME_GLOB)]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-c:v", enc]
    if enc == "libx264":
        cmd += ["-pix_fmt", "yuv420p", "-qp", "0"]
    if audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [f"{out_path}.mkv"]
    subprocess.run(cmd, check=True, capture_output=True)


def list_frames(directory):
    names = sorted(fn for fn in os.listdir(directory) if fn.startswith("frame_"))
    if not names:
        raise ValueError(f"no frame_*.png found in {directory}")
    return names


def read_frame(path):
    with open(path, "rb") as fh:
        return png_decode(fh.read())


def write_frame(path, bits):
    with open(path, "wb") as fh:
        fh.write(png_encode(to_rows(bits)))


# ---------------------------------------------------------------------------
# cli -------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _seed_int(seed):
    if seed is None:
        return random.SystemRandom().randrange(2 ** 32)
    return seed


def _print(path, msg):
    print(f"[*] {msg}: {path}")


def cmd_split_audio(args):
    paren = wav_params(args.input)
    _, sampwidth, _rate = paren
    data = wav_read_data(args.input)
    if sampwidth not in (1, 2):
        raise SystemExit("[!] WAV must be 8-bit or 16-bit PCM")

    if args.method == "additive":
        samples, paren = wav_read_floats(args.input)
        rng = random.Random(args.seed)
        shares = additive_split_audio(samples, args.shares, rng)
        for i, sh in enumerate(shares, 1):
            path = f"{args.out}.{i}.wav"
            wav_write(path, paren, floats_to_int16(sh))
            _print(path, f"additive share {i}/{args.shares}")
        print("[*] play every share at the same time (same loudness, aligned) "
              "to hear the message in the air")
    elif args.method == "xor":
        rng = random.Random(args.seed)
        for i, chunk in enumerate(xor_split(data, args.shares, rng), 1):
            path = f"{args.out}.{i}.wav"
            wav_write(path, paren, chunk)
            _print(path, f"xor share {i}/{args.shares}")
    else:  # shamir
        rng = random.Random(args.seed)
        _shamir_memory_warn(len(data))
        for (i, chunk) in shamir_split(data, args.shares, args.threshold, rng):
            path = f"{args.out}.{i}.wav"
            wav_write(path, paren, chunk)
            _print(path, f"shamir share {i}/{args.shares} (k={args.threshold})")
    print(f"[*] keep the shares apart; "
          f"{args.threshold if args.method == 'shamir' else args.shares} "
          f"of {args.shares} reveal the message")
    return 0


def cmd_reveal_audio(args):
    paren = wav_params(args.shares_files[0])
    for p in args.shares_files[1:]:
        if wav_params(p) != paren:
            raise SystemExit("[!] all shares must have identical WAV format")
    paths = sorted(args.shares_files)
    if args.method == "additive":
        chans = []
        for p in paths:
            samples, _ = wav_read_floats(p)
            chans.append(samples)
        wav_write(args.out, paren,
                  floats_to_int16(additive_reveal_audio(chans)))
    elif args.method == "xor":
        chunks = [wav_read_data(p) for p in paths]
        wav_write(args.out, paren, xor_reveal(chunks))
    else:  # shamir
        points = [_share_index(p) for p in paths]
        if len(set(points)) != len(points):
            raise SystemExit("[!] duplicate share index in reconstruction")
        points = [(ix, wav_read_data(p)) for (ix, p) in zip(points, paths)]
        wav_write(args.out, paren, shamir_reveal(points))
    _print(args.out, "write restored audio")
    return 0


def _share_index(path):
    """Parse the share number out of '<prefix>.<N>.wav' / '...shard'."""
    parts = os.path.splitext(os.path.basename(path))[0].split(".")
    return int(parts[-1])


def cmd_split_video(args):
    work = args.outdir
    os.makedirs(work, exist_ok=True)
    seed_base = _seed_int(args.seed)

    meta = {"type": "video", "version": 1, "seed": seed_base,
            "method": args.method, "shares": args.shares,
            "audio": None}

    frames_src = args.input
    if os.path.isdir(frames_src):
        frame_names = list_frames(frames_src)
        fps = args.fps or 24.0
    else:
        if not _has_ffmpeg():
            raise SystemExit("[!] ffmpeg required to decode video input")
        tmp = os.path.join(work, ".frames_src")
        ffmpeg_dump_frames(frames_src, tmp)
        frame_names = list_frames(tmp)
        frames_src = tmp
        fps = args.fps or ffmpeg_probe_fps(args.input)
        if not args.no_audio and ffmpeg_has_audio(args.input):
            audio_wav = os.path.join(work, ".audio_in.wav")
            ffmpeg_extract_audio(args.input, audio_wav)
    meta["fps"] = float(fps)

    # shares of the audio track
    pre = os.path.join(work, "audio_share")
    if os.path.isfile(os.path.join(work, ".audio_in.wav")):
        aud_shares = args.audio_shares or args.shares
        aud_threshold = args.audio_threshold or aud_shares
        aud = argparse.Namespace(
            input=os.path.join(work, ".audio_in.wav"), out=pre,
            shares=aud_shares, threshold=aud_threshold,
            method=args.audio_method, seed=seed_base)
        cmd_split_audio(aud)
        meta["audio"] = {"method": args.audio_method,
                         "shares": aud_shares,
                         "threshold": aud_threshold,
                         "files": [f"{pre}.{i}.wav"
                                   for i in range(1, aud_shares + 1)]}

    # visual shares: per-frame fresh randomness (TV static), n-of-n
    for c in range(1, args.shares + 1):
        os.makedirs(os.path.join(work, f"{c}"), exist_ok=True)
    for j, name in enumerate(frame_names, 1):
        _w, _h, rows = read_frame(os.path.join(frames_src, name))
        bits = binarize(rows, args.threshold, args.dither)
        rng = random.Random(seed_base + j)
        share_bits = (split_stack(bits, args.shares, rng)
                      if args.method == "stack" else
                      split_xor(bits, args.shares, rng))
        for c, sb in enumerate(share_bits, 1):
            write_frame(os.path.join(work, f"{c}", f"frame_{j:04d}.png"), sb)

    meta["frames"] = len(frame_names)
    meta["frame_width"], meta["frame_height"] = (
        len(bits[0]) if bits else 0, len(bits))
    with open(os.path.join(work, "manifest.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    _print(work, "write share bundle")
    print(f"[*] {len(frame_names)} frames into {args.shares} share dirs; "
          f"overlay/XOR all {args.shares} to see the video")
    return 0


def cmd_reveal_video(args):
    share_dirs = args.share_dirs
    if len(share_dirs) < 2:
        raise SystemExit("[!] need at least 2 share directories")
    first_names = list_frames(share_dirs[0])
    for d in share_dirs[1:]:
        if list_frames(d) != first_names:
            raise SystemExit("[!] share directories contain different frames")

    # prefer the bundle manifest when present so reveal just works
    bundle = os.path.dirname(os.path.abspath(share_dirs[0]))
    manifest = {}
    manifest_path = os.path.join(bundle, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path) as fh:
            manifest = json.load(fh)

    method = manifest.get("method", args.method)
    fps = args.fps or manifest.get("fps", 24.0)
    audio_meta = manifest.get("audio") or {}

    os.makedirs(args.outdir, exist_ok=True)
    out_frames = os.path.join(args.outdir, "video")
    os.makedirs(out_frames, exist_ok=True)
    for j, name in enumerate(first_names, 1):
        rows_list = []
        for d in share_dirs:
            _, _, rows = read_frame(os.path.join(d, name))
            rows_list.append(rows)
        bits = (reveal_stack(rows_list, len(share_dirs))
                if method == "stack" else
                reveal_xor(rows_list, len(share_dirs)))
        write_frame(os.path.join(out_frames, f"frame_{j:04d}.png"), bits)

    restored_audio = None
    if not args.no_audio and not audio_meta.get("no_audio"):
        audio_files = sorted(
            os.path.join(bundle, f)
            for f in os.listdir(bundle)
            if f.startswith("audio_share.") and f.endswith(".wav"))
        if len(audio_files) >= 2:
            aud = argparse.Namespace(
                shares_files=audio_files,
                method=audio_meta.get("method", "xor"),
                out=os.path.join(args.outdir, "audio_restored.wav"))
            cmd_reveal_audio(aud)
            restored_audio = aud.out

    if args.encode:
        if not _has_ffmpeg():
            raise SystemExit("[!] ffmpeg required for --encode")
        ffmpeg_encode_frames(out_frames, float(fps),
                             os.path.join(args.outdir, args.encode),
                             restored_audio)
        _print(os.path.join(args.outdir, f"{args.encode}.mkv"),
               "encoded restored video")
    else:
        _print(out_frames, "wrote restored frames")
        if restored_audio:
            _print(restored_audio, "wrote restored audio")
    return 0


def cmd_split_bytes(args):
    with open(args.input, "rb") as fh:
        data = fh.read()
    threshold = args.threshold or args.shares
    rng = random.Random(args.seed if args.seed is not None
                        else random.SystemRandom().randrange(2 ** 32))
    if args.method == "xor":
        chunks = xor_split(data, args.shares, rng)
        for i, c in enumerate(chunks, 1):
            with open(f"{args.out}.{i}.shard", "wb") as fh:
                fh.write(c)
            _print(f"{args.out}.{i}.shard", f"xor share {i}/{args.shares}")
        print(f"[*] any {args.shares} of {args.shares} reveal the file")
        return 0
    _shamir_memory_warn(len(data))
    for (i, chunk) in shamir_split(data, args.shares, threshold, rng):
        with open(f"{args.out}.{i}.shard", "wb") as fh:
            fh.write(chunk)
        _print(f"{args.out}.{i}.shard",
               f"shamir share {i}/{args.shares} (k={threshold})")
    print(f"[*] any {threshold} of {args.shares} reveal the file")
    return 0


def cmd_reveal_bytes(args):
    paths = sorted(args.share_files)
    data = [open(p, "rb").read() for p in paths]
    if args.method == "xor":
        out = xor_reveal(data)
    else:
        points = [(_share_index(p), c) for p, c in zip(paths, data)]
        out = shamir_reveal(points)
    with open(args.out, "wb") as fh:
        fh.write(out)
    _print(args.out, "write restored file")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="crypto-media",
        description="Visual-cryptography ideas for audio, video and bytes.",
        epilog="examples:\n"
               "  crypto_media.py split-audio voice.wav --out a --method additive --shares 2\n"
               "  crypto_media.py reveal-audio a.1.wav a.2.wav --out voice.wav --method additive\n"
               "  crypto_media.py split-audio voice.wav --out a --method shamir --shares 3 --threshold 2\n"
               "  crypto_media.py split-bytes secret.bin --out b --method xor --shares 2\n"
               "  crypto_media.py reveal-bytes b.2.shard b.1.shard --out secret.bin --method xor\n"
               "  crypto_media.py split-video clip.mp4 --outdir shares --shares 2 --method stack --fps 24\n"
               "  crypto_media.py reveal-video shares/1 shares/2 --outdir restored --method stack\n"
               "  crypto_media.py split-video frames/ --outdir shares --shares 2 --method stack\n"
               "  crypto_media.py reveal-video shares/1 shares/2 --outdir r --method xor --encode final")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("split-audio", help="split a WAV into shares")
    s.add_argument("input", help="input PCM WAV (8 or 16-bit)")
    s.add_argument("--out", required=True, help="output prefix -> <out>.N.wav")
    s.add_argument("--shares", "-n", type=int, default=2)
    s.add_argument("--method", choices=("additive", "xor", "shamir"),
                   default="additive")
    s.add_argument("--threshold", "-k", type=int, default=None,
                   help="shamir: how many shares are needed (default: all)")
    s.add_argument("--seed", type=int, default=None)
    s.set_defaults(func=cmd_split_audio)

    s = sub.add_parser("reveal-audio", help="recombine audio shares")
    s.add_argument("shares_files", nargs="+", metavar="SHARE.wav")
    s.add_argument("--out", required=True)
    s.add_argument("--method", choices=("additive", "xor", "shamir"),
                   default="additive")
    s.set_defaults(func=cmd_reveal_audio)

    s = sub.add_parser("split-bytes", help="split any file into shares")
    s.add_argument("input")
    s.add_argument("--out", required=True, help="output prefix -> <out>.N.shard")
    s.add_argument("--method", choices=("xor", "shamir"), default="xor")
    s.add_argument("--shares", "-n", type=int, default=2)
    s.add_argument("--threshold", "-k", type=int, default=None)
    s.add_argument("--seed", type=int, default=None)
    s.set_defaults(func=cmd_split_bytes)

    s = sub.add_parser("reveal-bytes", help="recombine byte shares")
    s.add_argument("share_files", nargs="+", metavar="SHARE.shard")
    s.add_argument("--out", required=True)
    s.add_argument("--method", choices=("xor", "shamir"), default="xor")
    s.set_defaults(func=cmd_reveal_bytes)

    s = sub.add_parser("split-video", help="split a video or PNG-frame dir")
    s.add_argument("input", help="video file or directory of frame_NNNN.png")
    s.add_argument("--outdir", required=True)
    s.add_argument("--shares", "-n", type=int, default=2)
    s.add_argument("--method", choices=("stack", "xor"), default="stack")
    s.add_argument("--fps", type=float, default=None)
    s.add_argument("--no-audio", action="store_true")
    s.add_argument("--audio-method", choices=("additive", "xor", "shamir"),
                   default="xor")
    s.add_argument("--audio-shares", type=int, default=None)
    s.add_argument("--audio-threshold", type=int, default=None)
    s.add_argument("--threshold", type=int, default=128)
    s.add_argument("--dither", action="store_true")
    s.add_argument("--seed", type=int, default=None)
    s.set_defaults(func=cmd_split_video)

    s = sub.add_parser("reveal-video", help="recombine a video bundle")
    s.add_argument("share_dirs", nargs="+", metavar="SHARE_DIR")
    s.add_argument("--outdir", required=True)
    s.add_argument("--method", choices=("stack", "xor"), default="stack")
    s.add_argument("--fps", type=float, default=None)
    s.add_argument("--encode", metavar="NAME", default=None,
                   help="ffmpeg-encode the result as NAME.mkv (lossless)")
    s.add_argument("--no-audio", action="store_true")
    s.set_defaults(func=cmd_reveal_video)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "reveal-audio":
        if args.method in ("xor", "shamir") and all(
                p.endswith(".wav") for p in args.shares_files):
            sizes = {os.path.getsize(p) for p in args.shares_files}
            if len(sizes) > 1:
                print("[!] warning: share files differ in size - results "
                      "may be truncated")
    try:
        return args.func(args)
    except (ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"[!] {error}")
    except OSError as error:
        raise SystemExit(f"[!] {error}")


if __name__ == "__main__":
    raise SystemExit(main())