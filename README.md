# Crypto_Couples

Visual cryptography in pure Python — no third-party dependencies.

Split any PNG image into **n-of-n shares** that look like random noise. Print
the shares on transparencies and **stack** them (or XOR them on a computer)
and the secret image reappears. Any fewer than *n* shares reveals nothing.

## Quick start

```
# 1. Make a message image (black text on white)
python3 crypto_couples.py demo message.png --text 'SECRET' --scale 6

# 2. Split into 2-of-2 shares (printable stacking shares)
python3 crypto_couples.py split message.png --shares 2 --method stack --seed 42 --out share

# 3. Recombine: physically stack + photograph, or...
python3 crypto_couples.py reveal share.1.png share.2.png --method stack --out revealed.png
```

Three-of-three XOR shares (cleaner digital recovery, no print/scaling needed):

```
python3 crypto_couples.py split message.png --shares 3 --method xor --seed 7 --out share
python3 crypto_couples.py reveal share.1.png share.2.png share.3.png --method xor --out msg.png
```

## Methods

| Method  | Shares look like | Reveal by                       | Good for                          |
|---------|------------------|---------------------------------|-----------------------------------|
| `stack` | noise (1/n dark) | printing & overlaying (OR)      | paper transparencies              |
| `xor`   | 50% black noise  | XORing the shares on any device | digital recovery, exact results   |

- `stack` is the classic Naor–Shamir (n,n) scheme: each original pixel becomes
  *n* subpixels per share. A white pixel puts one black subpixel in the same
  column of every share; a black pixel blackens one column per share. Any
  single share still looks like uniform noise.
- `xor` hides the message in a half of the bits chosen at random; the final
  share is the running XOR so that combining all shares is exact and lossless.

## Commands

- `demo` — render UPPERCASE text/`0-9`/`!?.,:-/#` onto a white PNG.
- `split` — `--shares N` (default 2), `--method stack|xor`, `--seed`,
  `--threshold 128`, `--dither` (Floyd–Steinberg for grayscale/color input).
- `reveal` — pass 2+ share PNGs; same `--method` as the split.
- Shares are written as `<out>.1.png`, `<out>.2.png`, …

## Input images

Any PNG that isn't interlaced: grayscale, RGB, palette, RGBA, bit depths
1/2/4/8 (16-bit is truncated). Reads and writes are handled by a small
bundled PNG codec (`zlib` + `struct` only).

## Security notes

- This is a **cryptographic toy** — it protects against casual sharing, not
  a determined adversary with all-but-one shares against a weak source image
  (secret-sharing schemes do not amplify an image's entropy).
- Anyone with all *n* shares can reconstruct the image; keep shares apart.
- Uses Python's `random` (Mersenne Twister), which is **not** cryptographically
  secure — do not use real secrets with this tool.

## Developing

```
python3 -m unittest discover -s tests        # stdlib tests, no deps
python3 -m pyflakes crypto_couples.py tests/ # lint (if pyflakes installed)
```

---

# Audio, video & bytes (`crypto_media.py`)

The same idea applied to sound, moving images and arbitrary files. Still pure
stdlib; only the *optional* `split-video`/`reveal-video --encode` paths shell
out to `ffmpeg`/`ffprobe`.

## Audio — superposition makes it physical

Sound adds in the air. So instead of stacking transparencies you **play every
share at the same time**: noise cancels, the message appears.

| Method       | Shares sound like | Any k of n | Recover by                 |
|--------------|-------------------|------------|----------------------------|
| `additive`   | hiss/static       | n          | adding waveforms (the air or software) |
| `xor`        | white noise       | n          | XORing sample words (exact) |
| `shamir`     | white noise       | k          | Lagrange interpolation, exact |

```
python3 crypto_media.py split-audio voice.wav --out a --method additive --shares 3 --seed 1
python3 crypto_media.py reveal-audio a.1.wav a.2.wav a.3.wav --out voice.wav --method additive

python3 crypto_media.py split-audio voice.wav --method shamir --shares 3 --threshold 2 --out a
python3 crypto_media.py reveal-audio a.1.wav a.3.wav --out voice.wav --method shamir
```

- `additive`: share i is random hiss, the last share is `message − (hiss₁ + …)`.
  Digital reveal is exact to ±1 LSB (16-bit PCM); physical playback works best
  from synchronized sources at equal loudness. If the message already peaks
  near full scale there is no headroom for the hiss — normalize first.
- `xor` / `shamir` split the PCM sample payload (the WAV header is kept
  metadata, so every share is a playable WAV) and reconstruct
  byte-for-byte in software.
- Input: 8-bit or 16-bit uncompressed PCM WAV. For mp3/ogg/m4a first convert
  with ffmpeg (`ffmpeg -i song.mp3 out.wav`).

## Video — living static

Each frame is split with the image tool using **fresh randomness per frame**,
so every share is a video of scrambling static. Bring all n shares together
(same timing) and the original footage reappears; the audio track travels
through the audio tool as a parallel set of shares.

```
# share clips: n directories of frame PNGs + optional audio shares + manifest
python3 crypto_media.py split-video clip.mp4 --outdir shares --shares 2 --method stack \
        --audio-method additive --audio-shares 2 --seed 7

# recombine (reads manifest.json: method, fps, audio scheme)
python3 crypto_media.py reveal-video shares/1 shares/2 --outdir restored --encode final
# -> restored/video/frame_NNNN.png + restored/audio_restored.wav + final.mkv
```

- Input is any ffmpeg-readable file, or a directory of `frame_NNNN.png`.
- `--encode NAME` bakes the restored frames (+ restored audio) into a lossless
  `NAME.mkv` (ffv1 → libx264 `-qp 0` → png, whichever ffmpeg has).
- The visual scheme is n-of-n (classic visual crypto); audio in a video bundle
  may use additive/xor/shamir independently.
- NOTE: like all video codecs, one stream has one resolution — a source with
  frames of varying widths is not representable; keep frame sizes constant.

## Bytes — any file, k-of-n

`split-bytes`/`reveal-bytes` secret-share any file. XOR = n-of-n; `shamir` =
any k of n (polynomial shares over GF(2⁸)). Each share is written to
`<out>.<k>.shard`.

```
python3 crypto_media.py split-bytes backup.zip --method shamir --shares 4 --threshold 3 --out b
python3 crypto_media.py reveal-bytes b.1.shard b.3.shard b.4.shard --out backup.zip --method shamir
```

## Security notes

Same honest caveats as the image tool: `random` (Mersenne Twister) is **not**
crypto-secure, so treat this as a demonstration, not for real secrets. The
Shamir arithmetic in GF(2⁸) is exactly the textbook construction, but a
determined adversary should use `secrets`-backed randomness and a vetted
library instead.