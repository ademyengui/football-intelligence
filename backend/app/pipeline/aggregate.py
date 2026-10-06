import gzip
import json

import numpy as np
from scipy.ndimage import gaussian_filter

from app.schemas import HeatmapGrid, HeatmapsData, RawTrajectoriesData, TrackItem

MAX_SPEED_MPS = 12.0  # Speed cap in metres per second to filter jumps

def compute_track_distance_and_avg(
    trajectories: list[tuple[float, float, float]]
) -> tuple[float, tuple[float, float]]:
    """
    Computes total distance in metres (capped by speed) and average pitch position [x, y].
    trajectories: list of (t, x, y)
    """
    if not trajectories:
        return 0.0, (0.0, 0.0)

    total_dist = 0.0
    pts = np.array([(x, y) for _, x, y in trajectories])
    ts = np.array([t for t, _, _ in trajectories])

    avg_x = float(np.mean(pts[:, 0]))
    avg_y = float(np.mean(pts[:, 1]))

    for i in range(1, len(trajectories)):
        dt = ts[i] - ts[i - 1]
        if dt <= 0:
            continue
        dx = pts[i, 0] - pts[i - 1, 0]
        dy = pts[i, 1] - pts[i - 1, 1]
        step = float(np.sqrt(dx * dx + dy * dy))
        speed = step / dt
        if speed <= MAX_SPEED_MPS:
            total_dist += step

    return round(total_dist, 1), (round(avg_x, 1), round(avg_y, 1))


def generate_heatmap_grid(
    positions: list[tuple[float, float]],
    width: int = 105,
    height: int = 68,
    sigma: float = 3.0
) -> list[list[float]]:
    """
    Generates a 2D heatmap grid [68 rows][105 cols] normalized so max is 1.0 (rounded to 3 decimals).
    """
    grid = np.zeros((height, width), dtype=np.float32)
    for x, y in positions:
        ix = int(np.clip(x, 0, width - 1))
        iy = int(np.clip(y, 0, height - 1))
        grid[iy, ix] += 1.0

    if np.sum(grid) > 0:
        grid = gaussian_filter(grid, sigma=sigma)
        max_val = np.max(grid)
        if max_val > 0:
            grid = grid / max_val

    grid = np.round(grid, 3)
    return grid.tolist()


def build_heatmaps_data(
    tracks: list[TrackItem],
    trajectories_map: dict[str, list[tuple[float, float, float]]],
    width: int = 105,
    height: int = 68
) -> HeatmapsData:
    """
    Builds Team A, Team B, and per-track heatmaps.
    """
    team_a_positions: list[tuple[float, float]] = []
    team_b_positions: list[tuple[float, float]] = []
    track_heatmaps: dict[str, list[list[float]]] = {}

    for track in tracks:
        track_str_id = str(track.track_id)
        pts = [(x, y) for _, x, y in trajectories_map.get(track_str_id, [])]

        if track.team == "A" and track.role == "outfield":
            team_a_positions.extend(pts)
        elif track.team == "B" and track.role == "outfield":
            team_b_positions.extend(pts)

        if track.duration_s >= 3.0 and pts:
            track_heatmaps[track_str_id] = generate_heatmap_grid(pts, width, height)

    heatmap_a = generate_heatmap_grid(team_a_positions, width, height)
    heatmap_b = generate_heatmap_grid(team_b_positions, width, height)

    return HeatmapsData(
        grid=HeatmapGrid(width=width, height=height, bin_m=1),
        teams={
            "A": heatmap_a,
            "B": heatmap_b
        },
        tracks=track_heatmaps
    )


def compress_trajectories(trajectories_data: RawTrajectoriesData) -> bytes:
    """Compresses raw trajectories dict to gzip bytes."""
    data_str = json.dumps(trajectories_data.model_dump())
    return gzip.compress(data_str.encode("utf-8"))


def decompress_trajectories(compressed_bytes: bytes) -> RawTrajectoriesData:
    """Decompresses gzip bytes to RawTrajectoriesData."""
    decompressed = gzip.decompress(compressed_bytes)
    data_dict = json.loads(decompressed.decode("utf-8"))
    return RawTrajectoriesData(**data_dict)
