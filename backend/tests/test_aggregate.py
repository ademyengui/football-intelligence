from app.pipeline.aggregate import (
    compute_track_distance_and_avg, generate_heatmap_grid
)

def test_distance_speed_cap():
    # Normal movement: (0,0) -> (3,4) over 1s => distance = 5m (speed 5m/s <= 12m/s)
    traj_normal = [(0.0, 0.0, 0.0), (1.0, 3.0, 4.0)]
    dist, avg = compute_track_distance_and_avg(traj_normal)
    assert dist == 5.0
    assert avg == (1.5, 2.0)

    # Jump movement: (0,0) -> (50,50) over 1s => speed 70.7m/s > 12m/s (should be ignored)
    traj_jump = [(0.0, 0.0, 0.0), (1.0, 50.0, 50.0)]
    dist_jump, _ = compute_track_distance_and_avg(traj_jump)
    assert dist_jump == 0.0

def test_heatmap_grid_normalization():
    points = [(50.0, 34.0), (50.0, 34.0)]
    grid = generate_heatmap_grid(points, width=105, height=68)
    assert len(grid) == 68
    assert len(grid[0]) == 105
    # Max value should be normalized to 1.0
    max_val = max(max(row) for row in grid)
    assert max_val == 1.0
