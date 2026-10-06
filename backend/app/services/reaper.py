import asyncio
import json
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import SessionLocal
from app.models import Match
from app.services.progress import get_redis_client


def reap_stale_jobs():
    """Scans DB for matches stuck in 'processing' state past STALE_JOB_SECONDS."""
    db = SessionLocal()
    redis_cli = get_redis_client()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.STALE_JOB_SECONDS)
        stale_matches = db.query(Match).filter(
            Match.status == "processing",
            Match.updated_at < cutoff
        ).all()

        for match in stale_matches:
            match.status = "failed"
            match.error_message = "Worker stopped responding"
            match.progress_message = "Failed due to stale worker timeout"
            match.updated_at = datetime.now(timezone.utc)
            db.commit()

            # Publish terminal state update to Redis
            channel_name = f"match:{match.id}:progress"
            payload = {
                "status": "failed",
                "progress": match.progress,
                "message": match.progress_message,
                "error": match.error_message
            }
            try:
                redis_cli.publish(channel_name, json.dumps(payload))
            except Exception as e:
                print(f"[Reaper] Redis publish error: {e}")

            print(f"[Reaper] Reaped stale job for match {match.id}")
    finally:
        db.close()


async def start_stale_job_reaper_loop():
    """Async background task that runs every 60 seconds."""
    while True:
        try:
            reap_stale_jobs()
        except Exception as exc:
            print(f"[Reaper] Error during stale job reap: {exc}")
        await asyncio.sleep(60)
