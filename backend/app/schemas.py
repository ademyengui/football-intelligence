from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- API Schemas ---

class HealthResponse(BaseModel):
    status: str = "ok"
    pipeline_mode: str

class MatchOut(BaseModel):
    id: UUID
    original_filename: str
    video_path: str | None = None
    status: str
    progress: int
    progress_message: str | None = None
    error_message: str | None = None
    pipeline_mode: str
    video_fps: float | None = None
    video_width: int | None = None
    video_height: int | None = None
    video_duration_s: float | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True

class MatchProgressUpdate(BaseModel):
    status: str
    progress: int
    message: str | None = None
    error: str | None = None

# --- Results JSON Schemas ---

class ResultsMeta(BaseModel):
    pipeline_mode: str  # real | imported
    calibration: str = "naive"
    duration_s: float
    sample_fps: float
    frame_size: tuple[int, int]

class TrackItem(BaseModel):
    track_id: int
    team: str | None = None  # "A" | "B" | None
    role: str  # "outfield" | "other"
    detector_hint: str  # "player" | "goalkeeper" | "referee" | "unknown"
    first_t: float
    last_t: float
    duration_s: float
    n_samples: int
    distance_m: float
    avg_pos_m: tuple[float, float]

class HeatmapGrid(BaseModel):
    width: int = 105
    height: int = 68
    bin_m: int = 1

class HeatmapsData(BaseModel):
    grid: HeatmapGrid = Field(default_factory=HeatmapGrid)
    teams: dict[str, list[list[float]]]  # "A", "B" -> 68 rows of 105 cols
    tracks: dict[str, list[list[float]]]  # track_id str -> 68 rows of 105 cols

class PossessionInterval(BaseModel):
    start_s: float
    end_s: float
    state: str  # "A" | "B" | "unknown"

class PossessionSummary(BaseModel):
    A_pct: float
    B_pct: float
    unknown_pct: float

class PossessionData(BaseModel):
    intervals: list[PossessionInterval]
    summary: PossessionSummary

class ArtifactItem(BaseModel):
    kind: str
    filename: str
    url: str | None = None
    media_type: str
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None

class MatchResultsResponse(BaseModel):
    schema_version: int = 1
    meta: ResultsMeta
    tracks: list[TrackItem]
    heatmaps: HeatmapsData
    possession: PossessionData
    artifacts: list[ArtifactItem] = Field(default_factory=list)
    # Trajectories are omitted from GET /results response per specification

class RawTrajectoriesData(BaseModel):
    # track_id (str) -> List of [t, x, y] triples
    trajectories: dict[str, list[tuple[float, float, float]]]
