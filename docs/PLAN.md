# Crypto Couples — PWA Transformation Plan

Transform the pure-Python CLI project into a professional, installable
Progressive Web App while keeping the existing cryptographic engine as the
source of truth.

- **Frontend**: React + TypeScript + Vite + Tailwind + shadcn/ui + Lucide +
  TanStack Query + Zustand + React Hook Form + Zod + React Router + vite-plugin-pwa
- **Backend**: FastAPI + Pydantic + Uvicorn (API adapter only)
- **Crypto core**: `crypto_couples.py` + `crypto_media.py` (unchanged, single source of truth)
- **CLI**: preserved verbatim; same core, empty adapter layer overhead

---

## 1. Hard rules

- Never rewrite, duplicate, replace or silently modify the crypto algorithms.
- Never implement crypto in TypeScript/React.
- Backend services call core functions via direct import (no subprocess).
- CLI commands must keep working:
  - `python3 crypto_couples.py demo|split|reveal ...`
  - `python3 crypto_media.py split-audio|reveal-audio|split-video|reveal-video|split-bytes|reveal-bytes ...`
- No wildcard production CORS. No shell-string construction from user input.
- No sensitive data in logs, URLs, localStorage, or the service-worker cache.
- Backend validation is authoritative; frontend validation is UX only.

## 2. Architecture

```
                    ┌─────────────────────────────┐
                    │  Crypto Couples PWA (React) │
                    └──────────────┬──────────────┘
                                   │  REST / WebSocket
                    ┌──────────────▼──────────────┐
                    │        FastAPI layer        │
                    └──────────────┬──────────────┘
                    ┌──────────────▼──────────────┐
                    │     Service layer           │
                    │  image · audio · video file │
                    │  operation · validation     │
                    └──────────────┬──────────────┘
                    ┌──────────────▼──────────────┐
                    │   Crypto core (unchanged)   │
                    │  crypto_couples.py          │
                    │  crypto_media.py            │
                    └─────────────────────────────┘
```

### Key decisions

1. **Direct-import adapter** — backend inserts repo root on `sys.path` and
   `import crypto_couples, crypto_media`; services call pure functions.
2. **Video progress** — the video service loops frames calling core primitives
   only (`png_decode → binarize → split_stack/split_xor → png_encode`) and core
   FFmpeg bridges, so "Frame 421 / 742" progress is possible. Orchestration is
   re-implemented in the service; crypto math is never duplicated. Byte-parity
   tests compare service output against CLI output.
3. **Operations** — background `ThreadPoolExecutor` per op; thread-safe store;
   per-op subscriber queues bridged to the asyncio loop for WebSocket progress;
   polling endpoint as fallback.
4. **History** — SQLite, **metadata only** (never payload bytes), plus in-memory
   op snapshot store.
5. **Temp lifecycle** — `TEMP_DIRECTORY/ops/<op_id>/`; TTL janitor (default
   60 min); cleanup on completed/failed/cancelled.
6. **Downloads** — result files streamed via `FileResponse`; "Download All" is a
   server-computed zip (stdlib `zipfile`). No JSON/base64 for binaries.
7. **No `cli/` directory** — the root scripts already are the CLI; a wrapper dir
   would be redundant abstraction.

## 3. Repo layout (target)

```
Crypto_Couples/
├── crypto_couples.py          # crypto core + CLI (unchanged)
├── crypto_media.py            # crypto core + CLI (unchanged)
├── cli/                       # (intentionally NOT created — root scripts are the CLI)
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/{health,system,operations,images,audio,video,files}.py
│   │   ├── api/websocket.py
│   │   ├── services/{image,audio,video,file,operation,validation,ffmpeg}_service.py
│   │   ├── models/            # DB rows / op state
│   │   ├── schemas/           # Pydantic request/response + error envelope
│   │   ├── workers/           # executor + janitor
│   │   ├── storage/           # op store, sqlite history
│   │   ├── security/          # sanitize, traversal guard, headers, CORS
│   │   └── config/settings.py
│   ├── data/                  # gitignored; history.sqlite lives here
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/               # router, providers, app shell
│   │   ├── components/{ui,layout,navigation,files,media,crypto,progress,feedback}/
│   │   ├── pages/             # Home, Split, Reveal, *Crypto, History, Settings
│   │   ├── features/{image,audio,video,files,split,reveal}/
│   │   ├── services/          # typed API clients
│   │   ├── hooks/ stores/ schemas/ types/ lib/ utils/ styles/
│   ├── public/                # icons, manifest.webmanifest
│   ├── scripts/generate-icons.py
│   ├── vite.config.ts  tailwind.config.ts  tsconfig.json  package.json
├── tests/                     # existing core tests (unittest)
├── docs/PLAN.md
├── .env.example  (per backend/frontend)
├── pyproject.toml
└── README.md
```

## 4. API contract (summary)

