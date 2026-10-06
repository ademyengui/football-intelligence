# Football Intelligence Dashboard: Build Instructions (v1.0)

> **For the coding agent.** Read this entire file before writing anything. Execute the phases in Section 14 in order. Each phase has acceptance criteria; verify them yourself (run the app, hit the endpoints, use the browser) before moving on. Do not skip ahead, and do not add features that are not listed here.
>
> **Placement:** this file lives at the repo root as `BUILD_INSTRUCTIONS.md`. Do **not** put it in `.agents/rules/` (rule files are size-limited and would be truncated). In Phase 1, copy **Section 2 (Working rules)** into a short `AGENTS.md` at the repo root so the rules persist across sessions.

---

## 1. Goal and scope

Build the **application layer** (frontend + backend + worker) of a post-match football analytics platform. A user uploads a broadcast match clip, a background worker processes it, and an Angular dashboard shows team/player heatmaps, per-track stats, and a possession timeline.

The ML research track is paused, so the app is built around a **pluggable pipeline**: a mock pipeline (no GPU, instant to develop against) and a real pipeline (YOLO detection + ByteTrack, with *faked* calibration and a simple colour-based team classifier). Real homography and embedding-based team classification come later and must be drop-in replacements.

### In scope (v1.0)
- Video upload (streamed to disk), matches list, per-match dashboard
- Background processing via RQ, live progress via WebSocket
- Heatmaps (team-level and per-track), stats table, possession timeline
- CSV export, delete match, failed-job handling with Retry
- Mock pipeline, real pipeline, results import command, seed command
- Native local dev setup (no Docker)

### Out of scope (do NOT build)
- Authentication / multi-user
- Docker, docker-compose, deployment, CI/CD
- Real pitch homography, SigLIP team classification
- PDF/PNG export, per-track trajectory endpoint, video playback, formation/pressing/passing features, live streaming
- Manual per-track role override in the UI (schema must make it easy to add later)

---

## 2. Working rules (copy into `AGENTS.md` in Phase 1)

1. Follow `BUILD_INSTRUCTIONS.md` phase by phase. Verify acceptance criteria before moving on. Make one local git commit per phase.
2. Never run `sudo` yourself. When a step needs it, write the exact commands and ask the human to run them, then continue.
3. Never invent secrets. The Roboflow API key is supplied by the human in `.env`. Never commit `.env`, videos, model weights, `node_modules`, `venv`, or `data/`.
4. Do not assume a GPU. Detect the device at runtime (CUDA if available, else CPU) and log which one was used. The machine has an NVIDIA MX350 (2 GB VRAM) and CUDA may not work; do not spend time on CUDA setup beyond a quick check.
5. Python: venv + pip + `requirements*.txt` only (no Poetry, no conda). Postgres and Redis run natively on Ubuntu 24 (no Docker).
6. Everything the dashboard shows must come from the results schema in Section 7. Keep the pipeline behind the interface in Section 8.
7. If blocked after two honest attempts, stop and report what you tried; do not hack around it or silently change scope.
8. At the end of each phase, report: what was built, how you verified it, anything deferred, and any decision the human must make.

---

## 3. Environment and constraints

| Item | Value |
|---|---|
| Machine | HP laptop, Ubuntu 24 |
| GPU | NVIDIA GeForce MX350 (2 GB) + Intel TigerLake-LP GT2; CUDA status unknown |
| Present | Docker (unused here), Python |
| Missing | Node.js (install via nvm, LTS compatible with the latest stable Angular CLI) |
| Postgres / Redis | Install natively with apt (human runs sudo) |
| Repo | Monorepo, brand new. `git init` locally; the human will create the remote later |
| Python deps | venv + pip + requirements files |

Network is available for pip/npm and for the first download of the Roboflow model weights.

---

## 4. Repository layout

