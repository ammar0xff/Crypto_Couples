"""Audio crypto adapter. Calls crypto_media primitives only."""

from __future__ import annotations

import random

from ..core_loader import cm
from ..deps import ops
from ..schemas.crypto import AudioRevealOptions, AudioSplitOptions
from ..security.errors import ApiError


def _check_cancel(rec) -> None:
    if rec.cancel_event.is_set():
        raise ApiError(code="CANCELLED", message="Operation cancelled.")


class AudioCryptoService:
    def split(self, rec, options: AudioSplitOptions) -> None:
        if len(rec.input_names) != 1:
            raise ApiError(code="INVALID_PARAMETER",
                           message="Audio split requires exactly one WAV file.")
        in_path = rec.dir / "input" / rec.input_names[0]

        try:
            paren = cm.wav_params(str(in_path))
        except Exception as exc:
            raise ApiError(code="UNSUPPORTED_FORMAT",
                           message="Only uncompressed PCM WAV is supported.",
                           details={"hint": type(exc).__name__}) from None
        _, sampwidth, _ = paren
        if sampwidth not in (1, 2):
            raise ApiError(code="UNSUPPORTED_FORMAT",
                           message="WAV must be 8-bit or 16-bit PCM.")

        data = cm.wav_read_data(str(in_path))
        rng = random.Random(options.seed)
        stem = Path(rec.input_names[0]).stem
        out_dir = rec.dir / "out"

        if options.method == "additive":
            samples, paren = cm.wav_read_floats(str(in_path))
            shares = cm.additive_split_audio(samples, options.shares, rng)
            for i, share in enumerate(shares, 1):
                _check_cancel(rec)
                cm.wav_write(str(out_dir / f"{stem}.wav.{i}.wav"), paren,
                             cm.floats_to_int16(share))
                ops.report(rec, int(90 * i / options.shares),
                           f"Writing additive share {i} of {options.shares}")
        else:
            chunks = (cm.xor_split(data, options.shares, rng)
                      if options.method == "xor" else
                      cm.shamir_split(data, options.shares,
                                      options.threshold or options.shares, rng))
            for i, chunk in enumerate(chunks, 1):
                _check_cancel(rec)
                name = f"{stem}.wav.{i}.wav"
                cm.wav_write(str(out_dir / name), paren,
                             chunk if isinstance(chunk, bytes) else chunk[1])
                ops.report(rec, int(90 * i / options.shares),
                           f"Writing {'XOR' if options.method == 'xor' else 'Shamir'} "
                           f"share {i} of {options.shares}")
        ops.finish(rec)

    def reveal(self, rec, options: AudioRevealOptions) -> None:
        paths = sorted(str(rec.dir / "input" / n) for n in rec.input_names)
        if len(paths) < 2:
            raise ApiError(code="INVALID_SHARE",
                           message="At least 2 audio shares are required.")
        try:
            paren = cm.wav_params(paths[0])
        except Exception as exc:
            raise ApiError(code="UNSUPPORTED_FORMAT",
                           message="Only uncompressed PCM WAV is supported.",
                           details={"hint": type(exc).__name__}) from None
        for p in paths[1:]:
            _check_cancel(rec)
            try:
                if cm.wav_params(p) != paren:
                    raise ApiError(code="INVALID_SHARE",
                                   message="All shares must have identical WAV "
                                           "format.")
            except ApiError:
                raise
            except Exception:
                raise ApiError(code="INVALID_SHARE",
                               message="Unable to read audio share.") from None

        out = rec.dir / "out" / f"{rec.id}.restored.wav"
        if options.method == "additive":
            chans = [cm.wav_read_floats(p)[0] for p in paths]
            cm.wav_write(str(out), paren,
                         cm.floats_to_int16(cm.additive_reveal_audio(chans)))
        elif options.method == "xor":
            chunks = [cm.wav_read_data(p) for p in paths]
            cm.wav_write(str(out), paren, cm.xor_reveal(chunks))
        else:
            points = [(cm._share_index(p), cm.wav_read_data(p)) for p in paths]
            if len({x for x, _ in points}) != len(points):
                raise ApiError(code="INVALID_SHARE",
                               message="Duplicate share index in reconstruction.")
            cm.wav_write(str(out), paren, cm.shamir_reveal(points))
        ops.report(rec, 90, f"Restored audio from {len(paths)} shares")
        ops.finish(rec)


audio_crypto = AudioCryptoService()