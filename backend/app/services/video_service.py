"""Video crypto adapter. Mirrors the CLI video flow frame-for-frame against
the core primitives; ffmpeg is only a bridge (decode frames, probe FPS,
encode result)."""

from __future__ import annotations

import json
import random
import shutil
import zipfile
from pathlib import Path

from ..core_loader import cm
from ..deps import ops
from ..schemas.crypto import VideoRevealOptions, VideoSplitOptions
from ..security.errors import ApiError
from .ffmpeg_service import require

_MANIFEST = "manifest.json"


def _check_cancel(rec) -> None:
    if rec.cancel_event.is_set():
        raise ApiError(code="CANCELLED", message="Operation cancelled.")


def _seed_int(seed: int | None) -> int:
    if seed is None:
        return random.SystemRandom().randrange(2**32)
    return seed % (2**32)


def _zip_dir(zip_path: Path, src_dir: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for child in sorted(src_dir.iterdir()):
            if child.is_file():
                zf.write(child, arcname=child.name)


def _unzip(zip_path: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target)


def _audio_split_to(audio_wav: Path, pre: Path, *, shares: int,
                    threshold: int, method: str, seed: int) -> None:
    paren = cm.wav_params(str(audio_wav))
    _, sampwidth, _ = paren
    if sampwidth not in (1, 2):
        raise ApiError(code="UNSUPPORTED_FORMAT",
                       message="Audio track is not 8/16-bit PCM after decode.")
    data = cm.wav_read_data(str(audio_wav))
    rng = random.Random(seed)
    if method == "additive":
        samples, paren = cm.wav_read_floats(str(audio_wav))
        for i, sh in enumerate(cm.additive_split_audio(samples, shares, rng), 1):
            cm.wav_write(f"{pre}.{i}.wav", paren, cm.floats_to_int16(sh))
    elif method == "xor":
        for i, chunk in enumerate(cm.xor_split(data, shares, rng), 1):
            cm.wav_write(f"{pre}.{i}.wav", paren, chunk)
    else:
        for i, chunk in cm.shamir_split(data, shares, threshold, rng):
            cm.wav_write(f"{pre}.{i}.wav", paren, chunk[1])


def _audio_reveal_to(audio_files: list[Path], out_path: Path,
                     method: str) -> None:
    paren = cm.wav_params(str(audio_files[0]))
    paths = sorted(str(p) for p in audio_files)
    if method == "additive":
        chans = [cm.wav_read_floats(p)[0] for p in paths]
        cm.wav_write(str(out_path), paren,
                     cm.floats_to_int16(cm.additive_reveal_audio(chans)))
    elif method == "xor":
        chunks = [cm.wav_read_data(p) for p in paths]
        cm.wav_write(str(out_path), paren, cm.xor_reveal(chunks))
    else:
        points = [(cm._share_index(p), cm.wav_read_data(p)) for p in paths]
        if len({x for x, _ in points}) != len(points):
            raise ApiError(code="INVALID_SHARE",
                           message="Duplicate share index in video audio.")
        cm.wav_write(str(out_path), paren, cm.shamir_reveal(points))


class VideoCryptoService:
    def split(self, rec, options: VideoSplitOptions) -> None:
        if len(rec.input_names) != 1:
            raise ApiError(code="INVALID_PARAMETER",
                           message="Video split requires exactly one file.")
        input_path = rec.dir / "input" / rec.input_names[0]
        work = rec.dir / "work"
        work.mkdir(parents=True, exist_ok=True)
        seed_base = _seed_int(options.seed)

        ops.report(rec, 5, "Preparing input frames")
        frames_src: Path
        frame_names: list[str]
        fps: float
        if input_path.suffix.lower() == ".zip":
            unpack = work / ".frames_zip"
            _unzip(input_path, unpack)
            try:
                frame_names = cm.list_frames(str(unpack))
            except ValueError:
                raise ApiError(code="INVALID_SHARE",
                               message="ZIP does not contain frame_*.png files.")
            frames_src = unpack
            fps = options.fps or 24.0
        else:
            require()
            try:
                frames_src_f = work / ".frames_src"
                cm.ffmpeg_dump_frames(str(input_path), str(frames_src_f))
                frame_names = cm.list_frames(str(frames_src_f))
                fps = options.fps or cm.ffmpeg_probe_fps(str(input_path))
                frames_src = frames_src_f
            except Exception as exc:
                raise ApiError(
                    code="UNSUPPORTED_FORMAT",
                    message="FFmpeg could not decode this video.",
                    details={"hint": type(exc).__name__}) from None

        meta: dict = {
            "type": "video", "version": 1, "seed": seed_base,
            "method": options.method, "shares": options.shares,
            "audio": None, "fps": float(fps),
            "frames": len(frame_names),
        }

        # extract + split the audio track, same as the CLI
        audio_wav = work / ".audio_in.wav"
        if not options.no_audio and settings_has_audio(input_path):
            require()
            try:
                cm.ffmpeg_extract_audio(str(input_path), str(audio_wav))
            except Exception as exc:
                raise ApiError(code="UNSUPPORTED_FORMAT",
                               message="Could not extract audio.",
                               details={"hint": type(exc).__name__}) from None
            aud_shares = options.audio_shares or options.shares
            aud_threshold = options.audio_threshold or aud_shares
            _audio_split_to(audio_wav, work / "audio_share",
                            shares=aud_shares, threshold=aud_threshold,
                            method=options.audio_method, seed=seed_base)
            meta["audio"] = {
                "method": options.audio_method, "shares": aud_shares,
                "threshold": aud_threshold,
                "files": [f"audio_share.{i}.wav"
                          for i in range(1, aud_shares + 1)],
            }
            ops.report(rec, 12, f"Split audio track into {aud_shares} shares")
        else:
            meta["audio"] = {"no_audio": True}

        # per-frame visual cryptography
        first = 20
        span = 70
        every = max(1, len(frame_names) // 200)
        for c in range(1, options.shares + 1):
            (work / str(c)).mkdir(parents=True, exist_ok=True)
        for j, name in enumerate(frame_names, 1):
            _check_cancel(rec)
            _w, _h, rows = cm.read_frame(str(frames_src / name))
            bits = cm.binarize(rows, options.threshold, options.dither)
            rng = random.Random(seed_base + j)
            share_bits = (cm.split_stack(bits, options.shares, rng)
                          if options.method == "stack" else
                          cm.split_xor(bits, options.shares, rng))
            for c, sb in enumerate(share_bits, 1):
                cm.write_frame(str(work / str(c) / f"frame_{j:04d}.png"), sb)
            if j % every == 0 or j == len(frame_names):
                pct = first + int(span * j / len(frame_names))
                ops.report(rec, pct, f"Processing frame {j} of {len(frame_names)}")
        meta["frame_width"], meta["frame_height"] = len(bits[0]), len(bits)
        (work / _MANIFEST).write_text(json.dumps(meta, indent=2))

        # package each share dir as a downloadable zip
        out_dir = rec.dir / "out"
        for c in range(1, options.shares + 1):
            _check_cancel(rec)
            _zip_dir(out_dir / f"{rec.id}.share.{c}.zip", work / str(c))
        shutil.copy2(work / _MANIFEST, out_dir / _MANIFEST)
        ops.report(rec, 97, f"Packaged {len(frame_names)} frames into "
                            f"{options.shares} share bundles")
        ops.finish(rec)

    def reveal(self, rec, options: VideoRevealOptions) -> None:
        work = rec.dir / "work"
        work.mkdir(parents=True, exist_ok=True)

        # unzip uploads; each zip is either a full bundle (manifest + dirs) or
        # a single share dir of frame_*.png files
        share_dirs: list[Path] = []
        bundle: Path | None = None
        for i, name in enumerate(sorted(rec.input_names), 1):
            _check_cancel(rec)
            target = work / "upload" / str(i)
            try:
                _unzip(rec.dir / "input" / name, target)
            except (zipfile.BadZipFile, Exception) as exc:
                if isinstance(exc, zipfile.BadZipFile):
                    raise ApiError(code="INVALID_SHARE",
                                   message=f"Upload {name} is not a ZIP.") from None
                raise
            if (target / _MANIFEST).is_file():
                bundle = target
                for child in sorted(target.iterdir()):
                    if child.is_dir() and _has_frames(child):
                        share_dirs.append(child)
            elif _has_frames(target):
                share_dirs.append(target)

        if len(share_dirs) < 2:
            raise ApiError(code="INVALID_SHARE",
                           message="Need at least 2 share bundles.")

        try:
            first_names = cm.list_frames(str(share_dirs[0]))
        except ValueError:
            raise ApiError(code="INVALID_SHARE",
                           message="Share bundles contain no frame_*.png files.")
        for d in share_dirs[1:]:
            if cm.list_frames(str(d)) != first_names:
                raise ApiError(
                    code="INVALID_SHARE",
                    message="Share bundles contain different frame sequences.")

        manifest: dict = {}
        if bundle is not None and (bundle / _MANIFEST).is_file():
            manifest = json.loads((bundle / _MANIFEST).read_text())
        method = manifest.get("method", options.method)
        fps = options.fps or float(manifest.get("fps", 24.0))
        audio_meta = manifest.get("audio") or {}

        restored = work / "restored"
        restored.mkdir(parents=True, exist_ok=True)
        every = max(1, len(first_names) // 200)
        for j, name in enumerate(first_names, 1):
            _check_cancel(rec)
            rows_list = []
            for d in share_dirs:
                _w, _h, rows = cm.read_frame(str(d / name))
                rows_list.append(rows)
            bits = (cm.reveal_stack(rows_list, len(share_dirs))
                    if method == "stack" else
                    cm.reveal_xor(rows_list, len(share_dirs)))
            cm.write_frame(str(restored / f"frame_{j:04d}.png"), bits)
            if j % every == 0 or j == len(first_names):
                pct = 5 + int(75 * j / len(first_names))
                ops.report(rec, pct, f"Restoring frame {j} of {len(first_names)}")

        # audio track reconstruction (from the bundle)
        restored_audio: Path | None = None
        if bundle is not None and not options.no_audio \
                and not audio_meta.get("no_audio"):
            audio_files = sorted(
                p for p in bundle.iterdir()
                if p.name.startswith("audio_share.") and p.suffix == ".wav")
            if len(audio_files) >= 2:
                restored_audio = work / "audio_restored.wav"
                _audio_reveal_to(audio_files, restored_audio,
                                 audio_meta.get("method", "xor"))
                ops.report(rec, 85, "Restored audio track")

        out_dir = rec.dir / "out"
        _zip_dir(out_dir / f"{rec.id}.frames.zip", restored)
        if restored_audio is not None:
            shutil.copy2(restored_audio, out_dir / "audio_restored.wav")

        if options.encode:
            require()
            enc_stem = (options.encode or "restored").rstrip(".mkv")
            try:
                cm.ffmpeg_encode_frames(str(restored), float(fps),
                                        str(out_dir / enc_stem),
                                        str(restored_audio)
                                        if restored_audio else None)
                ops.report(rec, 97,
                           f"Encoded {enc_stem}.mkv ({method})")
            except Exception as exc:
                raise ApiError(code="UNSUPPORTED_FORMAT",
                               message="FFmpeg could not encode the result.",
                               details={"hint": type(exc).__name__}) from None
        ops.finish(rec)


def _has_frames(directory: Path) -> bool:
    try:
        cm.list_frames(str(directory))
        return True
    except ValueError:
        return False


def settings_has_audio(video: Path) -> bool:
    try:
        return cm.ffmpeg_has_audio(str(video))
    except Exception:
        return False


video_crypto = VideoCryptoService()