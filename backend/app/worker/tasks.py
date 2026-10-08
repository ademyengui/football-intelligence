import traceback
from datetime import datetime, timezone

from app.config import settings
from app.db import SessionLocal
from app.models import Match, MatchResult
from app.pipeline.aggregate import compress_trajectories
from app.pipeline.base import PipelineContext
from app.pipeline.real import RealPipeline
from app.services.progress import ProgressReporter


def process_match(match_id: str):
    """
    RQ Worker job function. Executes the active pipeline for a match.
    """
    db = SessionLocal()
    reporter = ProgressReporter(match_id, db)

    try:
        match_obj = db.query(Match).filter(Match.id == match_id).first()
        if not match_obj:
            print(f"[Worker] Match {match_id} not found")
            return

        reporter.report(0, "Starting job processing", status="processing")

        pipeline_mode = settings.PIPELINE_MODE

        if pipeline_mode != "real":
            raise ValueError(f"Unsupported PIPELINE_MODE: {pipeline_mode}. Only real processing is available.")

        pipeline = RealPipeline()

        def progress_cb(pct: int, msg: str):
            reporter.report(pct, msg, status="processing")

        ctx = PipelineContext(callback=progress_cb)

        video_meta = {
            "fps": match_obj.video_fps,
            "width": match_obj.video_width,
            "height": match_obj.video_height,
            "duration_s": match_obj.video_duration_s
        }

        # Execute pipeline
        results, trajectories_obj = pipeline.run(
            video_path=match_obj.video_path,
            match_id=match_id,
            ctx=ctx,
            video_meta=video_meta
        )

        # Compress trajectories
        compressed_trajs = compress_trajectories(trajectories_obj)

        # Save or update MatchResult in Postgres
        existing_result = db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
        if existing_result:
            db.delete(existing_result)
            db.commit()

        result_row = MatchResult(
            match_id=match_obj.id,
            schema_version=results.schema_version,
            calibration=results.meta.calibration,
            summary=results.possession.summary.model_dump(),
            tracks=[t.model_dump() for t in results.tracks],
            heatmaps=results.heatmaps.model_dump(),
            possession=results.possession.model_dump(),
            trajectories=compressed_trajs
        )
        db.add(result_row)

        match_obj.status = "completed"
        match_obj.progress = 100
        match_obj.progress_message = "Processing complete"
        match_obj.completed_at = datetime.now(timezone.utc)
        db.commit()

        reporter.report(100, "Processing complete", status="completed")
        print(f"[Worker] Successfully processed match {match_id}")

    except Exception as exc:
        err_msg = str(exc)
        print(f"[Worker] Error processing match {match_id}: {err_msg}")
        traceback.print_exc()

        # Update match status to failed
        match_obj = db.query(Match).filter(Match.id == match_id).first()
        if match_obj:
            match_obj.status = "failed"
            match_obj.error_message = err_msg
            match_obj.progress_message = "Processing failed"
            match_obj.updated_at = datetime.now(timezone.utc)
            db.commit()

        reporter.report(
            progress=0,
            message="Processing failed",
            status="failed",
            error=err_msg
        )
    finally:
        db.close()