```
football-intelligence-dashboard/
├── BUILD_INSTRUCTIONS.md
├── AGENTS.md                 # created in Phase 1 from Section 2
├── README.md                 # written in Phase 7
├── SETUP.md                  # native install steps (Phase 1)
├── Makefile
├── Procfile.dev              # used by honcho: api, worker, web
├── .env.example
├── .gitignore
├── backend/
│   ├── requirements.txt          # core (mock mode works with this alone)
│   ├── requirements-real.txt     # real pipeline deps (inference, supervision, ...)
│   ├── requirements-dev.txt      # pytest, honcho, httpx, ruff
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, GZip, routers, startup tasks
│   │   ├── config.py             # pydantic-settings
│   │   ├── db.py                 # engine, session
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic API + results schemas
│   │   ├── api/                  # routers: health, matches, export, ws
│   │   ├── services/             # storage (upload streaming), progress, reaper
│   │   ├── worker/
│   │   │   └── tasks.py          # RQ job: process_match
│   │   ├── pipeline/
│   │   │   ├── base.py           # interfaces + PipelineContext
│   │   │   ├── mock.py
│   │   │   ├── real.py           # orchestrates the real pipeline
│   │   │   ├── detector.py       # Roboflow `inference` wrapper
│   │   │   ├── calibrator.py     # NaiveCalibrator
│   │   │   ├── teams.py          # colour-based team/role classifier
│   │   │   ├── possession.py
│   │   │   └── aggregate.py      # distance, heatmaps, trajectories
│   │   └── cli.py                # seed, import-results, export-schema
│   └── tests/
├── frontend/                     # Angular app
├── data/                         # gitignored: uploads/, imports/
└── docs/
    └── results.schema.json       # generated by `make schema`
```

---

## 5. Stack

**Backend:** Python 3.10+ (use the system Python 3.12 if present), FastAPI, uvicorn, SQLAlchemy 2.0, Alembic, `psycopg` (v3), `redis`, `rq`, pydantic v2 + pydantic-settings, numpy, opencv-python-headless, scikit-learn.
**Real mode only** (`requirements-real.txt`): `inference` (Roboflow), `supervision`. Install these in Phase 6, not earlier. If pip resolution conflicts appear, report them to the human instead of pinning around them for hours.
**Frontend:** latest stable Angular (standalone components, signals, new control flow), TypeScript strict, Tailwind CSS (use the setup the current Angular docs recommend), Plotly via `plotly.js-dist-min` with a thin wrapper component (do not use third-party Angular-Plotly wrappers).
**Infra:** native PostgreSQL, native Redis, RQ worker, honcho to run all processes in dev.

---

## 6. Configuration (`.env` / `.env.example`)

```
DATABASE_URL=postgresql+psycopg://football:football@localhost:5432/football
REDIS_URL=redis://localhost:6379/0
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_BYTES=2147483648          # 2 GB
ALLOWED_EXTENSIONS=.mp4,.mkv
CORS_ORIGINS=http://localhost:4200
PIPELINE_MODE=mock                   # mock | real
STALE_JOB_SECONDS=300
JOB_TIMEOUT_SECONDS=7200

# Mock
MOCK_DURATION_SECONDS=120
MOCK_RUN_SECONDS=20

# Real
ROBOFLOW_API_KEY=
ROBOFLOW_MODEL_ID=football-players-detection-3zvbc/11
DETECTION_CONFIDENCE=0.3
FRAME_STRIDE=5
MAX_CLIP_SECONDS=120
MAX_FRAME_WIDTH=1280
MIN_TRACK_SECONDS_STORE=1.0
```

`GET /api/v1/health` returns the active `pipeline_mode` so the UI can show a mode badge.

---

## 7. Data model and results schema

### 7.1 Database

**`matches`**: `id` (UUID, pk), `original_filename`, `video_path` (nullable: imported matches have no video), `status` (`uploaded|queued|processing|completed|failed`), `progress` (int 0–100), `progress_message`, `error_message`, `pipeline_mode` (`mock|real|imported`), `video_fps`, `video_width`, `video_height`, `video_duration_s`, `created_at`, `updated_at`, `completed_at`.

**`match_results`**: `match_id` (FK, unique, cascade delete), `schema_version` (int), `calibration` (string), `summary` (JSONB), `tracks` (JSONB), `heatmaps` (JSONB), `possession` (JSONB), `trajectories` (BYTEA, gzip-compressed JSON). **Postgres is the source of truth** for state and results; Redis is used only for the RQ queue and progress pub/sub. Trajectories are never stored one row per frame.

