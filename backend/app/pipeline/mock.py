import time
import uuid

import numpy as np

from app.config import settings
from app.pipeline.aggregate import build_heatmaps_data, compute_track_distance_and_avg
from app.pipeline.base import BasePipeline, PipelineContext
from app.pipeline.possession import compute_possession_from_frames
from app.schemas import (
    MatchResultsResponse,
    RawTrajectoriesData,
    ResultsMeta,
    TrackItem,
)


class MockPipeline(BasePipeline):
    """
    Deterministic Mock Pipeline for development and testing.
    Generates realistic 24-track random walks, synthetic heatmaps, and possession timeline.
    """

    def run(
        self,
        video_path: str | None,
        match_id: str,
        ctx: PipelineContext,
        video_meta: dict | None = None
    ) -> tuple[MatchResultsResponse, RawTrajectoriesData]:

        # Seed RNG deterministically from match_id UUID
        try:
            seed_val = int(uuid.UUID(match_id).int & 0xFFFFFFFF)
        except (ValueError, TypeError, AttributeError):
            seed_val = 42
        rng = np.random.RandomState(seed_val)

        duration_s = settings.MOCK_DURATION_SECONDS
        sample_fps = 5.0
        n_samples = int(duration_s * sample_fps)
        run_seconds = settings.MOCK_RUN_SECONDS

        ctx.report(5, "Initializing mock pipeline")
        time.sleep(run_seconds * 0.05)

        # Build 24 track definitions: 10 A, 10 B, 2 Goalkeepers, 2 Referees
        track_defs = []
        # Team A (10 outfield players)
        a_anchors = [
            (20, 20), (20, 34), (20, 48),
            (35, 15), (35, 34), (35, 53),
            (50, 10), (50, 27), (50, 44), (50, 60)
        ]
        for idx, (ax, ay) in enumerate(a_anchors):
            track_defs.append({
                "id": idx + 1,
                "team": "A",
                "role": "outfield",
                "hint": "player",
                "anchor": (ax, ay),
                "duration": duration_s
            })

        # Team B (10 outfield players)
        b_anchors = [
            (85, 20), (85, 34), (85, 48),
            (70, 15), (70, 34), (70, 53),
            (55, 10), (55, 27), (55, 44), (55, 60)
        ]
        for idx, (bx, by) in enumerate(b_anchors):
            track_defs.append({
                "id": idx + 11,
                "team": "B",
                "role": "outfield",
                "hint": "player",
                "anchor": (bx, by),
                "duration": duration_s
            })

        # 2 Goalkeepers
        track_defs.append({"id": 21, "team": None, "role": "other", "hint": "goalkeeper", "anchor": (5, 34), "duration": duration_s})
        track_defs.append({"id": 22, "team": None, "role": "other", "hint": "goalkeeper", "anchor": (100, 34), "duration": duration_s})

        # 2 Referees
        track_defs.append({"id": 23, "team": None, "role": "other", "hint": "referee", "anchor": (52, 30), "duration": duration_s})
        track_defs.append({"id": 24, "team": None, "role": "other", "hint": "referee", "anchor": (52, 38), "duration": duration_s})

        # Add 2 short fragment tracks
        track_defs.append({"id": 25, "team": "A", "role": "outfield", "hint": "player", "anchor": (45, 20), "duration": 4.0})
        track_defs.append({"id": 26, "team": "B", "role": "outfield", "hint": "player", "anchor": (60, 50), "duration": 5.0})

        ctx.report(20, "Generating trajectories")
        time.sleep(run_seconds * 0.15)

        trajectories_map: dict[str, list[tuple[float, float, float]]] = {}
        tracks_list: list[TrackItem] = []

        # Generate smooth random walk trajectories around anchors
        for tdef in track_defs:
            tid = tdef["id"]
            dur = tdef["duration"]
            t_samples = int(dur * sample_fps)
            t_vals = np.linspace(0.0, dur, t_samples)

            ax, ay = tdef["anchor"]
            # Gaussian random walk smoothed with cumulative sum
            dx = rng.normal(0, 0.4, size=t_samples)
            dy = rng.normal(0, 0.4, size=t_samples)
            x_vals = np.clip(ax + np.cumsum(dx), 1.0, 104.0)
            y_vals = np.clip(ay + np.cumsum(dy), 1.0, 67.0)

            traj_points = [
                (float(round(t_vals[i], 1)), float(round(x_vals[i], 1)), float(round(y_vals[i], 1)))
                for i in range(t_samples)
            ]
            trajectories_map[str(tid)] = traj_points

            dist_m, avg_pos = compute_track_distance_and_avg(traj_points)

            tracks_list.append(TrackItem(
                track_id=tid,
                team=tdef["team"],
                role=tdef["role"],
                detector_hint=tdef["hint"],
                first_t=0.0,
                last_t=float(round(dur, 1)),
                duration_s=float(round(dur, 1)),
                n_samples=t_samples,
                distance_m=dist_m,
                avg_pos_m=avg_pos
            ))

        ctx.report(50, "Generating synthetic ball trajectory & possession")
        time.sleep(run_seconds * 0.25)

        # Generate ball random walk and frame observations for possession engine
        frame_observations = []
        ball_x, ball_y = 52.5, 34.0
        for step in range(n_samples):
            t_curr = round(step / sample_fps, 1)
            # Ball move
            ball_x = float(np.clip(ball_x + rng.normal(0, 1.2), 2.0, 103.0))
            ball_y = float(np.clip(ball_y + rng.normal(0, 1.2), 2.0, 66.0))

            # Candidates present in this frame
            candidates = []
            for trk in tracks_list:
                if trk.first_t <= t_curr <= trk.last_t:
                    # Find candidate position at t_curr
                    pts = trajectories_map[str(trk.track_id)]
                    idx = min(int(t_curr * sample_fps), len(pts) - 1)
                    _, px, py = pts[idx]
                    candidates.append({
                        'track_id': trk.track_id,
                        'team': trk.team,
                        'role': trk.role,
                        'foot_pos': (px, py),
                        'box_height': 3.0
                    })

            frame_observations.append({
                't': t_curr,
                'ball_pos': (ball_x, ball_y),
                'candidates': candidates
            })

        possession_data = compute_possession_from_frames(frame_observations, duration_s)

        ctx.report(75, "Building heatmaps")
        time.sleep(run_seconds * 0.25)

        heatmaps_data = build_heatmaps_data(tracks_list, trajectories_map)

        ctx.report(95, "Finalizing mock results")
        time.sleep(run_seconds * 0.1)

        results = MatchResultsResponse(
            schema_version=1,
            meta=ResultsMeta(
                pipeline_mode="mock",
                calibration="naive",
                duration_s=duration_s,
                sample_fps=sample_fps,
                frame_size=(1280, 720)
            ),
            tracks=tracks_list,
            heatmaps=heatmaps_data,
            possession=possession_data
        )

        trajectories_obj = RawTrajectoriesData(trajectories=trajectories_map)
        ctx.report(100, "Completed")

        return results, trajectories_obj
