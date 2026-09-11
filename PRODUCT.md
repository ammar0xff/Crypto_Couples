# Product

## Register

product

## Users

Privacy-focused individuals — hobbyists, researchers, journalists-adjacent,
and terminal-curious makers — who want visual cryptography (stack/XOR shares)
and Shamir secret sharing over GF(2^8) for images, audio, video and arbitrary
files, without a heavyweight service or a server that ever sees their secrets.
They use this inside a browser and on mobile, on their own terms.

## Product Purpose

Turn the demonstrated crypto core (`crypto_couples.py` / `crypto_media.py`)
into a professional, installable PWA: split a secret into shares, or restore a
secret from shares, with honest progress feedback, offline-capable shell, and a
metadata-only history. Success = the driving loops (split → reveal) feel as
trustworthy and intact as the CLI they came from.

## Brand Personality

Focused, honest, curious. The persona of a careful lab notebook: "here is
exactly what the engine does, and here is its honest limit." Playful where the
original CLI is playful (share density stats, "keep the shares secret from each
other"), never cyber-noir bravado. This is a demo-grade crypto tool and the
product is transparent about that.

## Anti-references

Generic AI-slop SaaS dashboards (purple gradients, mesh blobs, three equal
cards). Fintech crypto neon (every blockchain meme). Produce-a-secret
"encryption" marketing sites that overclaim. Anything that implies stronger
guarantees than the engine actually has. Noise: dark themes that glow all over;
a cliché hacker terminal pastiche. The tool's own honest plainness is the
aesthetic — not a costume of one.

## Design Principles

- **Practice what you preach** — the app's own visuals show shares, pixels,
  and revealed density instead of stock metaphors; the split reveals the
  mechanics.
- **Show, don't tell** — progress is a real feed of what the engine is doing
  (frames processed, shares written), not an indeterminate spinner.
- **Honest about limits** — surfaced demos, absent ffmpeg, Mersenne-Twister
  caveat: state limitations plainly where they matter.
- **Respect the secret** — no server storage of contents, metadata-only
  history, aggressive temp TTL: privacy is behavior, not a badge.
- **Expert confidence, humble tone** — precise controls and honest defaults
  beat persuasion copy.

## Accessibility & Inclusion

Target WCAG 2.1 AA. Respect `prefers-reduced-motion`. Stack/XOR reveal results
must be readable without color (share overlays are luminance patterns, so
avoid color-only encoding). 44px touch targets, visible focus rings, 4.5:1 text
contrast on the dark surfaces. All states (loading, error, empty, success)
carry the same semantic color treatment everywhere.