Use Alembic for all schema changes. `updated_at` must change whenever progress changes (the stale-job reaper depends on it).

### 7.2 Results JSON (this is the contract; the dashboard, the importer, and any external notebook all use it)

Coordinates are **pitch metres**: origin top-left of the pitch, `x` 0 to 105 (left to right), `y` 0 to 68 (top to bottom). Times are seconds from the start of the processed clip.

```json
{
  "schema_version": 1,
  "meta": {
    "pipeline_mode": "mock | real | imported",
    "calibration": "naive",
    "duration_s": 120.0,
    "sample_fps": 5.0,
    "frame_size": [1280, 720]
  },
  "tracks": [
    {
      "track_id": 12,
      "team": "A | B | null",
      "role": "outfield | other",
      "detector_hint": "player | goalkeeper | referee | unknown",
      "first_t": 3.2,
      "last_t": 118.4,
      "duration_s": 115.2,
      "n_samples": 576,
      "distance_m": 842.5,
      "avg_pos_m": [48.2, 31.7]
    }
  ],
  "heatmaps": {
    "grid": {"width": 105, "height": 68, "bin_m": 1},
    "teams":  {"A": [[0.0, "... 105 values per row, 68 rows"]], "B": [[0.0]]},
    "tracks": {"12": [[0.0]]}
  },
  "possession": {
    "intervals": [{"start_s": 0.0, "end_s": 3.2, "state": "A | B | unknown"}],
    "summary": {"A_pct": 54.1, "B_pct": 45.9, "unknown_pct": 18.0}
  },
  "trajectories": {"12": [[0.2, 48.1, 30.9]]}
}
```

Rules:
- Heatmaps are indexed `[y][x]`, Gaussian-smoothed, **normalised so the max value is 1**, rounded to 3 decimals. Store per-track heatmaps only for tracks with `duration_s >= 3`.
- `A_pct` / `B_pct` are computed **excluding** unknown time (so they sum to 100); `unknown_pct` is the share of total time that was unknown.
- `trajectories` are `[t, x, y]` triples. They are stored compressed and are **not** returned by `GET /results` (no trajectory endpoint in v1.0).
- `team` is `null` and `role` is `"other"` for referee/goalkeeper-like tracks (see Section 9.3).
- `calibration` is `"naive"` for every v1.0 pipeline. Any future calibrated pipeline will use a different value.

Define the matching Pydantic models in `schemas.py` and make `python -m app.cli export-schema` write the JSON Schema to `docs/results.schema.json` (`make schema`). The human will use that file to produce importable results from a Kaggle notebook.

---

## 8. Pipeline architecture (pluggable)

```python
# pipeline/base.py
class PipelineContext:
    def report(self, pct: int, message: str = "") -> None: ...   # throttled; see 10.3

def run_pipeline(video_path: str, match_id: str, ctx: PipelineContext) -> MatchResults: ...
```

`worker/tasks.py::process_match(match_id)` loads the match, picks `mock.run` or `real.run` by `PIPELINE_MODE`, runs it, persists results, and sets status. Nothing outside `pipeline/` may know which mode ran. Internal swappable components for the real pipeline:

- `Detector`: frame → detections (xyxy, confidence, class)
- `Calibrator`: pixel point + frame size → pitch metres (**`NaiveCalibrator`** now; real homography later)
- `TeamClassifier`: tracks + crops → team/role per track (colour-based now; SigLIP later)
- `PossessionEngine`, `Aggregator`

### 8.1 Mock pipeline
- Deterministic: seed a RNG from the match id.
- Generate about 24 tracks: 10 outfield per team (Team A, Team B), 2 goalkeeper-like and 1 to 2 referee-like tracks (`role: "other"`), plus a few short tracks (1–6 s). Trajectories are random walks around formation anchor points on the 105×68 pitch, sampled at 5 Hz for `MOCK_DURATION_SECONDS`.
- Compute distance, heatmaps and possession from these trajectories using the **same aggregate/possession output builders** as the real pipeline, so the output is schema-identical.
- Possession intervals come from a simple Markov chain (A / B / unknown) with realistic run lengths.
- Take about `MOCK_RUN_SECONDS` to run with smooth progress ticks (sleep between steps), so the UI's live progress can be tested.
- Does not need the video content, but the video must have been uploaded (flow realism).