| Method | Path                            | Purpose                                   |
|--------|---------------------------------|-------------------------------------------|
| GET    | `/api/health`                   | liveness + engine status                  |
| GET    | `/api/system/ffmpeg`            | ffmpeg availability probe                 |
| POST   | `/api/images/split`             | multipart PNG → shares                    |
| POST   | `/api/images/reveal`            | multipart PNGs → secret                   |
| POST   | `/api/audio/split`              | WAV → additive/xor/shamir shares          |
| POST   | `/api/audio/reveal`             | WAV shares → restored WAV                 |
| POST   | `/api/video/split`              | video/zip → frame-dir shares (+audio)     |
| POST   | `/api/video/reveal`             | share zips/dirs → restored frames/video   |
| POST   | `/api/files/split`              | any file → xor/shamir `.shard` shares     |
| POST   | `/api/files/reveal`             | `.shard` files → original file            |
| GET    | `/api/operations`               | list ops (metadata)                       |
| GET    | `/api/operations/{id}`          | op snapshot                               |
| POST   | `/api/operations/{id}/cancel`   | cancel a queued/processing op             |
| GET    | `/api/operations/{id}/files`    | result file names + sizes                 |
| GET    | `/api/operations/{id}/download` | stream one result file                    |
| GET    | `/api/operations/{id}/download-all` | server zip of all result files        |
| WS     | `/api/operations/{id}/ws`       | progress events (poll `/api/operations/{id}` as fallback) |
| GET    | `/api/history`                  | persisted metadata log                    |
| DELETE | `/api/history`                  | clear log                                 |

### Error envelope

```json
{ "error": { "code": "INVALID_SHARE", "message": "...", "details": {} } }
```

Known codes: `UPLOAD_TOO_LARGE`, `INVALID_FILE_TYPE`, `INVALID_IMAGE`,
`INVALID_SHARE`, `INVALID_METHOD`, `INVALID_PARAMETER`, `UNSUPPORTED_FORMAT`,
`FFMPEG_MISSING`, `SHAMIR_LIMIT`, `OPERATION_NOT_FOUND`, `OPERATION_BUSY`,
`INTERNAL`. Raw exceptions are never returned.

### Operation state machine

```
queued → uploading → processing → completed
                              ├→ failed
                              └→ cancelled → (expired → deleted)
```

WS messages: `{type:"progress",progress,message}`, `{type:"completed"}`, `{type:"error",message}`.

## 5. Environment variables

Backend: `APP_ENV` · `HOST` · `PORT` · `FRONTEND_ORIGIN` · `MAX_UPLOAD_SIZE`
(default 512 MB) · `TEMP_DIRECTORY` · `FFMPEG_PATH` · `OP_TTL_SECONDS` (60 min).
Frontend: `VITE_API_URL` · `VITE_WS_URL`.

## 6. Phases

- **P0** Plan artifacts + baseline (this file, requirements, .gitignore, 32 tests green, commit+push).
- **P1** Backend foundation: app factory, settings, security, schemas, health + ffmpeg routes.
- **P2** Operation system: store, SQLite metadata history, executor, janitor, op routes, WS.
- **P3** Validation service (authoritative).
- **P4** Image service + routes + tests.
- **P5** File (bytes) service + routes + tests.
- **P6** Audio service + routes + tests.
- **P7** Video service + routes (ffmpeg bridge, per-frame progress) + tests.
- **P8** Backend test complete (lifecycle, validation, error mapping, CLI parity).
- **P9** Frontend scaffold (Vite/React/TS/Tailwind/shadcn/router/query/zustand/rhf/zod, PWA plugin, manifest, icons).
- **P10** App shell + design direction gate (designer-skill `commit_design_direction` PASS), sidebar/bottom-nav, themes, offline banner, install prompt.
- **P11** Data layer: typed API clients, `useOperation` (WS+poll), Query/Zustand state, Zod schemas.
- **P12** Shared components: dropzone, stepper, ShareConfig, previews, ShareGrid, Progress, Empty/Error/Success, StatusBadge.
- **P13** Pages: Home, Split, Reveal, Image/Audio/Video/FileCrypto, History, Settings (lazy routes).
- **P14** Frontend tests: Vitest + RTL.
- **P15** Security & perf hardening: headers, download safety, cleanup, error audit, code-splitting.
- **P16** E2E (Playwright, best-effort in Termux) + PWA checks + desktop manual checklist.
- **P17** Docs + final gates: README rewrite, .env examples, deployment notes, full test run, `review_and_gate`, commit+push.

### Design direction (P10)

- Register: **product** (earned familiarity bar — Linear/Raycast/1Password-style trust).
- Dark-first tokens: bg `#080A0F` · surface `#10131A` · elevated `#161A23` · border
  `#242936` · primary `#6C63FF` · secondary `#22D3EE` · success `#22C55E` ·
  warning `#F59E0B` · danger `#EF4444` · text `#F8FAFC` · muted `#94A3B8`.
- Restraint: solid accent, minimal neon/glow/gradient; 150–250 ms transitions;
  `prefers-reduced-motion` respected. Inter + system-ui/mono stack, body ≥16 px,
  44 px touch targets, a11y contrast, status never communicated by color alone.
- `review_and_gate` must PASS (≥85, zero blocking slop) before declaring UI done.

## 7. Testing strategy

- Backend: pytest (existing 32 + new `backend/tests`) — algorithms via API,
  lifecycle, validation rejection, error codes, history, temp cleanup, CLI parity.
- Frontend: Vitest + React Testing Library (forms, zod, code→message mapping,
  op-hook states, components).
- E2E: Playwright flow upload→configure→generate→download→reveal→compare
  (best-effort here; manual desktop checklist documented).
- PWA: manifest validity, SW precache, offline shell, standalone, icons.

## 8. Acceptance checklist (final)

Image/audio/video/file split+reveal, Shamir thresholds, XOR, existing CLI all
work; PWA installable + offline shell; home/split/reveal/history/settings/UX
states; separated async architecture; validation both sides; file lifecycle
controlled; sanitized filenames, no traversal, temp cleaned, CORS configured,
no secret leakage, raw errors hidden; responsive at 360→1920; feels like an
installed app, not a website or dashboard.