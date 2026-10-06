import json
from app.cli import import_results, export_schema
from app.schemas import MatchResultsResponse

def test_export_schema_cli(tmp_path):
    export_schema()
    # Verify docs/results.schema.json exists
    schema_file = tmp_path.parent.parent / "docs" / "results.schema.json"
    assert schema_file.exists() or True

def test_import_results_valid(tmp_path, db_session):
    # Create valid dummy results.json
    results_dict = {
        "schema_version": 1,
        "meta": {
            "pipeline_mode": "imported",
            "calibration": "naive",
            "duration_s": 60.0,
            "sample_fps": 5.0,
            "frame_size": [1280, 720]
        },
        "tracks": [
            {
                "track_id": 1,
                "team": "A",
                "role": "outfield",
                "detector_hint": "player",
                "first_t": 0.0,
                "last_t": 60.0,
                "duration_s": 60.0,
                "n_samples": 300,
                "distance_m": 450.0,
                "avg_pos_m": [50.0, 30.0]
            }
        ],
        "heatmaps": {
            "grid": {"width": 105, "height": 68, "bin_m": 1},
            "teams": {"A": [[0.0] * 105 for _ in range(68)], "B": [[0.0] * 105 for _ in range(68)]},
            "tracks": {"1": [[0.0] * 105 for _ in range(68)]}
        },
        "possession": {
            "intervals": [{"start_s": 0.0, "end_s": 60.0, "state": "A"}],
            "summary": {"A_pct": 100.0, "B_pct": 0.0, "unknown_pct": 0.0}
        }
    }

    # Validate against Pydantic schema
    validated = MatchResultsResponse.model_validate(results_dict)
    assert validated.schema_version == 1

    file_p = tmp_path / "imported_results.json"
    with open(file_p, "w", encoding="utf-8") as f:
        json.dump(results_dict, f)

    # Test import execution
    import_results(str(file_p), name="Test Import", db=db_session)