---

## 9. Real pipeline specification

### 9.1 Decode and detection
- Read with OpenCV, process every `FRAME_STRIDE`-th frame (default 5 → about 5 fps from 25 fps), stop at `MAX_CLIP_SECONDS` of source video (default 120 s).
- Downscale frames to `MAX_FRAME_WIDTH` (default 1280) preserving aspect ratio. All pixel geometry (foot points, ball distance) is in this processed frame size.
- Model: Roboflow `inference` package, `get_model(model_id=ROBOFLOW_MODEL_ID, api_key=ROBOFLOW_API_KEY)`, inference at `DETECTION_CONFIDENCE`. Classes: ball=0, goalkeeper=1, player=2, referee=3 (convert with `supervision` from the inference result).
- The detector sometimes labels referees and goalkeepers as `player`. **Never rely on the class label to decide team or role**; use it only as a vote (`detector_hint`) per Section 9.3.
- Log the compute device. Models load **inside** the job function, not at import time.

### 9.2 Tracking
- `supervision.ByteTrack` on non-ball detections (player, goalkeeper, referee).
- Because frames are strided, set the tracker's `frame_rate` to the effective sample fps and size its lost-track buffer in seconds (about 2 s of buffer). Check the installed `supervision` version's constructor arguments rather than assuming names.
- Ball: use the highest-confidence ball detection per processed frame (no ball tracking in v1.0). Ball position = centre of its box.
- Per processed frame, keep an in-memory observation list: `(t, track_id, foot_px, box_height_px, detector_class)` plus the ball position or `None`. Keep a small number of upper-body crops per track for team classification (see 9.3).
- Drop tracks shorter than `MIN_TRACK_SECONDS_STORE` from the stored results.

### 9.3 Team and role classification (track level)
Colour-based placeholder, behind the `TeamClassifier` interface:
1. For each track, collect up to 15 crops spread across its lifetime. Crop the **upper body**: from 15% to 55% of box height, central 60% of box width. Mask out grass pixels (HSV hue about 35–85 with saturation > 60) and compute the median **Lab** colour of the remaining pixels. The track's colour vector is the median of its crop colours.
2. Eligible-for-fit tracks: duration ≥ 5 s **and** detector class `player` in more than 80% of its frames.
3. Fit `KMeans(k=2)` on the eligible tracks' colour vectors. Team **A** is the cluster with more tracks.
4. Assign **every** track to its nearest centroid. If its distance to **both** centroids exceeds `2.5 ×` the median within-cluster distance, label it `role: "other"`, `team: null`.
5. Tracks whose detector class is mostly `goalkeeper` or `referee` (majority of frames) are `role: "other"` without clustering. Set `detector_hint` to that majority class (otherwise `unknown`).
6. `role: "other"` tracks are excluded from team heatmaps, team stats and possession candidates. Known v1.0 limitation: goalkeepers cannot contribute to possession. Document it in the README.

### 9.4 Calibration (naive)
`NaiveCalibrator`: `x_m = foot_x / frame_w * 105`, `y_m = foot_y / frame_h * 68`, clipped to the pitch. Foot point = **midpoint of the bottom edge of the bounding box**: `((x1 + x2) / 2, y2)`.
This is wrong whenever the camera pans or zooms; that is expected and must be surfaced to the user (see 11.4).

### 9.5 Aggregation
- **Distance:** sum of step lengths between consecutive samples of a track, in metres. Ignore any step implying more than 12 m/s (`dt` accounts for stride), since the naive mapping produces jumps when the camera moves.
- **Average position:** mean of the track's pitch positions.
- **Heatmaps:** 105×68 grid with 1 m bins, Gaussian blur (about 3 m sigma), normalised to max 1. Team heatmaps aggregate all `outfield` tracks of that team (so ID fragmentation does not matter).
- **Trajectories:** `[t, x, y]` per track, compressed.

