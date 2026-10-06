import json
import time
from datetime import datetime, timezone

import redis
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Match

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client

class ProgressReporter:
    def __init__(self, match_id: str, db: Session):
        self.match_id = match_id
        self.db = db
        self.redis = get_redis_client()
        self.last_pct = -1
        self.last_time = 0.0

    def report(
        self,
        progress: int,
        message: str = "",
        status: str = "processing",
        error: str = None
    ):
        now = time.time()
        # Throttle DB writes: only write if progress integer changed or >= 2s elapsed or terminal state
        if (progress != self.last_pct) or (now - self.last_time >= 2.0) or (status in ("completed", "failed")):
            self.last_pct = progress
            self.last_time = now

            # Update DB
            match_obj = self.db.query(Match).filter(Match.id == self.match_id).first()
            if match_obj:
                match_obj.status = status
                match_obj.progress = progress
                match_obj.progress_message = message
                if error is not None:
                    match_obj.error_message = error
                match_obj.updated_at = datetime.now(timezone.utc)
                if status == "completed":
                    match_obj.completed_at = datetime.now(timezone.utc)
                self.db.commit()

            # Publish to Redis channel match:{id}:progress
            payload = {
                "status": status,
                "progress": progress,
                "message": message,
                "error": error
            }
            channel_name = f"match:{self.match_id}:progress"
            try:
                self.redis.publish(channel_name, json.dumps(payload))
            except Exception as e:
                print(f"[ProgressReporter] Redis publish error: {e}")
