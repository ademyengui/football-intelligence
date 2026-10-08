# Football Intelligence Dashboard (v1.0)

Post-match football analytics platform built with **FastAPI**, **RQ**, and **Angular**. Upload a broadcast match clip to run automated detection and tracking, generating player/team heatmaps, per-track distance & speed stats, and a continuous possession timeline.

---

## Architecture Overview

- **Backend:** FastAPI, SQLAlchemy 2.0 (PostgreSQL), RQ + Redis worker, OpenCV, scikit-learn, Pydantic v2.
- **Frontend:** Angular 22 (Standalone Components & Signals), Tailwind CSS, Plotly.js (105m x 68m pitch overlay).
- **Pipeline modes:**
  - **Real Mode:** Roboflow football detection and pitch-keypoint models + ByteTrack + team classification + pitch analytics. Completed matches also include the annotated tracking video, 2D radar video, Voronoi pitch-control video, and ball-path image from the notebook workflow.
  - **Imported Mode:** Import results JSON directly from external Kaggle or Colab notebooks.

---

## Quick Start

### 1. Prerequisites (Ubuntu 24)
Ensure PostgreSQL and Redis services are installed and running:
```bash
sudo apt update
sudo apt install -y postgresql redis-server python3-venv python3-dev libpq-dev ffmpeg
sudo systemctl start postgresql redis-server

# Create database and user
sudo -u postgres psql -c "CREATE USER football WITH PASSWORD 'football';"
sudo -u postgres psql -c "CREATE DATABASE football OWNER football;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football TO football;"
```

### 2. Environment & Dependencies
```bash
# Set up environment variables
cp .env.example .env

# Run automated setup (virtualenv + npm dependencies)
make setup

# Run database migrations
make migrate
```

### 3. Configure and download real-mode dependencies
Put the Roboflow key in `.env` as `ROBOFLOW_API_KEY`. The first real worker run downloads/caches the configured models:

- `football-players-detection-3zvbc/11` (ball, player, goalkeeper, referee)
- `football-field-detection-f07vi/14` (pitch keypoints)

Install optional inference dependencies with:
```bash
backend/.venv/bin/python -m pip install -r backend/requirements-real.txt
```
The dependency file pins Pillow to `10.4.0` for compatibility. Model weights and caches remain outside this repository.

### 4. Run Development Server
```bash
# Start API, RQ Worker, and Angular Web App concurrently via Honcho
make dev
```
Open **http://localhost:4200** in your browser.

---

## Results JSON Schema

All pipeline outputs adhere strictly to the JSON contract documented in [docs/results.schema.json](docs/results.schema.json). To re-export or validate external results:
```bash
# Export JSON schema to docs/results.schema.json
make schema

# Import external results.json file
make import FILE=data/imports/sample_results.json
```

---

## Testing & Verification

Run the comprehensive pytest suite:
```bash
make test
```

---

## Known Limitations (v1.0)

1. **Keypoint Calibration:** Pitch projection depends on enough visible field keypoints; clips with insufficient keypoints fail clearly rather than returning synthetic positions.
2. **Colour-Based Team Classification:** Team classification uses median Lab colour clustering of upper-body crops. Goalkeepers and referees are categorized as `role: "other"` and do not contribute to team possession.
3. **ID Fragmentation:** ByteTrack IDs can fragment across lost frames. Use the **Minimum Duration Slider** on the Stats tab to filter short fragments.
4. **Hardware Compute Caps:** Inference is resource-intensive and capped to short clips (`MAX_CLIP_SECONDS=120`).

---

## Future Work

- Homography pitch calibration with automatic line detection.
- SigLIP embedding-based team classification.
- Manual per-track role override in the dashboard UI.
- Trajectory replay and video synchronization.
- Pressing, formation, and passing sequence analytics.