### 9.6 Possession
Per processed frame:
1. Ball position `b`: the detection in that frame, otherwise the last known ball position carried forward for at most **1.0 s**, otherwise no ball → state `unknown`.
2. Candidates = tracks present in that frame with `role == "outfield"`. For each, compute the Euclidean distance **in pixel space, within the same frame**, from `b` to the player's **foot point** (midpoint of the bottom edge of the box). Do **not** use the whole-box centre.
3. Nearest candidate wins. If its distance exceeds **1.5 × that player's box height**, the frame is `unknown` (loose or airborne ball). Otherwise the state is that player's team.
4. Run-length encode per-frame states into intervals. Absorb any interval shorter than **1.0 s** into the longer of its two neighbours (or its only neighbour at the edges). Repeat until no short intervals remain.
5. Summary percentages follow the rule in Section 7.2.

Possession needs team labels, which exist only after the full pass; therefore store per-frame observations in memory, classify teams at the end, then compute possession.

### 9.7 Progress mapping
Decode/detect/track: 0–85%. Team classification: 85–92%. Aggregation and possession: 92–99%. Persist: 100%.

### 9.8 Reality check for real mode
On this laptop real mode will be slow (the earlier Kaggle test with the same model was very slow). The caps in `.env` exist for that reason. Do not try to optimise further in v1.0; instead make sure progress reporting is smooth and failures are clean. Real-mode failures (model download, out of memory, unreadable video) must end in `failed` with a short human-readable `error_message`.

---

## 10. Backend API

REST under `/api/v1`, OpenAPI at `/docs`. CORS from `CORS_ORIGINS`. Enable `GZipMiddleware` (results responses are large).

