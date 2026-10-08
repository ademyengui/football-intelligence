import os
import subprocess
from pathlib import Path

import cv2
import numpy as np

from app.config import settings
from app.schemas import ArtifactItem
from sports.annotators.soccer import draw_pitch, draw_pitch_voronoi_diagram, draw_points_on_pitch
from sports.configs.soccer import SoccerPitchConfiguration
import supervision as sv

TEAM_COLORS = {"A": (255, 191, 0), "B": (147, 20, 255), None: (180, 180, 180)}
BALL_COLOR = (0, 215, 255)
PITCH_COLOR = (70, 70, 70)


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
    encoded = path.with_name(f"{path.stem}.encoded{path.suffix}")
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(temp),
                "-c:v",
                "libx264",
                "-profile:v",
                "baseline",
                "-level",
                "3.1",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(encoded),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ValueError(f"Unable to encode visual artifact '{path.name}': {result.stderr.strip()}")
        os.replace(encoded, path)
    finally:
        temp.unlink(missing_ok=True)
        encoded.unlink(missing_ok=True)


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
    config = SoccerPitchConfiguration()
    blue = sv.Color.from_hex("00BFFF")
    pink = sv.Color.from_hex("FF1493")
    yellow = sv.Color.from_hex("FFD700")
    white = sv.Color.WHITE

    for frame, observation in zip(frames, observations):
        scene = frame.copy()
        radar_scene = draw_pitch(config)
        team_points: dict[str, list[tuple[float, float]]] = {"A": [], "B": []}
        referee_points: list[tuple[float, float]] = []
        for detection in observation.get("detections", []):
            tid = detection["track_id"]
            team, role, _ = classifications.get(tid, (None, "other", "unknown"))
            color = TEAM_COLORS.get(team, TEAM_COLORS[None])
            x1, y1, x2, y2 = map(int, detection["bbox"])
            cv2.ellipse(scene, ((x1 + x2) // 2, y2), ((x2 - x1) // 2, max(3, (y2 - y1) // 8)), 0, 0, 360, color, 2)
            cv2.putText(scene, f"#{tid}", (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            point = detection.get("pitch_pos_native")
            if point and team in team_points and role == "outfield":
                team_points[team].append(point)
            elif point and detection.get("detector_hint") == "referee":
                referee_points.append(point)

        ball = observation.get("ball_pitch_native")
        if ball:
            ball_path.append(observation["ball_pitch_pos"])
            ball_x, ball_y = map(int, observation["ball_px"])
            triangle = np.array(
                [[ball_x, ball_y - 10], [ball_x - 8, ball_y + 6], [ball_x + 8, ball_y + 6]],
                dtype=np.int32,
            )
            cv2.polylines(scene, [triangle], True, BALL_COLOR, 2)
        radar_scene = draw_points_on_pitch(config, np.asarray([ball]) if ball else np.empty((0, 2)), white, sv.Color.BLACK, 10, pitch=radar_scene)
        radar_scene = draw_points_on_pitch(config, np.asarray(team_points["A"]), blue, sv.Color.BLACK, 16, pitch=radar_scene)
        radar_scene = draw_points_on_pitch(config, np.asarray(team_points["B"]), pink, sv.Color.BLACK, 16, pitch=radar_scene)
        radar_scene = draw_points_on_pitch(config, np.asarray(referee_points), yellow, sv.Color.BLACK, 16, pitch=radar_scene)
        vor = draw_pitch(config)
        if team_points["A"] and team_points["B"]:
            vor = draw_pitch_voronoi_diagram(
                config=config,
                team_1_xy=np.asarray(team_points["A"]),
                team_2_xy=np.asarray(team_points["B"]),
                team_1_color=blue,
                team_2_color=pink,
                pitch=vor,
            )
        vor = draw_points_on_pitch(config, np.asarray([ball]) if ball else np.empty((0, 2)), white, sv.Color.BLACK, 10, pitch=vor)
        vor = draw_points_on_pitch(config, np.asarray(team_points["A"]), blue, sv.Color.WHITE, 16, pitch=vor)
        vor = draw_points_on_pitch(config, np.asarray(team_points["B"]), pink, sv.Color.WHITE, 16, pitch=vor)
        radar.append(radar_scene)
        voronoi.append(vor)
        annotated.append(scene)

    annotated_path = output_dir / "annotated.mp4"
    radar_path = output_dir / "radar.mp4"
    voronoi_path = output_dir / "voronoi.mp4"
    ball_path_file = output_dir / "ball-path.png"
    _write_video(annotated_path, annotated, sample_fps, (width, height))
    radar_height, radar_width = radar[0].shape[:2]
    _write_video(radar_path, radar, sample_fps, (radar_width, radar_height))
    _write_video(voronoi_path, voronoi, sample_fps, (radar_width, radar_height))
    path_scene = draw_pitch(config)
    if len(ball_path) > 1:
        points = np.asarray(ball_path, dtype=np.float32) * 10
        cv2.polylines(path_scene, [points.astype(np.int32)], False, BALL_COLOR, 3)
    cv2.imwrite(str(ball_path_file), path_scene)

    return [
        ArtifactItem(kind="annotated_video", filename=f"artifacts/{match_id}/annotated.mp4", url=f"/api/v1/matches/{match_id}/artifacts/annotated_video", media_type="video/mp4", width=width, height=height),
        ArtifactItem(kind="radar_video", filename=f"artifacts/{match_id}/radar.mp4", url=f"/api/v1/matches/{match_id}/artifacts/radar_video", media_type="video/mp4", width=1300, height=800),
        ArtifactItem(kind="voronoi_video", filename=f"artifacts/{match_id}/voronoi.mp4", url=f"/api/v1/matches/{match_id}/artifacts/voronoi_video", media_type="video/mp4", width=1300, height=800),
        ArtifactItem(kind="ball_path_image", filename=f"artifacts/{match_id}/ball-path.png", url=f"/api/v1/matches/{match_id}/artifacts/ball_path_image", media_type="image/png", width=1300, height=800),
    ]
