from app.pipeline.mock import MockPipeline
from app.pipeline.base import PipelineContext
from app.schemas import MatchResultsResponse

def test_mock_pipeline_execution():
    pipeline = MockPipeline()
    ctx = PipelineContext()

    results, trajs = pipeline.run(video_path=None, match_id="test-match-123", ctx=ctx)

    assert isinstance(results, MatchResultsResponse)
    assert results.schema_version == 1
    assert results.meta.pipeline_mode == "mock"
    assert len(results.tracks) >= 20
    assert "A" in results.heatmaps.teams
    assert "B" in results.heatmaps.teams
    assert results.possession.summary.A_pct + results.possession.summary.B_pct == 100.0
