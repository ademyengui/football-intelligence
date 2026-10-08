import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from rq import Queue
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Match, MatchResult
from app.schemas import (
    HeatmapsData,
    MatchOut,
    MatchResultsResponse,
    PossessionData,
    ResultsMeta,
    TrackItem,
)
from app.services.progress import get_redis_client
from app.services.storage import probe_video, save_uploaded_video
from app.worker.tasks import process_match

router = APIRouter(prefix="/matches", tags=["matches"])

def get_rq_queue() -> Queue:
    redis_conn = get_redis_client()
    return Queue("default", connection=redis_conn)

@router.post("", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
async def create_match(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    video_path, original_filename = await save_uploaded_video(file)
    fps, width, height, duration_s = probe_video(video_path)

    match_obj = Match(
        id=uuid.uuid4(),
        original_filename=original_filename,
        video_path=video_path,
        status="uploaded",
        progress=0,
        progress_message="Uploaded video file",
        pipeline_mode=settings.PIPELINE_MODE,
        video_fps=fps,
        video_width=width,
        video_height=height,
        video_duration_s=duration_s
    )
    db.add(match_obj)
    db.commit()
    db.refresh(match_obj)

    return match_obj

@router.get("", response_model=list[MatchOut])
def list_matches(db: Session = Depends(get_db)):
    return db.query(Match).order_by(Match.created_at.desc()).all()

@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: UUID, db: Session = Depends(get_db)):
    match_obj = db.query(Match).filter(Match.id == match_id).first()
    if not match_obj:
        raise HTTPException(status_code=404, detail="Match not found")
    return match_obj

@router.post("/{match_id}/process", response_model=MatchOut)
def start_processing(
    match_id: UUID,
    db: Session = Depends(get_db),
    queue: Queue = Depends(get_rq_queue)
):
    match_obj = db.query(Match).filter(Match.id == match_id).first()
    if not match_obj:
        raise HTTPException(status_code=404, detail="Match not found")

    if match_obj.status not in ("uploaded", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot process match in state '{match_obj.status}'. Only 'uploaded' or 'failed' matches can be processed."
        )

    match_obj.status = "queued"
    match_obj.progress = 0
    match_obj.progress_message = "Enqueued for background processing"
    match_obj.error_message = None
    db.commit()
    db.refresh(match_obj)

    # Enqueue RQ job with configured JOB_TIMEOUT_SECONDS
    queue.enqueue(
        process_match,
        str(match_id),
        job_timeout=settings.JOB_TIMEOUT_SECONDS
    )

    return match_obj

@router.get("/{match_id}/results", response_model=MatchResultsResponse)
def get_match_results(match_id: UUID, db: Session = Depends(get_db)):
    match_obj = db.query(Match).filter(Match.id == match_id).first()
    if not match_obj:
        raise HTTPException(status_code=404, detail="Match not found")

    if match_obj.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Results are only available for 'completed' matches. Current status: '{match_obj.status}'."
        )

    result_row = db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
    if not result_row:
        raise HTTPException(status_code=444, detail="Match results record not found")

    tracks_data = [TrackItem(**t) for t in result_row.tracks]
    heatmaps_data = HeatmapsData(**result_row.heatmaps)
    possession_data = PossessionData(**result_row.possession)

    meta = ResultsMeta(
        pipeline_mode=match_obj.pipeline_mode,
        calibration=result_row.calibration,
        duration_s=match_obj.video_duration_s or 120.0,
        sample_fps=5.0,
        frame_size=(match_obj.video_width or 1280, match_obj.video_height or 720)
    )

    return MatchResultsResponse(
        schema_version=result_row.schema_version,
        meta=meta,
        tracks=tracks_data,
        heatmaps=heatmaps_data,
        possession=possession_data,
        artifacts=result_row.artifacts or []
    )


@router.get("/{match_id}/artifacts/{kind}")
def get_match_artifact(match_id: UUID, kind: str, db: Session = Depends(get_db)):
    result_row = db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
    if not result_row:
        raise HTTPException(status_code=404, detail="Match results record not found")
    artifact = next((item for item in (result_row.artifacts or []) if item.get("kind") == kind), None)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = os.path.join(settings.UPLOAD_DIR, artifact["filename"])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Artifact file is unavailable")
    return FileResponse(path, media_type=artifact.get("media_type"), filename=os.path.basename(path))

@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: UUID, db: Session = Depends(get_db)):
    match_obj = db.query(Match).filter(Match.id == match_id).first()
    if not match_obj:
        return  # Idempotent deletion

    if match_obj.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a match while it is currently being processed."
        )

    # Delete video file from disk if present
    if match_obj.video_path and os.path.exists(match_obj.video_path):
        try:
            os.remove(match_obj.video_path)
        except Exception as e:
            print(f"[Delete] Warning: failed to delete file {match_obj.video_path}: {e}")

    artifact_dir = os.path.join(settings.UPLOAD_DIR, "artifacts", str(match_id))
    if os.path.isdir(artifact_dir):
        for artifact_name in os.listdir(artifact_dir):
            artifact_path = os.path.join(artifact_dir, artifact_name)
            if os.path.isfile(artifact_path):
                os.remove(artifact_path)
        os.rmdir(artifact_dir)

    db.delete(match_obj)
    db.commit()
    return