| Method + path | Behaviour |
|---|---|
| `GET /health` | `{status, pipeline_mode}` |
| `POST /matches` | Multipart upload. **Stream to disk in 1 MB chunks** (never `await file.read()` the whole file). Enforce `MAX_UPLOAD_BYTES` (413, delete the partial file) and extension allow-list (400). After saving, probe with OpenCV for fps/size/duration; if unreadable → 400 and delete the file. Creates a match with `status=uploaded`. |
| `GET /matches` | List, newest first |
| `GET /matches/{id}` | Match detail (status, progress, message, error, metadata) |
| `POST /matches/{id}/process` | Allowed from `uploaded` or `failed` only (else 409). Sets `queued`, clears `error_message`, enqueues the RQ job with `job_timeout=JOB_TIMEOUT_SECONDS` (**RQ's default timeout would kill real-mode jobs**). |
| `GET /matches/{id}/results` | 409 unless `completed`. Returns tracks, heatmaps, possession, meta, calibration; **no trajectories**. |
| `GET /matches/{id}/export.csv?kind=tracks\|possession` | CSV download. `tracks`: `track_id,team,role,detector_hint,duration_s,distance_m,avg_x_m,avg_y_m,calibration`. `possession`: `start_s,end_s,state`. |
| `DELETE /matches/{id}` | Deletes DB rows and the video file (idempotent on the file). Refuse (409) while `processing`. |
| `WS /ws/matches/{id}` | On connect sends the current `{status, progress, message, error}`; then relays updates from Redis pub/sub channel `match:{id}:progress`; closes after a terminal state. |

### 10.1 Status machine
`uploaded → queued → processing → completed | failed`. `failed → queued` via process (Retry). No cancel in v1.0.

### 10.2 Stale-job reaper
On API startup and every 60 s (background task): any `processing` match whose `updated_at` is older than `STALE_JOB_SECONDS` becomes `failed` with `error_message="Worker stopped responding"`, and a terminal progress message is published.

### 10.3 Progress writes
The worker writes progress to Postgres (throttled: only when the integer percentage changes or at least 2 s have passed) and publishes the same payload to Redis. Postgres is authoritative; Redis only feeds the WebSocket. The worker uses its own DB session. If RQ's per-job fork causes trouble with model libraries, use `rq worker --worker-class rq.SimpleWorker`.

### 10.4 CLI (`backend/app/cli.py`, wrapped by Makefile)
- `seed`: creates one completed **mock** match (no video) so the dashboard is never empty.
- `import-results --file results.json [--name "..."]`: validate against the results Pydantic model, create a match with `pipeline_mode="imported"`, `status=completed`, `video_path=NULL`. Reject invalid files with a clear error listing the problems.
- `export-schema`: writes `docs/results.schema.json`.

---

## 11. Frontend (Angular)

Standalone components, signals, strict TypeScript. API base URL from an environment file (default `http://localhost:8000/api/v1`). Style with Tailwind: clean, readable, dark-neutral theme. The human will later supply visual references for graphs and styling, so **keep every Plotly chart in its own component under `src/app/charts/` with all styling in one config module** that is easy to restyle.

### 11.1 Routes
- `/` : Upload page
- `/matches` : Matches list
- `/matches/:id` : Match dashboard

### 11.2 Upload page
Drag-and-drop or file picker, client-side check of extension and size (2 GB), real upload progress via `HttpClient` progress events. On success, call `POST /matches/{id}/process` automatically and navigate to `/matches/:id`. Show the pipeline-mode badge (from `/health`).

### 11.3 Matches list
Table: filename, status chip, progress, mode badge (mock/real/imported), created time, actions (Open, Delete with confirmation). Poll every 5 s while any match is non-terminal. Empty state with a link to upload.

### 11.4 Match dashboard
- Header: filename, status, mode badge.
- **Calibration banner** on every completed match with `calibration === "naive"`: "Positions are approximate: pitch calibration is not yet enabled." Distances display with a leading "≈".
- `uploaded` / `queued` / `processing`: progress card driven by the WebSocket (auto-reconnect; fall back to polling `GET /matches/{id}` if the socket fails). `uploaded` also shows a "Start processing" button.
- `failed`: error message and a **Retry** button.
- `completed`: three tabs:
  - **Heatmaps:** selector `Team A | Team B | Individual track`. Plotly heatmap with the pitch lines drawn over it (outline, halfway line, centre circle, penalty and goal boxes in metres), fixed 105:68 aspect ratio, hover showing metres. The track picker lists only tracks passing the duration filter (below).
  - **Stats:** sortable table: track label ("Track #12"), team, role, duration, distance (≈ m), average position. A **minimum-duration slider** (default 10 s, range 0–120 s) filters tracks; team filter; per-team totals row. ID fragmentation is expected, hence the slider and the "Track #" labels.
  - **Possession:** horizontal timeline (Team A / Team B / Unknown colour bands) plus a summary showing A%, B% and the unknown share.
- **Team labels:** a toggle to swap the A/B colours and optional renaming, kept client-side per match.
- **Export:** buttons for the tracks CSV and the possession CSV.
- Loading skeletons and clear error states for every request.

---

## 12. Dev runner and setup

`SETUP.md` must contain exact, copy-pasteable steps (flag every step that needs sudo):
- apt packages: `postgresql redis-server python3-venv python3-dev libpq-dev ffmpeg`
- Create the Postgres role and database matching `.env.example`
- Node LTS via nvm; Angular CLI
- Python venv at `backend/.venv`; `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`
- Copy `.env.example` to `.env`

Makefile targets: `setup`, `migrate`, `seed`, `dev` (honcho runs `Procfile.dev`: uvicorn API with reload, the RQ worker, `ng serve`), `test`, `schema`, `import FILE=path`, `lint`.

---

## 13. Testing

**Backend (pytest):**
- Health, status machine transitions (including 409s), stale-job reaper
- Upload: rejects bad extension, rejects over-limit size and removes the partial file, rejects unreadable video
- Full mock lifecycle: upload → process → completed → results validate against the Pydantic model (run the job function directly, plus one test with a real Redis/RQ burst worker)
- Unit tests: `NaiveCalibrator`, foot-point calculation, possession engine (nearest foot point, 1.5× box-height threshold, 1 s carry-forward, short-interval merging, percentage rule), team classifier on synthetic colour crops (two teams plus an outlier), distance with the speed cap
- Import command: valid and invalid files
- Real-mode smoke test marked `@pytest.mark.real`, skipped unless `RUN_REAL=1` and a fixture clip exists; it only checks that the pipeline runs and returns schema-valid results, including gracefully when there are zero detections

**Frontend:** component or service tests for the duration filter and sorting, the progress service (socket plus polling fallback), and the calibration banner logic. No e2e framework.

**Agent self-verification (every phase):** run the app and check the acceptance criteria yourself. From Phase 3 on, use the browser to confirm the UI behaves as described, and fix problems before reporting.

---

## 14. Build phases and acceptance criteria

### Phase 1: Repo, setup, health
Create the repo layout, `.gitignore`, `.env.example`, `AGENTS.md` (from Section 2), `SETUP.md`, `Makefile`, `Procfile.dev`. Ask the human to run the sudo steps. Create the FastAPI skeleton, Alembic init, the Angular app skeleton with Tailwind.
**Accept:** `make dev` starts API, worker and web; `/api/v1/health` returns OK; Angular home loads; Postgres and Redis connections succeed.

### Phase 2: Database, API, queue, mock pipeline
Models + migrations, all REST endpoints, upload streaming, RQ worker, mock pipeline, progress writes + pub/sub, WebSocket endpoint, stale-job reaper, `seed` command.
**Accept:** upload a small video via `curl`, process it, watch WS progress reach 100%, fetch results that validate against the schema; over-limit and bad-extension uploads are rejected; `make seed` creates a viewable match; killing the worker mid-job leads to `failed` after the stale timeout (use a short timeout to test).

### Phase 3: Frontend shell, upload, matches list, progress
Routes, API service, upload page with progress, matches list with polling and delete, dashboard shell with the progress card, WebSocket service with fallback, failed state with Retry.
**Accept (in the browser):** upload → auto-processing → live progress → completed state; list shows statuses; delete works with confirmation; Retry works on a deliberately failed job.

### Phase 4: Dashboard views
Heatmaps tab (pitch overlay, team + track views), Stats tab (sorting, duration slider, team filter, totals), Possession tab, calibration banner, A/B swap/rename.
**Accept:** the seeded mock match shows correct heatmaps (axes in metres, 105:68 ratio), the slider changes the table and the track picker, the possession timeline and percentages match the data, and the banner is shown.

### Phase 5: Export, delete, error states, polish
CSV exports (both kinds), delete semantics (including the processing 409), loading/empty/error states everywhere, GZip.
**Accept:** both CSVs download with the specified columns and open correctly; delete removes the DB rows and the video file; every request failure shows a clear message.

### Phase 6: Real pipeline
Install `requirements-real.txt`. Implement the real pipeline per Section 9 behind the interface, selectable with `PIPELINE_MODE=real`. Ask the human for `ROBOFLOW_API_KEY` and a short test clip (about 10–20 s).
**Accept:** on the test clip, a real-mode job completes (or fails cleanly with a readable error); results validate against the schema; the dashboard renders them with the naive-calibration banner; the log states which device was used; mock mode still works unchanged.

### Phase 7: Import, tests, README
`import-results` and `export-schema`, full test suite from Section 13, `README.md` (what it is, quick start, modes, results schema pointer, known limitations, future work).
**Accept:** `make test` passes; importing a valid results file produces a viewable match; invalid files are rejected clearly; a new developer can follow the README from clone to running dashboard.

---

## 15. Known limitations (state these in the README)
- Positions and distances are approximate: naive pixel-to-pitch scaling ignores camera motion.
- Team/role classification is colour-based; goalkeepers and referees are grouped as "other" and goalkeepers do not count towards possession.
- ByteTrack IDs fragment; the UI filters by minimum duration rather than showing "players".
- Real mode on the development laptop is slow and capped to short clips.

## 16. Future work (do not build now)
Real homography calibration; SigLIP team classification; manual per-track role override; trajectory endpoint and replay; PDF/PNG export; auth; Docker and deployment (note: Railway/Render have no GPU, so a deployed demo would use mock or imported results); formation, pressing and passing analytics; richer chart styling from supplied references.
