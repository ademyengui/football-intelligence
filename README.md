# Football Intelligence Dashboard

Football Intelligence is a local post-match analytics platform. Upload a football
video, process it with Roboflow detection models, and inspect the resulting
tracking, pitch, team, and possession analysis in an Angular dashboard.

The repository is organized as a small monorepo:

```text
football/
├── backend/       FastAPI API, RQ worker, pipeline, database models and migrations
├── frontend/      Angular dashboard
├── docs/          Generated results schema
├── data/          Local uploads and generated artifacts (gitignored)
├── BUILD_INSTRUCTIONS.md
└── Makefile
```

## Features

- Upload `.mp4` and `.mkv` match clips.
- Queue processing with Redis and RQ.
- Detect balls, players, goalkeepers, and referees with Roboflow.
- Track players with ByteTrack.
- Detect pitch keypoints and project detections onto the configured soccer pitch.
- Classify player teams with the `sports` package's notebook-compatible
  SigLIP/UMAP/KMeans `TeamClassifier`.
- Calculate player trajectories, distances, heatmaps, team possession, and
  possession timelines.
- Generate four persisted visual artifacts:
  - Annotated broadcast video with team colors, track IDs, and ball marker.
  - 2D pitch radar video with players, ball, and referees.
  - Voronoi pitch-control video.
  - Ball-path pitch image.
- Export tracks and possession data as CSV.
- Import results that already conform to the documented JSON schema.
- Show processing progress and failed-job errors in the dashboard.
- Serve generated videos in browser-compatible H.264 format.

## Technology stack

### Backend

- Python 3.12+
- FastAPI and Uvicorn
- SQLAlchemy 2 and Alembic
- PostgreSQL
- Redis and RQ
- Pydantic v2 and `pydantic-settings`
- OpenCV and NumPy
- `supervision` for detections and ByteTrack
- Roboflow `inference_sdk` hosted inference
- Roboflow `sports` for soccer pitch geometry, view transformation, team
  classification, pitch drawing, radar points, Voronoi diagrams, and ball paths
- PyTorch, Transformers, and SigLIP through the real-pipeline dependencies
- FFmpeg/libx264 for browser-compatible artifact encoding

### Frontend

- Angular standalone components
- TypeScript with strict typing
- Tailwind CSS
- Plotly.js charts
- WebSocket progress updates

## Processing architecture

1. The Angular client uploads a video to FastAPI.
2. FastAPI stores the upload and enqueues an RQ job in Redis.
3. The worker opens the video and samples frames according to `FRAME_STRIDE`.
4. Each sampled frame is sent to the Roboflow player and field-keypoint models.
5. Detections are tracked with ByteTrack.
6. The field keypoints are transformed into the soccer pitch coordinate system
   used by the notebook workflow.
7. Representative player crops are passed through the notebook-compatible
   `sports.common.team.TeamClassifier`.
8. The pipeline aggregates tracks, heatmaps, possession, and visual frames.
9. The notebook-style pitch renderers create the radar, Voronoi, and ball-path
   artifacts. The annotated broadcast frames are also rendered.
10. Results and artifact metadata are persisted in PostgreSQL and served through
    the API.

The results schema is the contract between the pipeline and the dashboard. See
[`docs/results.schema.json`](docs/results.schema.json).

## Prerequisites

The supported development environment is Ubuntu with:

- Python 3.12+
- Node.js and npm
- PostgreSQL
- Redis
- FFmpeg with the `libx264` encoder

Create a PostgreSQL database and ensure PostgreSQL and Redis are running before
starting the application. Do not commit database credentials, model keys,
videos, model weights, virtual environments, or generated data.

## Setup

Clone the repository and enter its directory:

```bash
git clone https://github.com/ademyengui/football-intelligence.git
cd football-intelligence
```

Create the local environment file:

```bash
cp .env.example .env
```

Set `ROBOFLOW_API_KEY` in `.env`. The key is read only from the local
environment and must never be committed.

Install the core dependencies:

```bash
make setup
```

Install the real-pipeline dependencies:

```bash
backend/.venv/bin/python -m pip install -r backend/requirements-real.txt
```

The real requirements pin Pillow to `10.4.0` for compatibility with the
notebook-derived computer-vision stack.

