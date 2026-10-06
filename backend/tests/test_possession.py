from app.pipeline.possession import compute_possession_from_frames

def test_possession_basic():
    obs = [
        {
            "t": 0.0,
            "ball_pos": (20.0, 20.0),
            "candidates": [
                {"track_id": 1, "team": "A", "role": "outfield", "foot_pos": (20.5, 20.5), "box_height": 3.0}
            ]
        },
        {
            "t": 1.0,
            "ball_pos": (80.0, 20.0),
            "candidates": [
                {"track_id": 11, "team": "B", "role": "outfield", "foot_pos": (80.2, 20.1), "box_height": 3.0}
            ]
        }
    ]

    res = compute_possession_from_frames(obs, total_duration_s=10.0)
    assert res.summary.A_pct + res.summary.B_pct == 100.0
    assert len(res.intervals) >= 1
