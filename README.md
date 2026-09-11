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

## Development

```
python3 -m unittest discover -s tests        # stdlib tests, no deps
python3 -m pyflakes crypto_couples.py tests/ # lint (if pyflakes installed)
```