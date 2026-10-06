import numpy as np
from app.pipeline.calibrator import NaiveCalibrator
from app.pipeline.teams import TeamClassifier

def test_naive_calibrator():
    calibrator = NaiveCalibrator(pitch_width_m=105.0, pitch_height_m=68.0)
    # Box [x1=100, y1=200, x2=200, y2=400] on 1280x720 frame
    foot_px = calibrator.get_foot_point_px([100, 200, 200, 400])
    assert foot_px == (150.0, 400.0)

    # Centre of frame (640, 360) -> (52.5m, 34.0m)
    x_m, y_m = calibrator.pixel_to_pitch((640.0, 360.0), (1280, 720))
    assert x_m == 52.5
    assert y_m == 34.0

def test_team_classifier_synthetic():
    classifier = TeamClassifier()

    # Create synthetic color vectors for 2 distinct teams
    # Team A: Red-ish Lab colors
    # Team B: Blue-ish Lab colors
    # 1 Referee outlier
    color_vectors = {}
    stats = {}

    for i in range(1, 11):
        color_vectors[i] = [np.array([120.0, 160.0, 140.0], dtype=np.float32) for _ in range(10)]
        stats[i] = {'duration_s': 10.0, 'player_ratio': 0.9, 'majority_class': 'player'}

    for i in range(11, 21):
        color_vectors[i] = [np.array([120.0, 90.0, 80.0], dtype=np.float32) for _ in range(10)]
        stats[i] = {'duration_s': 10.0, 'player_ratio': 0.9, 'majority_class': 'player'}

    # Goalkeeper
    stats[21] = {'duration_s': 10.0, 'player_ratio': 0.1, 'majority_class': 'goalkeeper'}
    color_vectors[21] = [np.array([200.0, 200.0, 200.0], dtype=np.float32)]

    results = classifier.classify_tracks(color_vectors, stats)

    assert results[1][0] in ('A', 'B')
    assert results[11][0] in ('A', 'B')
    assert results[1][0] != results[11][0]
    assert results[21] == (None, 'other', 'goalkeeper')
