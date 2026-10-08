import os
from pathlib import Path

import cv2
import numpy as np

from app.config import settings
from app.schemas import ArtifactItem

TEAM_COLORS = {"A": (255, 191, 0), "B": (147, 20, 255), None: (180, 180, 180)}
BALL_COLOR = (0, 215, 255)
PITCH_COLOR = (70, 70, 70)


def _pitch(canvas: np.ndarray) -> np.ndarray:
    h, w = canvas.shape[:2]
    sx, sy = w / 105.0, h / 68.0
    cv2.rectangle(canvas, (0, 0), (w - 1, h - 1), (35, 120, 35), 2)
    cv2.line(canvas, (w // 2, 0), (w // 2, h), (35, 120, 35), 2)
    cv2.circle(canvas, (w // 2, h // 2), int(9.15 * min(sx, sy)), (35, 120, 35), 2)
    for x in (0, 16.5, 88.5, 105):
        cv2.rectangle(canvas, (int(x * sx), int(13.84 * sy)), (int(x * sx), int(54.16 * sy)), (35, 120, 35), 2)
    return canvas


def _write_video(path: Path, frames: list[np.ndarray], fps: float, size: tuple[int, int]) -> None:
    if not frames:
        raise ValueError("No frames were available for visual artifact generation")
    temp = path.with_name(f"{path.stem}.tmp{path.suffix}")
    writer = cv2.VideoWriter(str(temp), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    if not writer.isOpened():
        raise ValueError(f"Unable to create visual artifact '{path.name}'")
    try:
        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()
    os.replace(temp, path)


def render_artifacts(
    match_id: str,
    frames: list[np.ndarray],
    observations: list[dict],
    classifications: dict[int, tuple[str | None, str, str]],
    sample_fps: float,
) -> list[ArtifactItem]:
    """Render the notebook's four visual outputs from one inference pass."""
    output_dir = Path(settings.UPLOAD_DIR) / "artifacts" / match_id
    output_dir.mkdir(parents=True, exist_ok=True)
    height, width = frames[0].shape[:2]
    annotated: list[np.ndarray] = []
    radar: list[np.ndarray] = []
    voronoi: list[np.ndarray] = []
    ball_path: list[tuple[float, float]] = []

    for frame, observation in zip(frames, observations):
        scene = frame.copy()
        radar_scene = _pitch(np.zeros((680, 1050, 3), dtype=np.uint8))
        team_points: dict[str, list[tuple[float, float]]] = {"A": [], "B": []}
        for detection in observation.get("detections", []):
            tid = detection["track_id"]
            team, role, _ = classifications.get(tid, (None, "other", "unknown"))
            color = TEAM_COLORS.get(team, TEAM_COLORS[None])
            x1, y1, x2, y2 = map(int, detection["bbox"])
            cv2.ellipse(scene, ((x1 + x2) // 2, y2), ((x2 - x1) // 2, max(3, (y2 - y1) // 8)), 0, 0, 360, color, 2)
            cv2.putText(scene, f"#{tid}", (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            if team in team_points and role == "outfield":
                point = detection["pitch_pos"]
                team_points[team].append(point)
                px, py = int(point[0] * 10), int(point[1] * 10)
                cv2.circle(radar_scene, (px, py), 8, color, -1)
            elif role == "other":
                point = detection.get("pitch_pos")
                if point:
                    cv2.circle(radar_scene, (int(point[0] * 10), int(point[1] * 10)), 6, (220, 220, 220), 2)

        ball = observation.get("ball_pitch_pos")
        if ball:
            ball_path.append(ball)
            bx, by = int(ball[0] * 10), int(ball[1] * 10)
            ball_x, ball_y = map(int, observation["ball_px"])
            triangle = np.array(
                [[ball_x, ball_y - 10], [ball_x - 8, ball_y + 6], [ball_x + 8, ball_y + 6]],
                dtype=np.int32,
            )
            cv2.polylines(scene, [triangle], True, BALL_COLOR, 2)
            cv2.circle(radar_scene, (bx, by), 6, BALL_COLOR, -1)

        vor = radar_scene.copy()
        yy, xx = np.indices((680, 1050))
        if team_points["A"] and team_points["B"]:
            a = np.asarray(team_points["A"]) * np.array([10, 10])
            b = np.asarray(team_points["B"]) * np.array([10, 10])
            da = np.min((xx[None] - a[:, 0, None, None]) ** 2 + (yy[None] - a[:, 1, None, None]) ** 2, axis=0)
            db = np.min((xx[None] - b[:, 0, None, None]) ** 2 + (yy[None] - b[:, 1, None, None]) ** 2, axis=0)
            mask = da <= db
            overlay = np.zeros_like(vor)
            overlay[mask] = TEAM_COLORS["A"]
            overlay[~mask] = TEAM_COLORS["B"]
            vor = cv2.addWeighted(overlay, 0.28, vor, 0.72, 0)
        radar.append(radar_scene)
        voronoi.append(vor)
        annotated.append(scene)

    annotated_path = output_dir / "annotated.mp4"
    radar_path = output_dir / "radar.mp4"
    voronoi_path = output_dir / "voronoi.mp4"
    ball_path_file = output_dir / "ball-path.png"
    _write_video(annotated_path, annotated, sample_fps, (width, height))
    _write_video(radar_path, radar, sample_fps, (1050, 680))
    _write_video(voronoi_path, voronoi, sample_fps, (1050, 680))
    path_scene = _pitch(np.zeros((680, 1050, 3), dtype=np.uint8))
    if len(ball_path) > 1:
        points = np.asarray(ball_path, dtype=np.float32) * 10
        cv2.polylines(path_scene, [points.astype(np.int32)], False, BALL_COLOR, 3)
    cv2.imwrite(str(ball_path_file), path_scene)

    return [
        ArtifactItem(kind="annotated_video", filename=f"artifacts/{match_id}/annotated.mp4", url=f"/api/v1/matches/{match_id}/artifacts/annotated_video", media_type="video/mp4", width=width, height=height),
        ArtifactItem(kind="radar_video", filename=f"artifacts/{match_id}/radar.mp4", url=f"/api/v1/matches/{match_id}/artifacts/radar_video", media_type="video/mp4", width=1050, height=680),
        ArtifactItem(kind="voronoi_video", filename=f"artifacts/{match_id}/voronoi.mp4", url=f"/api/v1/matches/{match_id}/artifacts/voronoi_video", media_type="video/mp4", width=1050, height=680),
        ArtifactItem(kind="ball_path_image", filename=f"artifacts/{match_id}/ball-path.png", url=f"/api/v1/matches/{match_id}/artifacts/ball_path_image", media_type="image/png", width=1050, height=680),
    ]
