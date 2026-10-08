import os
import cv2
import numpy as np
from app.config import settings
from app.schemas import (
    MatchResultsResponse, ResultsMeta, TrackItem, RawTrajectoriesData
)
from app.pipeline.base import BasePipeline, PipelineContext
from app.pipeline.calibrator import HomographyCalibrator
from app.pipeline.keypoints import FieldKeypointDetector
from app.pipeline.teams import TeamClassifier
from app.pipeline.aggregate import (
    compute_track_distance_and_avg, build_heatmaps_data
)
from app.pipeline.possession import compute_possession_from_frames
from app.pipeline.render import render_artifacts

class RealPipeline(BasePipeline):
    """
    Real ML Pipeline orchestrator:
    Roboflow detectors -> supervision.ByteTrack -> pitch homography ->
    Lab TeamClassifier -> Aggregator & Possession Engine.
    """

    def run(
        self,
        video_path: str | None,
        match_id: str,
        ctx: PipelineContext,
        video_meta: dict | None = None
    ) -> tuple[MatchResultsResponse, RawTrajectoriesData]:

        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"Video file not found at '{video_path}'")

        ctx.report(0, "Opening video file")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Failed to open video file")

        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)

        stride = settings.FRAME_STRIDE
        sample_fps = src_fps / float(stride)
        max_frames = int(settings.MAX_CLIP_SECONDS * src_fps)

        # Downscale target
        target_w = min(orig_w, settings.MAX_FRAME_WIDTH)
        scale_ratio = target_w / float(orig_w) if orig_w > 0 else 1.0
        target_h = int(orig_h * scale_ratio)

        # Dynamic import of heavy dependencies
        import supervision as sv
        from app.pipeline.detector import Detector

        detector = Detector()
        field_detector = FieldKeypointDetector()
        calibrator = HomographyCalibrator()
        team_classifier = TeamClassifier(device="cpu")

        # Initialize ByteTrack
        byte_tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=int(sample_fps * 2),
            minimum_matching_threshold=0.8,
            frame_rate=int(sample_fps)
        )

        # Tracking state
        raw_track_points: dict[int, list[tuple[float, float, float]]] = {} # tid -> list of (t, x_m, y_m)
        raw_track_crops: dict[int, list[np.ndarray]] = {} # tid -> player crops
        raw_track_stats: dict[int, dict] = {} # tid -> {'classes': [], 'frames': int}
        raw_track_boxes: dict[int, dict[float, tuple[tuple[float, float], float]]] = {} # tid -> {t: (foot_pos, box_h)}

        frame_observations: list[dict] = []
        render_frames: list[np.ndarray] = []

        frame_idx = 0
        processed_count = 0
        max_process_frames = min(total_frames, max_frames) if total_frames > 0 else max_frames

        ctx.report(5, "Processing frames with detection & tracking")

        while cap.isOpened() and frame_idx < max_process_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % stride == 0:
                t_curr = round(frame_idx / src_fps, 2)

                # Resize frame if necessary
                if target_w != orig_w or target_h != orig_h:
                    frame_proc = cv2.resize(frame, (target_w, target_h))
                else:
                    frame_proc = frame

                # Run object and pitch-keypoint inference.
                non_ball_dets, best_ball = detector.infer_frame(frame_proc)
                frame_points, point_confidences = field_detector.infer_frame(frame_proc)
                calibrator.update(frame_points, point_confidences)

                # Convert non-ball detections to supervision Detections object
                if non_ball_dets:
                    xyxy = np.array([d['bbox'] for d in non_ball_dets])
                    confidence = np.array([d['confidence'] for d in non_ball_dets])
                    class_id = np.array([d['class_id'] for d in non_ball_dets])
                    sv_dets = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
                else:
                    sv_dets = sv.Detections.empty()

                # Update ByteTrack
                tracked_dets = byte_tracker.update_with_detections(sv_dets)

                frame_cands = []
                frame_detections = []

                if tracked_dets and len(tracked_dets) > 0:
                    for i in range(len(tracked_dets)):
                        bbox = tracked_dets.xyxy[i]
                        tid = int(tracked_dets.tracker_id[i]) if tracked_dets.tracker_id is not None else i
                        cid = int(tracked_dets.class_id[i]) if tracked_dets.class_id is not None else 2

                        cname = 'player' if cid == 2 else ('goalkeeper' if cid == 1 else 'referee')

                        # Foot point & calibration
                        foot_px = calibrator.get_foot_point_px(bbox)
                        x_m, y_m = calibrator.pixel_to_pitch(foot_px)
                        box_h = float(bbox[3] - bbox[1])

                        if tid not in raw_track_points:
                            raw_track_points[tid] = []
                            raw_track_crops[tid] = []
                            raw_track_stats[tid] = {'classes': [], 'frames': 0}
                            raw_track_boxes[tid] = {}

                        raw_track_points[tid].append((t_curr, x_m, y_m))
                        raw_track_stats[tid]['classes'].append(cname)
                        raw_track_stats[tid]['frames'] += 1
                        raw_track_boxes[tid][t_curr] = (foot_px, box_h)
                        frame_detections.append({
                            "track_id": tid,
                            "bbox": [float(value) for value in bbox],
                            "foot_px": foot_px,
                            "pitch_pos": (x_m, y_m),
                            "pitch_pos_native": calibrator.pixel_to_pitch_native(foot_px),
                            "detector_hint": cname,
                        })

                        # The notebook fits TeamClassifier on player crops.
                        if len(raw_track_crops[tid]) < 15:
                            crop = sv.crop_image(frame_proc, bbox)
                            if crop.size:
                                raw_track_crops[tid].append(crop)

                        frame_cands.append({
                            'track_id': tid,
                            'foot_pos': foot_px,
                            'box_height': box_h
                        })

                ball_pos = best_ball['center'] if best_ball else None
                ball_pitch_pos = calibrator.pixel_to_pitch(ball_pos) if ball_pos and calibrator.matrix is not None else None
                ball_pitch_native = calibrator.pixel_to_pitch_native(ball_pos) if ball_pos and calibrator.matrix is not None else None
                frame_observations.append({
                    't': t_curr,
                    'ball_pos': ball_pos,
                    'ball_px': ball_pos,
                    'ball_pitch_pos': ball_pitch_pos,
                    'ball_pitch_native': ball_pitch_native,
                    'candidates': frame_cands,
                    'detections': frame_detections
                })
                render_frames.append(frame_proc.copy())

                processed_count += 1

                # Update progress (0-85%)
                pct = 5 + int((frame_idx / max_process_frames) * 80)
                ctx.report(pct, f"Processed frame {frame_idx}/{max_process_frames}")

            frame_idx += 1

        cap.release()

        ctx.report(85, "Running team & role classification")

        # Compile track statistics for classification
        track_stats_compiled = {}
        for tid, stats in raw_track_stats.items():
            pts = raw_track_points[tid]
            dur = pts[-1][0] - pts[0][0] if len(pts) > 1 else 0.0
            classes = stats['classes']
            player_count = classes.count('player')
            player_ratio = player_count / float(len(classes)) if classes else 0.0

            # Majority class
            maj_class = max(set(classes), key=classes.count) if classes else 'unknown'

            track_stats_compiled[tid] = {
                'duration_s': dur,
                'player_ratio': player_ratio,
                'majority_class': maj_class
            }

        # Classify teams using the notebook's fitted SigLIP/UMAP/KMeans model.
        all_crops = [crop for crops in raw_track_crops.values() for crop in crops]
        team_classifier.fit(all_crops)
        track_classifications = {}
        player_team_by_track: dict[int, int] = {}
        for tid, crops in raw_track_crops.items():
            stats = track_stats_compiled[tid]
            if stats["majority_class"] in ("goalkeeper", "referee"):
                track_classifications[tid] = (None, "other", stats["majority_class"])
                continue
            team_id = team_classifier.majority_team(team_classifier.predict(crops))
            if team_id is None:
                track_classifications[tid] = (None, "other", "unknown")
            else:
                player_team_by_track[tid] = team_id
                track_classifications[tid] = ("A" if team_id == 0 else "B", "outfield", "player")

        player_centroids = {}
        for team_id in (0, 1):
            points = [
                raw_track_points[tid][-1][1:]
                for tid, assigned in player_team_by_track.items()
                if assigned == team_id and raw_track_points[tid]
            ]
            if points:
                player_centroids[team_id] = np.mean(np.asarray(points), axis=0)
        for tid, stats in track_stats_compiled.items():
            if stats["majority_class"] != "goalkeeper":
                continue
            point = np.asarray(raw_track_points[tid][-1][1:])
            if len(player_centroids) == 2:
                team_id = min(player_centroids, key=lambda key: np.linalg.norm(point - player_centroids[key]))
                track_classifications[tid] = ("A" if team_id == 0 else "B", "outfield", "goalkeeper")

        ctx.report(92, "Aggregating tracks, heatmaps & possession")

        # Filter tracks by MIN_TRACK_SECONDS_STORE
        tracks_list: list[TrackItem] = []
        trajectories_map: dict[str, list[tuple[float, float, float]]] = {}

        min_store_dur = settings.MIN_TRACK_SECONDS_STORE

        for tid, pts in raw_track_points.items():
            if not pts:
                continue

            dur_s = round(pts[-1][0] - pts[0][0], 1)
            if dur_s < min_store_dur:
                continue

            team, role, hint = track_classifications.get(tid, (None, "other", "unknown"))
            dist_m, avg_pos = compute_track_distance_and_avg(pts)
            track_str_id = str(tid)

            trajectories_map[track_str_id] = pts

            tracks_list.append(TrackItem(
                track_id=tid,
                team=team,
                role=role,
                detector_hint=hint,
                first_t=round(pts[0][0], 1),
                last_t=round(pts[-1][0], 1),
                duration_s=dur_s,
                n_samples=len(pts),
                distance_m=dist_m,
                avg_pos_m=avg_pos
            ))

        # Annotate frame observations with classified team & role
        for obs in frame_observations:
            for cand in obs['candidates']:
                tid = cand['track_id']
                team, role, _ = track_classifications.get(tid, (None, "other", "unknown"))
                cand['team'] = team
                cand['role'] = role
            for detection in obs['detections']:
                tid = detection['track_id']
                team, role, _ = track_classifications.get(tid, (None, "other", "unknown"))
                detection['team'] = team
                detection['role'] = role

        total_dur_s = round(max_process_frames / src_fps, 1)
        possession_data = compute_possession_from_frames(frame_observations, total_dur_s)
        heatmaps_data = build_heatmaps_data(tracks_list, trajectories_map)
        ctx.report(99, "Rendering notebook visual artifacts")
        artifacts = render_artifacts(
            match_id=match_id,
            frames=render_frames,
            observations=frame_observations,
            classifications=track_classifications,
            sample_fps=sample_fps,
        )

        ctx.report(98, "Finalizing real pipeline results")

        results = MatchResultsResponse(
            schema_version=1,
            meta=ResultsMeta(
                pipeline_mode="real",
                calibration="homography",
                duration_s=total_dur_s,
                sample_fps=round(sample_fps, 1),
                frame_size=(target_w, target_h)
            ),
            tracks=tracks_list,
            heatmaps=heatmaps_data,
            possession=possession_data,
            artifacts=artifacts
        )

        trajectories_obj = RawTrajectoriesData(trajectories=trajectories_map)
        ctx.report(100, "Completed real pipeline processing")

        return results, trajectories_obj
