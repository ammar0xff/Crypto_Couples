# Design

Dark, focused, tool-first. Two neutral layers carry structure; a single restrained accent means action only. The app's own pixel-grid output is the recurring motif.

## Key principles

1. **The tool disappears into the task.** Familiar product affordances: top bar + side nav, tabs for Split/Reveal, standard form controls. No page theater.
2. **Accent = action.** Primary actions, current selection, state dots. Nothing decorative.
3. **Honest surface.** Hairline borders and two quiet neutrals tell structure; no glow, no gradient text.
4. **One motif:** luminance pixel grids (the crypto output itself) as contextual decoration, never as fake screenshots.
5. **Consistent state vocabulary.** Loading/error/warning/success/empty get one treatment per state, everywhere.

## Color

| Token | Value |
|-------|-------|
| `bg` | `#080A0F` — near-black canvas (never pure #000) |
| `surface` | `#10141C` — first content layer |
| `surface-2` | `#161B25` — second neutral layer (toolbars, side panels) |
| `border` | `#222B39` — hairlines (low-contrast, structure only) |
| `text` | `#E6E9EF` — primary ink |
| `text-muted` | `#9AA5B5` — secondary ink |
| `text-faint` | `#6B7686` — tertiary/meta ink |
| `primary` | `#6C63FF` — action only: primary buttons, active nav, progress, links |
| `success` | `#34D399` |
| `warning` | `#FBBF24` |
| `danger` | `#F87171` |
| `info` | `#38BDF8` |

Saturation below 80% for all status colors. No hue-260–310 gradients; `primary` is flat, no glow.
Dark surface never dips below `#080A0F`; text never hits pure white.

## Typography

| Role | Family | Notes |
|------|--------|-------|
| UI (body, buttons, labels, headings) | System sans stack (`-apple-system`, `Segoe UI`, `Inter`, `sans-serif`) | Product register: honest system UI is legitimate |
| Data / meta (share ids, hashes, stats, frame counts) | `JetBrains Mono`, `SF Mono`, `Menlo`, `monospace` | Numbers and ids in mono at `0.8125rem` |

Scale (≥1.25 ratio): `text-xs 12` → `text-sm 14` → `text-base 16` → `text-lg 20` → `text-2xl 24` → `text-4xl 36`. Body ≥16px, line-height 1.6. Headings tracking `-0.02em`.
No display fonts in UI labels, buttons, or data.

## Spacing & radius

- Scale: 4-based grid (4, 8, 12, 16, 24, 32).
- Cards/surfaces: `rounded-lg` (8px) max; buttons `rounded-md` (6px); pills only at tag scale.
- Focus rings: 2px `ring-offset` using `#6C63FF` at focus-visible only.
- Ambient shadows are banned (dark hairline surfaces do the elevation work).

## Components

- **Button**: `primary` (accent fill), `secondary` (surface-2 + border), `ghost` (borderless, text-muted hover → text), `danger`. 44px min touch target. `active:scale-[0.98]`.
- **Card / surface**: `card-surface` (surface bg + hairline border + rounded-lg + p-5).
- **Tabs**: underline style (accent underline on active), for Split vs Reveal.
- **Progress**: thin bar, `primary` fill, mono percent readout; step feed below.
- **Status pill**: subtle dot + text, state color only on the dot + hint text.
- **Dropzone**: dashed hairline border → solid accent on drag; keyboard accessible.
- **Skeleton**: muted shimmer only for placeholders (no circular spinners from P15 onward; runtime/progress is real data, not a spinner).

## Motion

- Default `transition` 150–200ms ease-out on `transform`/`opacity` only.
- Scroll/state entries: fade + `translateY(8px)` → 0 over 300ms.
- Progress steps appear with a small fade; no persistent looping motion (privacy-focused tool — no perpetual micro-loops).
- `prefers-reduced-motion: reduce` → zero animation; states change instantly.
- Deterministic, quiet. Nothing bounces; nothing glows.

## Layout

- App shell: fixed top bar (brand wordmark in mono + nav) + content column, `max-w-7xl`, px-4/8/16 responsive. Side nav only where density earns it (operations pool); everything else is a single work column.
- Split view: two-pane wizard (form left, live "recipe" summary right) stacking on mobile.
- Reveal view: sequential steps (uploads → verify → result) with sticky step progress.
- Result view: revealed preview (pixel canvas) + download payload; share cards show id, sha256, size, checksum in mono.

## Imagery & iconography

- Lucide icons at `strokeWidth=1.75`, `size=18` UI / `20` nav, never decorative.
- Motif: the app renders its own share previews (tiled luminance grids from `to_rows`/share PNGs) — the only "imagery" in the product. No stock, no gradients.