Apply database migrations:

```bash
make migrate
```

## Configuration

The main settings are in `.env`:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `UPLOAD_DIR` | Upload and generated-artifact directory |
| `PIPELINE_MODE` | Processing mode; use `real` |
| `ROBOFLOW_API_KEY` | Roboflow API key |
| `ROBOFLOW_MODEL_ID` | Player/ball/goalkeeper/referee model |
| `ROBOFLOW_FIELD_MODEL_ID` | Soccer pitch keypoint model |
| `DETECTION_CONFIDENCE` | Detection confidence threshold |
| `FRAME_STRIDE` | Number of source frames skipped between sampled frames |
| `MAX_CLIP_SECONDS` | Maximum processed clip duration |
| `MAX_FRAME_WIDTH` | Maximum inference frame width |
| `MIN_TRACK_SECONDS_STORE` | Minimum track duration persisted in results |
| `JOB_TIMEOUT_SECONDS` | RQ job timeout |
| `STALE_JOB_SECONDS` | Time before a silent processing job is considered stale |

The default models are:

- `football-players-detection-3zvbc/11`
- `football-field-detection-f07vi/14`

The backend uses the hosted Roboflow inference endpoint with the configured
model IDs. Model access depends on the permissions of the configured API key.

## Running the application

Start the API, worker, and Angular development server together:

```bash
make dev
```

Open the dashboard at [http://localhost:4200](http://localhost:4200).

Useful service endpoints:

- API root: [http://localhost:8000](http://localhost:8000)
- API health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- OpenAPI documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Docker Compose

To run the complete application with PostgreSQL, Redis, the API, the RQ
worker, and the Angular frontend in containers:

```bash
ROBOFLOW_API_KEY=your-key docker compose up --build
```

Compose always sets `PIPELINE_MODE=real`. The dashboard is available at
[http://localhost:4200](http://localhost:4200), and uploaded videos persist in
the `uploads` volume. Do not put the API key in `docker-compose.yml` or commit
your local `.env` file.

To run services separately:

```bash
cd backend
../backend/.venv/bin/python -m uvicorn app.main:app --reload --port 8000
../backend/.venv/bin/python -c 'import sys; from rq.cli import main; sys.argv=["rq","worker","--url","redis://localhost:6379/0"]; main()'
```

In another terminal:

```bash
npm --prefix frontend exec ng serve -- --port 4200 --host 0.0.0.0
```

## Testing and development commands

```bash
make test
make lint
make schema
```

The backend tests cover API behavior, result contracts, calibration helpers,
and pipeline seams. The frontend can be production-built with:

```bash
npm --prefix frontend run build
```

## Results and artifacts

Results are exposed through:

```text
GET /api/v1/matches/{match_id}/results
GET /api/v1/matches/{match_id}/artifacts/{kind}
GET /api/v1/matches/{match_id}/export.csv?kind=tracks
GET /api/v1/matches/{match_id}/export.csv?kind=possession
```

Artifact files are stored below:

```text
data/uploads/artifacts/{match_id}/
├── annotated.mp4
├── radar.mp4
├── voronoi.mp4
└── ball-path.png
```

The generated MP4 files are encoded with H.264 constrained baseline,
`yuv420p`, and fast-start metadata so they can be played by common browsers.

## Importing existing results

Results that conform to the schema can be imported without running inference:

```bash
make import FILE=data/imports/results.json
```

Regenerate the schema after changing result models:

```bash
make schema
```

## Security and repository hygiene

- Keep `.env` local and rotate keys if they are exposed.
- Do not commit videos, generated artifacts, model weights, caches, `node_modules`,
  Python virtual environments, or database files.
- The application is intended for local development and does not include
  authentication or multi-user authorization.

## Current limitations

- Processing is compute- and network-intensive because sampled frames use hosted
  Roboflow inference.
- ByteTrack can fragment IDs when detections disappear.
- Pitch projection requires enough visible, confident field keypoints.
- Team classification is intentionally bounded to representative tracks to keep
  processing practical on local hardware.
- The application is a local development platform, not a production deployment.

## License

No license has been declared for this repository yet. Add a project license
before distributing the code publicly.
